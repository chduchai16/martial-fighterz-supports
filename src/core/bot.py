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
        Tìm nút OK trên popup cuộn thư, tự động hỗ trợ cả giao diện mới ('ok_btn') và giao diện cũ ('ok_btn_vi').
        Ưu tiên ok_btn_vi (nút màu cam có hoa văn mây) trong vùng ok_roi chính xác.
        """
        for key in ["ok_btn_vi", "ok_btn"]:
            match = self.vision.find_template(
                frame, key, threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
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
                self.capture.tap(cx, cy, jitter_px=2)
                dismissed_any = True
                t_start = time.perf_counter()
                time.sleep(0.15)
                continue

            # 2. Kiểm tra nút Rút lui / Withdraw (Song ngữ Việt - Anh)
            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🔔 [Popup {btn_name}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm {btn_name}!")
                self._tap(cx, cy, label=f"Click {btn_name}")
                self.capture.tap(cx, cy, jitter_px=2)
                dismissed_any = True
                t_start = time.perf_counter()
                time.sleep(0.15)
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
                self.capture.tap(cx, cy, jitter_px=2)
                return True

            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🔔 [{btn_name}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm {btn_name}!")
                self._tap(cx, cy, label=f"Click {btn_name}")
                self.capture.tap(cx, cy, jitter_px=2)
                return True

            return False

        return self.wait_and_dismiss_all_popups(max_wait_sec=0.5)

    # ==================== CÁC STATE CHI TIẾT ====================

    def enter_vip_section(self, vip_type: str = "vip7") -> bool:
        """Chuyển vào Tab 3 (VIP7) hoặc Tab 4 (VIP9) tức thì bằng toạ độ cố định qua Persistent Shell."""
        self._check_stop()
        if getattr(self, "active_tab", None) == vip_type:
            logger.info(f"=== Đang ở sẵn Tab {vip_type.upper()} -> Không cần bấm chuyển tab ===")
            return True

        logger.info(f"=== [STATE] Vào Tab {vip_type.upper()} ===")
        pos = self.cfg.vip7_tab_pos if vip_type == "vip7" else self.cfg.vip9_tab_pos
        # Bấm Tab ngay lập tức qua Persistent Shell (<5ms)
        self._tap(pos[0], pos[1], label=f"Click Tab {vip_type.upper()}")
        time.sleep(self.cfg.wait_after_vip_open)
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
        THEO DÕI VÀ NHẬN QUÀ:
        Quét màn hình liên tục chờ máy chủ trả kết quả:
        - Xuất hiện nút [Rút lui] / [Withdraw] -> Bấm nhận quà và kết thúc lượt.
        - Xuất hiện popup [OK] (Warrior Gem hoặc Hết lượt) -> Bấm OK xử lý.
        Tuyệt đối không dùng luồng spam click mù quáng.
        """
        wait_limit = max_wait_sec or self.cfg.api_loading_timeout
        t_start = time.perf_counter()
        logger.info("⏳ Đang theo dõi màn hình chờ nút Rút lui / Popup nhận quà...")

        last_skip_tap = 0.0
        while time.perf_counter() - t_start < wait_limit:
            self._check_stop()
            try:
                frame = self._wait_for_frame(timeout=0.4)
            except BotStoppedException:
                raise
            except Exception:
                continue

            elapsed = time.perf_counter() - t_start

            # 1. Kiểm tra nếu xuất hiện nút [Rút lui] / [Withdraw] (Song ngữ Việt - Anh)
            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🎉 [Nhận quà] Màn hình đã xuất hiện nút '{btn_name}' sau {elapsed:.2f}s (conf: {match_btn.confidence:.2f}) -> Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label=f"Click {btn_name}")
                time.sleep(0.18)
                return "SUCCESS"

            # 2. Kiểm tra nếu xuất hiện popup [OK]
            match_ok, ok_key = self._find_ok_button(frame)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                if p_type == "WARRIOR_GEM":
                    logger.info(f"✨ [Warrior Gem] Popup xuất hiện sau {elapsed:.2f}s! Bấm OK tại ({cx}, {cy}).")
                    self._tap(cx, cy, label="Click OK (Warrior Gem)")
                    time.sleep(0.20)
                    return "WARRIOR_GEM"
                else:
                    logger.warning(f"⚠️ [Hết lượt / Hết vật phẩm] Popup xuất hiện sau {elapsed:.2f}s! Bấm OK tại ({cx}, {cy}).")
                    self._tap(cx, cy, label="Click OK (Het luot doi)")
                    time.sleep(0.20)
                    return "OUT_OF_ITEMS"

            # 3. Bỏ qua hoạt ảnh lắc xúc xắc: Tap nhịp nhàng mỗi 0.22s vào toạ độ nút Rút lui (538, 1217)
            # Vừa skip hoạt ảnh lắc bát vừa bấm nhận quà ngay khoảnh khắc nút vừa xuất hiện!
            now = time.perf_counter()
            if elapsed >= 0.15 and (now - last_skip_tap >= 0.22):
                self.capture.tap(538, 1217, jitter_px=3)
                last_skip_tap = now

            time.sleep(0.015)

        logger.warning(f"⚠️ Hết thời gian chờ nhận quà ({wait_limit}s).")
        return "NO_POPUP"

    def play_diamond_row(self, max_rounds: int, vip_name: str = "VIP") -> bool:
        """
        Chơi các lượt nhận quà cho 1 dòng Kim Cương.
        - Sau khi bấm vào dòng, chờ kiểm tra xem có popup 'Exchange not available' / 'Not enough items' không.
        - Nếu có popup lỗi: Bấm OK đóng popup và chuyển sang dòng khác ngay (KHÔNG BẤM CƯỢC).
        - Nếu hợp lệ: Lần lượt cược từng lượt (chọn Even/Odd -> chờ xuất hiện Rút lui -> bấm Rút lui nhận quà).
        """
        self._check_stop()
        logger.info(f"--- [CHƠI DÒNG KIM CƯƠNG ({vip_name})] Chuỗi tối đa {max_rounds} lượt nhận quà ---")

        # 1. Chờ và kiểm tra phản hồi sau khi click vào dòng
        t_enter = time.perf_counter()
        while time.perf_counter() - t_enter < 0.35:
            self._check_stop()
            frame_enter = self._wait_for_frame(timeout=0.3)
            match_ok, ok_key = self._find_ok_button(frame_enter)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame_enter)
                if p_type == "WARRIOR_GEM":
                    logger.info(f"✨ [Warrior Gem] Màn hình xuất hiện popup Warrior Gem! Bấm OK tại ({cx}, {cy}).")
                    self._tap(cx, cy, label="Click OK (Warrior Gem)")
                    time.sleep(0.18)
                else:  # EXHAUSTED / Hết lượt / Không đủ vật phẩm
                    logger.warning(f"⚠️ [Không thể đổi] Dòng này hết lượt đổi hoặc không đủ vật phẩm! Bấm OK tại ({cx}, {cy}) để bỏ qua.")
                    self._tap(cx, cy, label="Click OK (Bỏ qua dòng)")
                    time.sleep(0.18)
                    return False
            # Nếu nút cược EVEN đã xuất hiện -> bàn cược đã sẵn sàng, vào chơi ngay không chờ!
            match_even = self.vision.find_template(
                frame_enter, "even_btn", threshold=0.72,
                roi=Rect(int(0.80 * self.cfg.target_width), int(0.35 * self.cfg.target_height), int(0.18 * self.cfg.target_width), int(0.15 * self.cfg.target_height))
            )
            if match_even.found:
                break
            time.sleep(0.04)

        # 2. Bắt đầu vòng lặp các lượt chơi
        round_idx = 1
        while round_idx <= max_rounds:
            self._check_stop()
            logger.info(f"👉 [{vip_name}] Lượt chơi #{round_idx}/{max_rounds}...")

            # Đợi nút cược sẵn sàng rồi bấm cược
            time.sleep(0.15)
            self.choose_even_odd()

            # Chờ phản hồi và bấm nhận quà (Rút lui / OK) - Không dùng spam click mù
            status = self.wait_and_handle_reward_popup(max_wait_sec=self.cfg.api_loading_timeout)

            if status == "OUT_OF_ITEMS":
                logger.warning(f"[{vip_name}] Dòng này đã hết lượt ở lượt #{round_idx}. Chuyển sang dòng khác!")
                return False
            elif status == "WARRIOR_GEM":
                logger.info(f"[{vip_name}] Đã đóng popup Warrior Gem, tiếp tục thực hiện lượt #{round_idx}...")
                continue
            elif status == "NO_POPUP":
                logger.info(f"[{vip_name}] Không còn popup nhận quà -> Hoàn tất dòng này.")
                return True
            else:  # SUCCESS
                logger.info(f"✅ [{vip_name}] Hoàn thành xong lượt #{round_idx}/{max_rounds}.")
                round_idx += 1
                time.sleep(0.20)

        logger.info(f"🎉 [{vip_name}] Đã hoàn thành đủ {max_rounds}/{max_rounds} lượt nhận quà.")
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

            # Quét Dòng 1 và Dòng 2 ở vị trí ban đầu (dùng 1 frame duy nhất)
            frame = self._wait_for_frame()
            if self.dismiss_popup_if_present(frame):
                time.sleep(0.10)
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
                    cx = self.cfg.target_width // 2
                    cy = target_row.center[1]
                    item_label = "Kim Cương" if target_type == "DIAMOND" else "Phục Tùng C (Obedient C)"
                    logger.info(f"💎 [VIP7] Phát hiện {item_label} ở DÒNG #{idx + 1} (conf: {match.confidence:.3f}). Bấm tại ({cx}, {cy})")
                    self._tap(cx, cy, label=f"Click Center Row #{idx + 1}")
                    self.play_diamond_row(max_rounds, vip_name="VIP7")
                    frame = self._wait_for_frame()
                else:
                    logger.info(f"[VIP7] Dòng #{idx + 1} không có Kim Cương / Phục Tùng (conf: {match.confidence:.3f}). Bỏ qua.")

            # 2. Xử lý Dòng 3 VIP7: Kéo cuộn lên 1 lần để dòng 3 lộ ra hoàn toàn
            self._check_stop()
            logger.info("[VIP7] Cuộn khay item lên để kiểm tra Dòng 3...")
            self._swipe_tray_up(label="VIP7")
            self._check_stop()
            frame = self._wait_for_frame()

            w, h = self.cfg.target_width, self.cfg.target_height
            tray_roi = Rect(x=int(0.5694 * w), y=int(0.65 * h), w=int(0.2130 * w), h=int(0.28 * h))

            match_r3, target_type_r3, roi_r3 = self._check_candidate_rois(
                frame=frame,
                candidate_rois=self.cfg.vip7_scrolled_row3_candidates,
                min_threshold=self.cfg.diamond_threshold,
                enable_phuc_tung=self.cfg.enable_phuc_tung,
                phuc_tung_threshold=self.cfg.phuc_tung_threshold,
                fallback_tray_roi=tray_roi
            )

            if match_r3.found and roi_r3:
                cx = self.cfg.target_width // 2
                cy = roi_r3.center[1]
                item_label = "Kim Cương" if target_type_r3 == "DIAMOND" else "Phục Tùng C (Obedient C)"
                logger.info(f"💎 [VIP7] Phát hiện {item_label} ở DÒNG 3 sau khi cuộn (conf: {match_r3.confidence:.3f}). Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label="Click Row 3 (Scrolled)")
                self.play_diamond_row(max_rounds, vip_name="VIP7")
            else:
                logger.info(f"[VIP7] Dòng 3 không có Kim Cương / Phục Tùng (conf: {match_r3.confidence:.3f}). Bỏ qua.")

            # 3. Kết thúc VIP7 -> Luôn cuộn trả khay item về lại đầu trang
            self._swipe_tray_down(label="VIP7", times=1)
            logger.info("[VIP7] Đã kiểm tra xong lần lượt tất cả các dòng của VIP7. Chuyển sang VIP9.")

        else:
            # 1. Chuyển vào Tab VIP9 1 lần duy nhất từ VIP7
            self.enter_vip_section("vip9")
            initial_rows = self.cfg.vip9_initial_rows

            # Quét Dòng 1 và Dòng 2 ở vị trí ban đầu (dùng 1 frame duy nhất)
            frame = self._wait_for_frame()
            if self.dismiss_popup_if_present(frame):
                time.sleep(0.10)
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
                    cx = self.cfg.target_width // 2
                    cy = target_row.center[1]
                    item_label = "Kim Cương" if target_type == "DIAMOND" else "Phục Tùng C (Obedient C)"
                    logger.info(f"💎 [VIP9] Phát hiện {item_label} ở DÒNG #{idx + 1} (conf: {match.confidence:.3f}). Bấm tại ({cx}, {cy})")
                    self._tap(cx, cy, label=f"Click Center Row #{idx + 1}")
                    self.play_diamond_row(max_rounds, vip_name="VIP9")
                    frame = self._wait_for_frame()
                else:
                    logger.info(f"[VIP9] Dòng #{idx + 1} không có Kim Cương / Phục Tùng (conf: {match.confidence:.3f}). Bỏ qua.")

            # 2. Xử lý Dòng 3 và Dòng 4 VIP9:
            # Cuộn lên 1 LẦN DUY NHẤT để đưa CẢ Dòng 3 và Dòng 4 vào tầm nhìn rõ nét
            self._check_stop()
            logger.info("[VIP9] Cuộn khay item lên để kiểm tra Dòng 3 và Dòng 4...")
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
                cx = self.cfg.target_width // 2
                cy = roi_r3.center[1]
                item_label = "Kim Cương" if target_type_r3 == "DIAMOND" else "Phục Tùng C (Obedient C)"
                logger.info(f"💎 [VIP9] Phát hiện {item_label} ở DÒNG 3 sau khi cuộn (conf: {match_r3.confidence:.3f}). Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label="Click Row 3 (Scrolled)")
                self.play_diamond_row(max_rounds, vip_name="VIP9")
                # Sau khi chơi xong Dòng 3, cập nhật lại frame mới nhất
                frame = self._wait_for_frame()
            else:
                logger.info(f"[VIP9] Dòng 3 không có Kim Cương / Phục Tùng (conf: {match_r3.confidence:.3f}). Bỏ qua.")

            # 3. Soi Dòng 4 (ở vị trí đáy đã lộ rõ sau cú cuộn):
            # Không cuộn thêm nữa tránh làm trôi dòng 4 lên trên!
            logger.info("[VIP9] Đang kiểm tra Dòng 4...")

            match_r4, target_type_r4, roi_r4 = self._check_candidate_rois(
                frame=frame,
                candidate_rois=self.cfg.vip9_scrolled_row4_candidates,
                min_threshold=self.cfg.diamond_threshold,
                enable_phuc_tung=self.cfg.enable_phuc_tung,
                phuc_tung_threshold=self.cfg.phuc_tung_threshold,
                fallback_tray_roi=tray_roi_r4
            )

            # Tự động lưu ảnh Dòng 4 vào thư mục debug_dumps
            try:
                r4_to_save = roi_r4 if roi_r4 else self.cfg.vip9_scrolled_row4_candidates[0]
                cropped_r4 = frame[r4_to_save.y : r4_to_save.y2, r4_to_save.x : r4_to_save.x2]
                cv2.imwrite(str(DEBUG_DIR / "vip9_dong_4.png"), cropped_r4)
            except Exception as e:
                logger.debug(f"Lỗi lưu ảnh debug line_4: {e}")

            if match_r4.found and roi_r4:
                cx = self.cfg.target_width // 2
                cy = roi_r4.center[1]
                item_label = "Kim Cương" if target_type_r4 == "DIAMOND" else "Phục Tùng C (Obedient C)"
                logger.info(f"💎 [VIP9] Phát hiện {item_label} ở DÒNG 4 sau khi cuộn (conf: {match_r4.confidence:.3f}). Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label="Click Row 4 (Scrolled)")
                self.play_diamond_row(max_rounds, vip_name="VIP9")
            else:
                logger.info(f"[VIP9] Dòng 4 không có Kim Cương / Phục Tùng (conf: {match_r4.confidence:.3f}). Bỏ qua.")

            # 4. Kết thúc VIP9 -> Luôn cuộn trả khay item về lại đầu trang
            self._swipe_tray_down(label="VIP9", times=1)

    def reset_cycle(self) -> bool:
        """
        Bấm Refresh/Reset để làm mới vòng lặp.
        - Bấm trực tiếp toạ độ cố định tại nút Refresh tức thì qua Persistent Shell (<5ms).
        - Đợi và xử lý triệt để popup Warrior Gem (nếu quay trúng) trước khi kết thúc!
        """
        self._check_stop()
        logger.info("=== [STATE] Bấm Reset (Refresh) ===")
        cx, cy = self.cfg.reset_btn_pos
        logger.info(f"🔄 Bấm nút Reset tại ({cx}, {cy})")
        self._tap(cx, cy, label="Reset Cycle")

        # Chờ tối thiểu 0.35s để hoạt ảnh reset / cuộn thư bắt đầu
        time.sleep(0.35)
        t_start = time.perf_counter()
        while time.perf_counter() - t_start < 1.2:
            self._check_stop()
            try:
                frame = self._wait_for_frame(timeout=0.6)
                if frame is not None and self.dismiss_popup_if_present(frame):
                    logger.info("✅ Đã xử lý xong popup Warrior Gem sau khi Reset!")
                    break
            except Exception:
                pass
            if time.perf_counter() - t_start >= 0.65:
                break

        logger.info("✅ Đã làm mới (Reset) xong chu kỳ!")
        return True

    # ==================== ĐIỀU PHỐI VÒNG LẶP ====================

    def run_one_cycle(self) -> bool:
        """
        Chạy 1 chu kỳ hoàn chỉnh theo cơ chế Đảo chiều thông minh (Alternating Loop):
        - Nếu đang ở VIP7: VIP7 -> VIP9 -> Reset -> (Ở lại VIP9)
        - Nếu đang ở VIP9: VIP9 -> VIP7 -> Reset -> (Ở lại VIP7)
        Tiết kiệm tối đa thao tác chuyển tab.
        """
        self._check_stop()
        self.cycle_count += 1
        cycle_start = time.perf_counter()
        logger.info(f"\n==================== BẮT ĐẦU VÒNG #{self.cycle_count} (Bắt đầu từ {self.current_vip.upper()}) ====================")

        try:
            # 0. Tự động đóng popup nếu có kẹt từ trước (như Warrior Gem)
            self.dismiss_popup_if_present()
            self._check_stop()

            if self.current_vip == "vip7":
                # Flow: VIP7 -> VIP9 -> Reset
                self.process_vip_section("vip7")
                self._check_stop()
                self.process_vip_section("vip9")
                self._check_stop()
                self.reset_cycle()
                # Sau khi Reset ở VIP9, vòng tiếp theo sẽ ở luôn VIP9 chơi trước!
                self.current_vip = "vip9"
            else:
                # Flow: VIP9 -> VIP7 -> Reset
                self.process_vip_section("vip9")
                self._check_stop()
                self.process_vip_section("vip7")
                self._check_stop()
                self.reset_cycle()
                # Sau khi Reset ở VIP7, vòng tiếp theo sẽ ở luôn VIP7 chơi trước!
                self.current_vip = "vip7"

            total_time_sec = time.perf_counter() - cycle_start
            self.success_count += 1
            logger.info(f"🏁 Hoàn thành vòng #{self.cycle_count} trong {total_time_sec:.2f}s! (Vòng kế tiếp sẽ bắt đầu từ: {self.current_vip.upper()})")
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
