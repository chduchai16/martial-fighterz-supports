"""
Module Bot: State Machine và logic tự động hoá toàn bộ chu kỳ game.
Nâng ngưỡng nhận diện Kim Cương lên >= 0.80 và tối ưu cơ chế click Rút lui đảm bảo 100% không bị sót.
"""
from enum import Enum, auto
import logging
from pathlib import Path
import random
import threading
import time
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

try:
    from src.core.capture import FastCapture
    from src.core.config import BotConfig, Rect, config, DEBUG_DIR
    from src.core.vision import MatchResult, VisionEngine
except ImportError:
    from .capture import FastCapture
    from .config import BotConfig, Rect, config, DEBUG_DIR
    from .vision import MatchResult, VisionEngine

logger = logging.getLogger("GameBot.Core")


class BotStoppedException(Exception):
    """Ngoại lệ ném ra khi bot nhận tín hiệu dừng từ người dùng."""
    pass


class GameBot:
    """
    Class điều khiển bot theo State Machine hoàn chỉnh.
    """

    def __init__(self, cfg: Optional[BotConfig] = None):
        self.cfg = cfg or config
        self.capture = FastCapture(
            device_serial=self.cfg.device_serial,
            max_fps=self.cfg.scrcpy_max_fps,
            bitrate=self.cfg.scrcpy_bitrate
        )
        self.vision = VisionEngine(self.cfg.templates)
        self.cycle_count = 0
        self.success_count = 0
        self.current_vip = "vip7"  # Bắt đầu vòng đầu tiên từ VIP7, các vòng sau sẽ đảo chiều thông minh
        self.active_tab: Optional[str] = None  # Theo dõi tab VIP hiện tại đang đứng
        self._stopped = False

    def _check_stop(self):
        """Kiểm tra và ngắt bot ngay lập tức nếu nhận lệnh dừng."""
        if self._stopped:
            raise BotStoppedException("GameBot đã nhận tín hiệu dừng!")

    def start(self):
        """Khởi động hệ thống capture và nạp template."""
        logger.info("Đang khởi động GameBot...")
        self._stopped = False
        self.capture.start()
        logger.info("GameBot đã sẵn sàng hoạt động.")

    def stop(self):
        """Dừng GameBot an toàn (chỉ dừng 1 lần)."""
        if self._stopped:
            return
        self._stopped = True
        logger.info("Đang dừng GameBot...")
        self.capture.stop()
        logger.info("GameBot đã dừng.")

    def _wait_for_frame(self, timeout: float = 3.5) -> np.ndarray:
        """Lấy frame mới nhất và tự động đồng bộ độ phân giải."""
        self._check_stop()
        frame = self.capture.get_latest_frame(timeout=timeout)
        self._check_stop()
        if frame is None:
            raise TimeoutError("Không nhận được frame từ thiết bị!")
        
        f_h, f_w = frame.shape[:2]
        if self.cfg.target_width != f_w or self.cfg.target_height != f_h:
            logger.info(f"Đồng bộ độ phân giải giả lập: {f_w}x{f_h}")
            self.cfg.target_width = f_w
            self.cfg.target_height = f_h

        return frame

    def _tap(self, x: int, y: int, label: str = "Tap"):
        """Gửi lệnh tap vào toạ độ (x, y) tức thì qua Persistent Shell."""
        self._check_stop()
        logger.info(f"[{label}] -> Tap tại điểm ({x}, {y})")
        self.capture.tap(x, y, jitter_px=self.cfg.tap_jitter_px)

    def _swipe_tray_up(self, label: str = "VIP"):
        """Vuốt cuộn khay item lên để lộ dòng kế tiếp."""
        self._check_stop()
        w, h = self.cfg.target_width, self.cfg.target_height
        x1 = int(self.cfg.swipe_vip9_start_ratio[0] * w)
        y1 = int(self.cfg.swipe_vip9_start_ratio[1] * h)
        x2 = int(self.cfg.swipe_vip9_end_ratio[0] * w)
        y2 = int(self.cfg.swipe_vip9_end_ratio[1] * h)
        logger.info(f"[{label}] Đang cuộn khay item lên: từ ({x1}, {y1}) -> ({x2}, {y2})...")
        self.capture.swipe(x1, y1, x2, y2, duration=0.20)
        time.sleep(self.cfg.wait_after_scroll)

    def _swipe_tray_down(self, label: str = "VIP", times: int = 1):
        """Vuốt cuộn khay item xuống để trở về vị trí đầu, hiện full Dòng 1 và 2."""
        self._check_stop()
        w, h = self.cfg.target_width, self.cfg.target_height
        x1 = int(self.cfg.swipe_vip9_end_ratio[0] * w)
        y1 = int(self.cfg.swipe_vip9_end_ratio[1] * h)
        x2 = int(self.cfg.swipe_vip9_start_ratio[0] * w)
        y2 = int(self.cfg.swipe_vip9_start_ratio[1] * h)
        for i in range(times):
            logger.info(f"[{label}] Đang cuộn khay item xuống lại đầu trang (lần {i+1}/{times})...")
            self.capture.swipe(x1, y1, x2, y2, duration=0.20)
            time.sleep(self.cfg.wait_after_scroll)

    def _swipe_vip9_up(self):
        self._swipe_tray_up("VIP9")

    def _swipe_vip9_down(self):
        self._swipe_tray_down("VIP9", times=2)

    def _check_candidate_rois(
        self,
        frame: np.ndarray,
        candidate_rois: List[Rect],
        min_threshold: float,
        enable_phuc_tung: bool = False,
        phuc_tung_threshold: float = 0.78,
        fallback_tray_roi: Optional[Rect] = None
    ) -> Tuple[MatchResult, str, Optional[Rect]]:
        """
        Kiểm tra danh sách các ROI ứng viên của một dòng sau khi cuộn.
        Chọn ROI có confidence cao nhất. Nếu đạt ngưỡng, trả về (best_match, target_type, best_roi).
        Nếu các ứng viên không đạt và có fallback_tray_roi, quét tìm mục tiêu trong toàn vùng khay.
        """
        best_match = MatchResult(found=False, confidence=0.0)
        best_type = "NONE"
        best_roi: Optional[Rect] = None

        for roi in candidate_rois:
            match, target_type = self.vision.check_row_for_targets(
                frame=frame,
                row_roi=roi,
                min_threshold=min_threshold,
                enable_phuc_tung=enable_phuc_tung,
                phuc_tung_threshold=phuc_tung_threshold
            )
            if match.confidence > best_match.confidence:
                best_match = match
                best_type = target_type
                best_roi = roi

        is_found = (best_match.confidence >= min_threshold) or (enable_phuc_tung and best_type == "PHUC_TUNG_C" and best_match.confidence >= phuc_tung_threshold)
        if is_found:
            best_match.found = True
            return best_match, best_type, best_roi

        # Quét fallback toàn vùng nếu có
        if fallback_tray_roi is not None:
            match_fb, target_type_fb = self.vision.check_row_for_targets(
                frame=frame,
                row_roi=fallback_tray_roi,
                min_threshold=min_threshold,
                enable_phuc_tung=enable_phuc_tung,
                phuc_tung_threshold=phuc_tung_threshold
            )
            if match_fb.found:
                cy = match_fb.y + match_fb.h // 2
                dyn_roi = Rect(x=fallback_tray_roi.x, y=max(0, cy - 130), w=fallback_tray_roi.w, h=260)
                return match_fb, target_type_fb, dyn_roi

        return best_match, "NONE", best_roi

    def classify_ok_popup(self, frame: np.ndarray) -> str:
        """
        Phân biệt nhanh nội dung trong popup có nút OK:
        - 'WARRIOR_GEM': Quay trúng Warrior Gem (có mũ Arale hoặc chữ Warrior Gem ở phần đầu popup) -> Bấm OK và tiếp tục chơi tiếp.
        - 'EXHAUSTED': Thông báo hết lượt / hết vật phẩm / không thể đổi -> Bấm OK và chuyển dòng khác.
        Tối ưu quét trong vùng đầu popup (popup_header_roi) để phản xạ tức thì (<0.2s), không quét full màn hình tốn 4 giây!
        """
        w, h = frame.shape[1], frame.shape[0]
        # Vùng nửa trên của popup nơi hiển thị tiêu đề và biểu tượng Arale (y từ 28% đến 58% màn hình)
        popup_header_roi = Rect(int(0.15 * w), int(0.28 * h), int(0.70 * w), int(0.30 * h))

        # 1. Kiểm tra mũ Arale đặc trưng (chỉ xuất hiện trên popup quay trúng Warrior Gem)
        match_arale = self.vision.find_template(frame, "arale_header", threshold=0.75, roi=popup_header_roi)
        if match_arale.found:
            logger.info("✨ [Popup] Nhận diện popup Warrior Gem qua mũ Arale!")
            return "WARRIOR_GEM"

        # 2. Kiểm tra chữ Warrior Gem (Tiếng Anh & Tiếng Việt) trong vùng popup
        for wg_key in ["warrior_gem_en", "warrior_gem_full_en", "warrior_gem_text"]:
            if wg_key in self.cfg.templates:
                match_wg = self.vision.find_template(frame, wg_key, threshold=0.70, roi=popup_header_roi)
                if match_wg.found:
                    logger.info(f"✨ [Popup] Nhận diện popup: Warrior Gem ('{wg_key}')")
                    return "WARRIOR_GEM"

        # 3. Mọi popup OK còn lại (Exchange not available / Not enough items / v.v.) đều là EXHAUSTED
        logger.info("ℹ️ [Popup] Nhận diện thông báo: Hết lượt đổi / Thiếu vật phẩm (EXHAUSTED)")
        return "EXHAUSTED"

    def _confirm_button_closed(self, template_key: str, threshold: float, roi: Rect, tap_pos: Tuple[int, int], max_wait: float = 3.0) -> bool:
        """
        ĐẢM BẢO BẤM THÀNH CÔNG:
        Theo dõi màn hình liên tục cho tới khi nút/popup biến mất hoàn toàn.
        Nếu sau 0.25s nút vẫn còn hiển thị, bấm lại tại toạ độ tap_pos cho tới khi màn hình cập nhật đóng hẳn!
        """
        c_start = time.perf_counter()
        last_retry = c_start
        while time.perf_counter() - c_start < max_wait:
            try:
                frame = self._wait_for_frame()
                re_match = self.vision.find_template(frame, template_key, threshold=threshold, roi=roi)
                if not re_match.found:
                    logger.info(f"✅ Nút/Popup '{template_key}' đã đóng hoàn toàn khỏi màn hình.")
                    return True
                
                # Nếu quá 0.25s mà nút vẫn còn trên màn hình -> tap lại
                if time.perf_counter() - last_retry > 0.25:
                    logger.info(f"🔄 Nút/Popup '{template_key}' vẫn còn (conf: {re_match.confidence:.2f}) -> Bấm lại tại ({tap_pos[0]}, {tap_pos[1]})...")
                    self._tap(tap_pos[0], tap_pos[1], label=f"Retry {template_key}")
                    last_retry = time.perf_counter()
            except Exception:
                pass
            time.sleep(0.005)
        logger.warning(f"⚠️ Hết thời gian chờ đóng popup '{template_key}'.")
        return False

    def _check_and_dismiss_ok_immediate(self, max_wait_sec: float = 0.5) -> bool:
        """
        KIỂM TRA VÀ BẤM NÚT OK TỨC THÌ TẠI MỌI ĐIỂM then chốt (sau click dòng, trước cược EVEN, sau reset):
        - Nếu phát hiện có nút OK (Cuộn thư hoặc Arale): Bấm ngay lập tức và đảm bảo đóng sạch!
        - Trả về True nếu có popup OK bị đóng, False nếu màn hình sạch.
        """
        t_start = time.perf_counter()
        dismissed = False
        while time.perf_counter() - t_start < max_wait_sec:
            self._check_stop()
            try:
                frame = self._wait_for_frame(timeout=0.2)
                if frame is not None:
                    match_ok, ok_key = self._find_ok_button(frame)
                    if match_ok and match_ok.found:
                        cx, cy = match_ok.center
                        logger.warning(f"🛑 [Popup OK Phát Hiện] Bấm OK ngay lập tức tại ({cx}, {cy})!")
                        self._tap(cx, cy, label="Click OK Immediate")
                        self._confirm_ok_closed(max_wait=1.2)
                        dismissed = True
                        break
            except Exception:
                pass
            time.sleep(0.04)
        return dismissed

    def _confirm_ok_closed(self, max_wait: float = 0.6) -> bool:
        """
        GIÁM SÁT VÀ ĐÓNG TRIỆT ĐỂ NÚT OK (Không bị hụt / lệch):
        Quét trực tiếp qua _find_ok_button.
        Nếu nút OK vẫn còn trên màn hình sau 0.15s -> tap lại ngay vào tâm hiện tại.
        """
        c_start = time.perf_counter()
        last_retry = c_start

        while time.perf_counter() - c_start < max_wait:
            try:
                frame = self._wait_for_frame(timeout=0.2)
                match_ok, ok_key = self._find_ok_button(frame)
                if not match_ok or not match_ok.found:
                    logger.info("✅ Nút/Popup OK đã đóng hoàn toàn khỏi màn hình.")
                    return True

                if time.perf_counter() - last_retry > 0.15:
                    cx, cy = match_ok.center
                    logger.info(f"🔄 Nút OK vẫn còn tại ({cx}, {cy}) (conf: {match_ok.confidence:.2f}) -> Tap lại chính xác...")
                    self._tap(cx, cy, label="Retry Click OK")
                    last_retry = time.perf_counter()
            except Exception:
                pass
            time.sleep(0.02)

        return True

    def wait_for_template(
        self,
        template_key: str,
        threshold: Optional[float] = None,
        roi: Optional[Rect] = None,
        timeout: float = 10.0,
        label: str = ""
    ) -> Optional[MatchResult]:
        """
        CHỜ MÀN HÌNH XUẤT HIỆN HÌNH ẢNH:
        Liên tục quét frame theo thời gian thực cho đến khi template xuất hiện trên màn hình.
        Phản hồi ngay tức thì khi xuất hiện, không chờ theo giây cố định.
        """
        thresh = threshold or self.cfg.default_threshold
        lbl = label or template_key
        t_start = time.perf_counter()
        while time.perf_counter() - t_start < timeout:
            self._check_stop()
            try:
                frame = self._wait_for_frame()
                match = self.vision.find_template(frame, template_key, threshold=thresh, roi=roi)
                if match.found:
                    elapsed = time.perf_counter() - t_start
                    logger.info(f"👁️ [{lbl}] Màn hình đã xuất hiện '{template_key}' sau {elapsed:.2f}s (conf: {match.confidence:.2f}) tại {match.center}")
                    return match
            except BotStoppedException:
                raise
            except Exception:
                pass
            time.sleep(0.005)
        return None

    def _find_reward_button(self, frame: np.ndarray) -> Tuple[Optional[MatchResult], str]:
        """
        Tìm nút nhận thưởng, tự động hỗ trợ song song cả 2 ngôn ngữ:
        - Tiếng Việt: 'rut_lui_btn' (Rút lui)
        - Tiếng Anh: 'withdraw_btn' (Withdraw)
        """
        match_vi = self.vision.find_template(
            frame, "rut_lui_btn", threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi
        )
        if match_vi.found:
            return match_vi, "rut_lui_btn"

        match_en = self.vision.find_template(
            frame, "withdraw_btn", threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi
        )
        if match_en.found:
            return match_en, "withdraw_btn"

        return None, ""

    def _find_ok_button(self, frame: np.ndarray) -> Tuple[Optional[MatchResult], str]:
        """
        Tìm nút OK trên popup (Cuộn thư hoặc Arale/Warrior Gem).
        Dùng template matching chuẩn với ngưỡng 0.60 (nhận diện tốt cả khi popup vừa nở to).
        """
        for key in ["ok_btn", "ok_btn_vi"]:
            match = self.vision.find_template(
                frame, key, threshold=0.60, roi=self.cfg.ok_roi
            )
            if match.found:
                return match, key

        return None, ""

    def wait_and_dismiss_all_popups(self, max_wait_sec: float = 3.5) -> bool:
        """
        Theo dõi màn hình và bấm đóng tất cả các popup (OK / Rút lui / Withdraw / Warrior Gem) cho tới khi màn hình hoàn toàn sạch.
        Đảm bảo phải bấm thành công và popup biến mất mới kết thúc!
        """
        t_start = time.perf_counter()
        dismissed_any = False

        while time.perf_counter() - t_start < max_wait_sec:
            try:
                frame = self._wait_for_frame()
            except Exception:
                time.sleep(0.005)
                continue

            # 1. Kiểm tra nút OK (Giao diện mới & cũ)
            match_ok, ok_key = self._find_ok_button(frame)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                popup_label = "Warrior Gem" if p_type == "WARRIOR_GEM" else "Hết lượt / Vật phẩm"
                logger.info(f"🔔 [Popup {popup_label}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm OK!")
                self._tap(cx, cy, label=f"Click OK ({popup_label})")
                self._confirm_ok_closed(max_wait=1.2)
                dismissed_any = True
                t_start = time.perf_counter()
                time.sleep(0.25)
                continue

            # 2. Kiểm tra nút Rút lui / Withdraw (Song ngữ Việt - Anh)
            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🔔 [Popup {btn_name}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm {btn_name}!")
                self._tap(cx, cy, label=f"Click {btn_name}")
                self._confirm_button_closed(btn_key, threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi, tap_pos=(cx, cy), max_wait=1.2)
                dismissed_any = True
                t_start = time.perf_counter()
                time.sleep(0.25)
                continue

            # Nếu không thấy popup nào xuất hiện -> màn hình sạch, thoát ngay lập tức!
            break

        return dismissed_any

    def dismiss_popup_if_present(self, frame: Optional[np.ndarray] = None, max_attempts: int = 1) -> bool:
        """Kiểm tra nhanh xem có popup nào đang kẹt không và bấm đóng ngay (hỗ trợ kiểm tra trực tiếp trên frame)."""
        if frame is not None:
            match_ok, ok_key = self._find_ok_button(frame)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                lbl = "Warrior Gem" if p_type == "WARRIOR_GEM" else "Popup OK"
                logger.info(f"🔔 [{lbl}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm OK!")
                self._tap(cx, cy, label=f"Click OK ({lbl})")
                self._confirm_ok_closed(max_wait=1.2)
                time.sleep(0.35)
                return True

            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🔔 [{btn_name}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm {btn_name}!")
                self._tap(cx, cy, label=f"Click {btn_name}")
                self._confirm_button_closed(btn_key, threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi, tap_pos=(cx, cy), max_wait=1.2)
                time.sleep(0.35)
                return True

            return False

        return self.wait_and_dismiss_all_popups(max_wait_sec=0.5)

    # ==================== CÁC STATE CHI TIẾT ====================

    def enter_vip_section(self, vip_type: str = "vip7") -> bool:
        """Chuyển vào Tab VIP7 hoặc Tab VIP9 tức thì bằng toạ độ cố định qua Persistent Shell."""
        self._check_stop()
        if self.active_tab == vip_type:
            return True

        pos = self.cfg.vip7_tab_pos if vip_type == "vip7" else self.cfg.vip9_tab_pos
        self._tap(pos[0], pos[1], label=f"Click Tab {vip_type.upper()}")
        time.sleep(0.12)
        self.active_tab = vip_type
        return True

    def choose_even_odd(self, timeout: float = 0.0) -> bool:
        """
        Bấm nút CHẴN (EVEN) hoặc LẺ (ODD) trực tiếp theo toạ độ cố định.
        Nút này luôn nằm cố định trên giao diện game (không cần quét template chờ đợi).
        """
        self._check_stop()
        strategy = getattr(self.cfg, "even_odd_strategy", "even").lower()
        if strategy == "random":
            choice = random.choice(["even", "odd"])
        elif strategy == "odd":
            choice = "odd"
        else:
            choice = "even"

        if choice == "odd":
            cx, cy = self.cfg.odd_btn_pos
            logger.info(f"🎲 [Cược ODD] Bấm nút LẺ (ODD) tại ({cx}, {cy})")
            self._tap(cx, cy, label="Select ODD")
        else:
            cx, cy = self.cfg.even_btn_pos
            logger.info(f"🎲 [Cược EVEN] Bấm nút CHẴN (EVEN) tại ({cx}, {cy})")
            self._tap(cx, cy, label="Select EVEN")
        return True

    def wait_and_handle_reward_popup(self, max_wait_sec: Optional[float] = None) -> str:
        """
        THEO DÕI VÀ GIẢI QUYẾT TOÀN BỘ POPUP SAU KHI CƯỢC:
        - Quét màn hình thời gian thực:
          + Thấy bất kỳ nút [OK] nào (hết lượt, thiếu đồ...) -> Bấm OK ngay tại toạ độ tìm thấy, báo OUT_OF_ITEMS để chuyển sang dòng khác.
          + Thấy nút [Rút lui] / [Withdraw] -> Bấm nhận quà.
        - Hoàn toàn KHÔNG spam tap mù vào toạ độ dòng item (538, 1217).
        - Bỏ qua hoạt ảnh bằng cú tap tại vùng trung tâm bàn cờ an toàn (y=750).
        """
        wait_limit = max_wait_sec or self.cfg.api_loading_timeout
        t_start = time.perf_counter()
        logger.info("⏳ Đang theo dõi và xử lý popup (OK / Rút lui / Withdraw)...")

        last_skip_tap = 0.0
        while time.perf_counter() - t_start < wait_limit:
            self._check_stop()
            try:
                frame = self._wait_for_frame(timeout=1.0)
            except BotStoppedException:
                raise
            except Exception:
                continue

            elapsed = time.perf_counter() - t_start

            # 1. Thấy nút OK ở đâu bấm ngay ở đó -> Báo OUT_OF_ITEMS để qua khay/dòng khác
            match_ok, ok_key = self._find_ok_button(frame)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                logger.info(f"⚠️ [Popup OK] Xuất hiện sau {elapsed:.2f}s tại ({cx}, {cy}) -> Bấm OK và chuyển dòng khác!")
                self._tap(cx, cy, label="Click OK")
                time.sleep(0.18)
                return "OUT_OF_ITEMS"

            # 2. Xử lý nút [Rút lui] / [Withdraw] (Song ngữ)
            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🎉 [Nhận quà] Màn hình xuất hiện nút '{btn_name}' sau {elapsed:.2f}s (conf: {match_btn.confidence:.2f}) -> Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label=f"Click {btn_name}")
                time.sleep(0.18)
                return "SUCCESS"

            # 3. Skip hoạt ảnh lắc xúc xắc an toàn: Tap tại vùng bàn cờ (540, 750)
            now = time.perf_counter()
            safe_skip_y = int(0.39 * self.cfg.target_height)
            safe_skip_x = int(0.50 * self.cfg.target_width)
            if elapsed >= 0.15 and (now - last_skip_tap >= 0.22):
                self.capture.tap(safe_skip_x, safe_skip_y, jitter_px=4)
                last_skip_tap = now

            time.sleep(0.015)

        logger.warning(f"⚠️ Hết thời gian chờ nhận quà ({wait_limit}s).")
        return "NO_POPUP"

    def play_diamond_row(self, max_rounds: int, vip_name: str = "VIP") -> bool:
        """
        Chơi các lượt nhận quà cho 1 dòng Kim Cương:
        1. Bấm chọn dòng để mở bàn cược.
        2. Chờ phản hồi từ game (0.35s - 0.45s):
           - Nếu có Popup Cuộn Giấy (Hết đồ / Không thể đổi) -> Bấm OK và THOÁT DÒNG NGAY (không bấm EVEN).
        3. Chỉ khi dòng hợp lệ -> Mới spam bấm nút EVEN chờ máy chủ xử lý.
        4. Xử lý chuỗi nhận quà:
           - Popup Arale hết lượt cược (cy >= 78% h) -> Bấm OK giải phóng.
           - Nút Withdraw / Rút lui -> Bấm nhận quà (đủ max_rounds lần).
        """
        self._check_stop()
        logger.info(f"--- [CHƠI DÒNG KIM CƯƠNG ({vip_name})] Kiểm tra dòng và nhận tối đa {max_rounds} lượt ---")

        # 1. Chờ ngắn 0.20s cho game nảy popup (nếu dòng hết đồ) rồi chụp đúng 1 frame kiểm tra
        time.sleep(0.20)
        self._check_stop()
        try:
            frame_check = self._wait_for_frame(timeout=1.0)
            if frame_check is not None:
                match_ok, ok_key = self._find_ok_button(frame_check)
                if match_ok and match_ok.found:
                    cx, cy = match_ok.center
                    logger.warning(f"🛑 [Popup Cuộn Giấy] Hết đồ -> Bấm OK ({cx}, {cy})")
                    self._tap(cx, cy, label="Click OK (Hết Đồ Đổi)")
                    self._confirm_ok_closed(max_wait=0.8)
                    return False
        except Exception:
            pass

        # 2. VÒNG LẶP CƯỢC THEO TỪNG LƯỢT CHUẨN XÁC (Không spam mù, không cược lẹm sang dòng khác)
        even_x, even_y = self.cfg.even_btn_pos
        withdraw_count = 0

        for r_idx in range(1, max_rounds + 1):
            self._check_stop()
            self._tap(even_x, even_y, label=f"Bet EVEN #{r_idx}")

            # Chờ và nhận quà của lượt này (có skip hoạt ảnh an toàn)
            t_wait_round = time.perf_counter()
            round_claimed = False
            last_skip_tap = 0.0

            while time.perf_counter() - t_wait_round < 6.0:
                self._check_stop()
                try:
                    f_round = self._wait_for_frame(timeout=0.6)
                except Exception:
                    continue

                now = time.perf_counter()
                elapsed = now - t_wait_round

                # A. Ưu tiên 1: Nút Withdraw / Rút lui
                match_btn, btn_key = self._find_reward_button(f_round)
                if match_btn and match_btn.found:
                    cx, cy = match_btn.center
                    btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                    withdraw_count += 1
                    logger.info(f"🎉 [{vip_name}] Nhận quà #{withdraw_count}/{max_rounds} ({btn_name})")
                    self._tap(cx, cy, label=f"Click {btn_name}")
                    # Xác nhận nút đóng hoàn toàn, nếu chưa đóng thì tap lại
                    self._confirm_button_closed(btn_key, threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi, tap_pos=(cx, cy), max_wait=1.2)
                    time.sleep(0.15)
                    round_claimed = True
                    break

                # B. Ưu tiên 2: Popup OK (hết lượt / thông báo)
                match_ok, ok_key = self._find_ok_button(f_round)
                if match_ok and match_ok.found:
                    cx, cy = match_ok.center
                    logger.warning(f"⚠️ [{vip_name}] Popup OK -> Bấm đóng và kết thúc dòng.")
                    self._tap(cx, cy, label="Click OK")
                    self._confirm_ok_closed(max_wait=0.8)
                    return True

                # C. Skip hoạt ảnh lắc xúc xắc an toàn ở vùng trên (không dính dòng item)
                safe_skip_y = int(0.39 * self.cfg.target_height)
                safe_skip_x = int(0.50 * self.cfg.target_width)
                if elapsed >= 0.15 and (now - last_skip_tap >= 0.22):
                    self.capture.tap(safe_skip_x, safe_skip_y, jitter_px=4)
                    last_skip_tap = now

                time.sleep(0.02)

            if not round_claimed:
                logger.warning(f"⚠️ [{vip_name}] Hết thời gian chờ quà #{r_idx}")
                break

            time.sleep(0.18)

        logger.info(f"🎉 [{vip_name}] Hoàn tất dòng Kim Cương (Đã cược và nhận {withdraw_count}/{max_rounds} lần quà).")

        # CHỐT CHẶN: Dọn sạch nút Withdraw còn sót hoặc modal OK
        try:
            f_clean = self._wait_for_frame(timeout=0.3)
            # 1. Nếu còn nút Withdraw sót lại -> bấm nhận nốt
            m_btn, b_key = self._find_reward_button(f_clean)
            if m_btn and m_btn.found:
                cx, cy = m_btn.center
                b_name = "Rút lui" if b_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🎉 [{vip_name}] Nhận quà còn sót ({b_name})")
                self._tap(cx, cy, label=f"Dismiss Tail {b_name}")
                self._confirm_button_closed(b_key, threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi, tap_pos=(cx, cy), max_wait=1.2)
                f_clean = self._wait_for_frame(timeout=0.3)

            # 2. Nếu còn modal OK -> bấm đóng
            m_ok, _ = self._find_ok_button(f_clean)
            if m_ok and m_ok.found:
                self._tap(m_ok.center[0], m_ok.center[1], label="Dismiss Remaining OK")
                self._confirm_ok_closed(max_wait=0.8)
        except Exception:
            pass

        return True

    def process_vip_section(self, vip_type: str = "vip7"):
        """
        Quản lý toàn bộ quy trình cho 1 tab VIP:
        - Chuyển vào Tab VIP 1 lần duy nhất khi bắt đầu.
        - Dòng 1 và Dòng 2: Soi và chơi ở vị trí ban đầu (không bị che khuất).
        - Dòng 3: Bị che khuất ở vị trí ban đầu -> Tự động kéo khay item lên để hiển thị đầy đủ rồi mới soi và chơi!
        - Dòng 4 (ở VIP9): Xong 3 lượt dòng 3 (hoặc không có kim cương), tiếp tục kéo lên để soi và chơi Dòng 4!
        - Sau khi xong tất cả các dòng: Cuộn trả về đầu trang để chuẩn bị cho chu kỳ tiếp theo.
        """
        self._check_stop()
        max_rounds = self.cfg.vip7_rounds_per_row if vip_type == "vip7" else self.cfg.vip9_rounds_per_row

        if vip_type == "vip7":
            # 1. Chuyển vào Tab VIP7 1 lần duy nhất
            self.enter_vip_section("vip7")
            initial_rows = self.cfg.vip7_initial_rows

            # Quét Dòng 1 và Dòng 2 ở vị trí ban đầu (dùng đúng 1 frame duy nhất)
            frame = self._wait_for_frame()

            # KIỂM TRA ĐẦU TAB: Dọn sạch nếu có nút Withdraw kẹt hoặc popup Warrior Gem
            match_btn_start, btn_key_start = self._find_reward_button(frame)
            if match_btn_start and match_btn_start.found:
                cx, cy = match_btn_start.center
                b_name = "Rút lui" if btn_key_start == "rut_lui_btn" else "Withdraw"
                logger.info(f"🎉 [VIP7] Nhận quà tồn đọng ({b_name})")
                self._tap(cx, cy, label=f"Dismiss Initial {b_name}")
                self._confirm_button_closed(btn_key_start, threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi, tap_pos=(cx, cy), max_wait=1.2)
                frame = self._wait_for_frame()

            match_ok_start, _ = self._find_ok_button(frame)
            if match_ok_start and match_ok_start.found:
                ok_x, ok_y = match_ok_start.center
                logger.info(f"✨ [VIP7] Phát hiện Popup Warrior Gem/OK tại ({ok_x}, {ok_y}) -> Bấm OK giải phóng ngay!")
                self._tap(ok_x, ok_y, label="Dismiss Initial OK")
                self._confirm_ok_closed(max_wait=0.8)
                frame = self._wait_for_frame()

            for idx, target_row in enumerate(initial_rows):
                self._check_stop()
                match, target_type = self.vision.check_row_for_targets(
                    frame=frame,
                    row_roi=target_row,
                    min_threshold=self.cfg.diamond_threshold,
                    enable_phuc_tung=self.cfg.enable_phuc_tung,
                    phuc_tung_threshold=self.cfg.phuc_tung_threshold
                )

                if match.found:
                    if self.vision.is_input_zero(frame, target_row):
                        logger.info(f"⏩ [VIP7] Dòng #{idx + 1} Input = 0 -> Bỏ qua")
                        continue

                    cx = self.cfg.target_width // 2
                    cy = target_row.center[1]
                    logger.info(f"💎 [VIP7] Chọn Dòng #{idx + 1}")
                    self._tap(cx, cy, label=f"Click Center Row #{idx + 1}")
                    self.play_diamond_row(max_rounds, vip_name="VIP7")
                    frame = self._wait_for_frame()

            # 2. Xử lý Dòng 3 VIP7: Kéo cuộn lên 1 lần để dòng 3 lộ ra hoàn toàn
            self._check_stop()
            self._swipe_tray_up(label="VIP7")
            self._check_stop()
            frame = self._wait_for_frame()

            w, h = self.cfg.target_width, self.cfg.target_height
            # Vùng khay riêng biệt cho Dòng 3 VIP7 sau khi cuộn (y từ 75% đến 93% chiều cao: 1440 -> 1785)
            # Tránh quét nhầm lên Dòng 2 phía trên (y ≈ 1220)!
            tray_roi = Rect(x=int(0.5694 * w), y=int(0.75 * h), w=int(0.2130 * w), h=int(0.18 * h))

            match_r3, target_type_r3, roi_r3 = self._check_candidate_rois(
                frame=frame,
                candidate_rois=self.cfg.vip7_scrolled_row3_candidates,
                min_threshold=self.cfg.diamond_threshold,
                enable_phuc_tung=self.cfg.enable_phuc_tung,
                phuc_tung_threshold=self.cfg.phuc_tung_threshold,
                fallback_tray_roi=tray_roi
            )

            if match_r3.found and roi_r3:
                if self.vision.is_input_zero(frame, roi_r3):
                    logger.info("⏩ [VIP7] Dòng 3 Input = 0 -> Bỏ qua")
                else:
                    cx = self.cfg.target_width // 2
                    cy = roi_r3.center[1]
                    logger.info("💎 [VIP7] Chọn Dòng 3")
                    self._tap(cx, cy, label="Click Row 3 (Scrolled)")
                    self.play_diamond_row(max_rounds, vip_name="VIP7")

            # 3. Kết thúc VIP7 -> Luôn cuộn trả khay item về lại đầu trang
            self._swipe_tray_down(label="VIP7", times=1)

        else:
            # 1. Chuyển vào Tab VIP9 1 lần duy nhất từ VIP7
            self.enter_vip_section("vip9")
            initial_rows = self.cfg.vip9_initial_rows

            # Quét Dòng 1 và Dòng 2 ở vị trí ban đầu (dùng đúng 1 frame duy nhất)
            frame = self._wait_for_frame()

            # KIỂM TRA ĐẦU TAB: Dọn sạch nếu có nút Withdraw kẹt hoặc popup Warrior Gem
            match_btn_start, btn_key_start = self._find_reward_button(frame)
            if match_btn_start and match_btn_start.found:
                cx, cy = match_btn_start.center
                b_name = "Rút lui" if btn_key_start == "rut_lui_btn" else "Withdraw"
                logger.info(f"🎉 [VIP9] Nhận quà tồn đọng ({b_name})")
                self._tap(cx, cy, label=f"Dismiss Initial {b_name}")
                self._confirm_button_closed(btn_key_start, threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi, tap_pos=(cx, cy), max_wait=1.2)
                frame = self._wait_for_frame()

            match_ok_start, _ = self._find_ok_button(frame)
            if match_ok_start and match_ok_start.found:
                ok_x, ok_y = match_ok_start.center
                logger.info(f"✨ [VIP9] Popup Warrior Gem/OK -> Bấm OK ({ok_x}, {ok_y})")
                self._tap(ok_x, ok_y, label="Dismiss Initial OK")
                self._confirm_ok_closed(max_wait=0.8)
                frame = self._wait_for_frame()

            for idx, target_row in enumerate(initial_rows):
                self._check_stop()
                match, target_type = self.vision.check_row_for_targets(
                    frame=frame,
                    row_roi=target_row,
                    min_threshold=self.cfg.diamond_threshold,
                    enable_phuc_tung=self.cfg.enable_phuc_tung,
                    phuc_tung_threshold=self.cfg.phuc_tung_threshold
                )

                if match.found:
                    if self.vision.is_input_zero(frame, target_row):
                        logger.info(f"⏩ [VIP9] Dòng #{idx + 1} Input = 0 -> Bỏ qua")
                        continue

                    cx = self.cfg.target_width // 2
                    cy = target_row.center[1]
                    logger.info(f"💎 [VIP9] Chọn Dòng #{idx + 1}")
                    self._tap(cx, cy, label=f"Click Center Row #{idx + 1}")
                    self.play_diamond_row(max_rounds, vip_name="VIP9")
                    frame = self._wait_for_frame()

            # 2. Xử lý Dòng 3 và Dòng 4 VIP9:
            # Cuộn lên 1 LẦN DUY NHẤT để đưa CẢ Dòng 3 và Dòng 4 vào tầm nhìn rõ nét
            self._check_stop()
            self._swipe_tray_up(label="VIP9")
            self._check_stop()
            frame = self._wait_for_frame()

            w, h = self.cfg.target_width, self.cfg.target_height
            # Vùng khay riêng biệt cho Dòng 3 (y từ 60% đến 76.5% chiều cao màn hình: 1152 -> 1468)
            tray_roi_r3 = Rect(x=int(0.5694 * w), y=int(0.60 * h), w=int(0.2130 * w), h=int(0.165 * h))
            # Vùng khay riêng biệt cho Dòng 4 (y từ 76.5% đến 93% chiều cao màn hình: 1468 -> 1784)
            tray_roi_r4 = Rect(x=int(0.5694 * w), y=int(0.765 * h), w=int(0.2130 * w), h=int(0.165 * h))

            # Soi Dòng 3
            match_r3, target_type_r3, roi_r3 = self._check_candidate_rois(
                frame=frame,
                candidate_rois=self.cfg.vip9_scrolled_row3_candidates,
                min_threshold=self.cfg.diamond_threshold,
                enable_phuc_tung=self.cfg.enable_phuc_tung,
                phuc_tung_threshold=self.cfg.phuc_tung_threshold,
                fallback_tray_roi=tray_roi_r3
            )

            if match_r3.found and roi_r3:
                if self.vision.is_input_zero(frame, roi_r3):
                    logger.info("⏩ [VIP9] Dòng 3 Input = 0 -> Bỏ qua")
                else:
                    cx = self.cfg.target_width // 2
                    cy = roi_r3.center[1]
                    logger.info("💎 [VIP9] Chọn Dòng 3")
                    self._tap(cx, cy, label="Click Row 3 (Scrolled)")
                    self.play_diamond_row(max_rounds, vip_name="VIP9")
                    # Sau khi chơi xong Dòng 3, cập nhật lại frame mới nhất
                    frame = self._wait_for_frame()

            # 3. Soi Dòng 4 (ở vị trí đáy đã lộ rõ sau cú cuộn):
            match_r4, target_type_r4, roi_r4 = self._check_candidate_rois(
                frame=frame,
                candidate_rois=self.cfg.vip9_scrolled_row4_candidates,
                min_threshold=self.cfg.diamond_threshold,
                enable_phuc_tung=self.cfg.enable_phuc_tung,
                phuc_tung_threshold=self.cfg.phuc_tung_threshold,
                fallback_tray_roi=tray_roi_r4
            )

            if match_r4.found and roi_r4:
                if self.vision.is_input_zero(frame, roi_r4):
                    logger.info("⏩ [VIP9] Dòng 4 Input = 0 -> Bỏ qua")
                else:
                    cx = self.cfg.target_width // 2
                    cy = roi_r4.center[1]
                    logger.info("💎 [VIP9] Chọn Dòng 4")
                    self._tap(cx, cy, label="Click Row 4 (Scrolled)")
                    self.play_diamond_row(max_rounds, vip_name="VIP9")

            # 4. Kết thúc VIP9 -> Luôn cuộn trả khay item về lại đầu trang
            self._swipe_tray_down(label="VIP9", times=1)

    def reset_cycle(self) -> bool:
        """
        Bấm Refresh/Reset để làm mới vòng lặp:
        - Bấm nút Reset tại toạ độ cố định qua Persistent Shell (<5ms).
        - Chờ và dập tắt triệt để popup Warrior Gem (nếu nổ) ngay tại chỗ!
        - Đảm bảo màn hình sạch 100% không còn popup che trước khi sang vòng mới.
        """
        self._check_stop()
        cx, cy = self.cfg.reset_btn_pos
        logger.info(f"🔄 Bấm Reset ({cx}, {cy})")
        self._tap(cx, cy, label="Reset Cycle")
        time.sleep(0.35)

        # Quét kiểm tra trong 0.8s: Nếu nổ popup Warrior Gem -> bấm OK đóng dứt điểm ngay!
        t_check = time.perf_counter()
        while time.perf_counter() - t_check < 0.8:
            self._check_stop()
            try:
                frame = self._wait_for_frame(timeout=0.3)
                if frame is not None:
                    match_ok, _ = self._find_ok_button(frame)
                    if match_ok and match_ok.found:
                        ok_cx, ok_cy = match_ok.center
                        logger.info(f"✨ [Reset] Popup Warrior Gem -> Bấm OK ({ok_cx}, {ok_cy})")
                        self._tap(ok_cx, ok_cy, label="Click OK (Warrior Gem)")
                        self._confirm_ok_closed(max_wait=1.0)
                        break
            except Exception:
                pass
            time.sleep(0.05)

        return True

    # ==================== ĐIỀU PHỐI VÒNG LẶP ====================

    def run_one_cycle(self) -> bool:
        """
        Chạy 1 chu kỳ hoàn chỉnh theo quy trình giữ nguyên Tab sau Reset:
        - Bắt đầu từ VIP hiện tại (current_vip).
        - Quét và cược VIP hiện tại.
        - Chuyển sang VIP còn lại để quét và cược.
        - Bấm Reset -> Ở NGUYÊN TẠI VIP ĐÓ cho chu kỳ tiếp theo (không nhảy tab vội).
        """
        self._check_stop()
        self.cycle_count += 1
        cycle_start = time.perf_counter()
        first_vip = self.current_vip
        second_vip = "vip9" if first_vip == "vip7" else "vip7"

        logger.info(f"\n==================== BẮT ĐẦU VÒNG #{self.cycle_count} ({first_vip.upper()} -> {second_vip.upper()} -> RESET) ====================")

        try:
            # 1. Quét và cược VIP hiện tại đang đứng
            self.process_vip_section(first_vip)
            self._check_stop()

            # 2. Chuyển sang VIP còn lại quét và cược
            self.process_vip_section(second_vip)
            self._check_stop()

            # 3. Bấm Reset làm mới chu kỳ
            self.reset_cycle()

            # Sau khi Reset, game giữ nguyên tab second_vip -> đặt làm tab khởi đầu vòng sau!
            self.current_vip = second_vip

            total_time_sec = time.perf_counter() - cycle_start
            self.success_count += 1
            logger.info(f"🏁 Hoàn thành vòng #{self.cycle_count} trong {total_time_sec:.2f}s! (Vòng sau ở lại: {self.current_vip.upper()})")
            return True
        except BotStoppedException:
            logger.info("🛑 Bot đã dừng ngay lập tức theo lệnh người dùng.")
            return False

    def run_forever(self):
        """Vòng lặp vô hạn chạy liên tục."""
        logger.info("Bắt đầu vòng lặp vô hạn. Nhấn Ctrl+C để dừng.")
        try:
            while True:
                self.run_one_cycle()
        except KeyboardInterrupt:
            logger.info("Nhận tín hiệu dừng từ người dùng.")
        finally:
            logger.info(f"Tổng kết: Hoàn thành {self.cycle_count} vòng | Thành công: {self.success_count}")
            self.stop()
