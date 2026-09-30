"""
Module Bot: State Machine và logic tự động hoá toàn bộ chu kỳ game.
Nâng ngưỡng nhận diện Kim Cương lên >= 0.80 và tối ưu cơ chế click Rút lui đảm bảo 100% không bị sót.
"""
from enum import Enum, auto
import logging
from pathlib import Path
import random
import time
from typing import Dict, List, Optional, Set, Tuple

import cv2
import numpy as np

from capture import FastCapture
from config import BotConfig, Rect, config
from vision import MatchResult, VisionEngine

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

    def _swipe_vip9_up(self):
        """Vuốt cuộn khay item VIP9 lên để lộ Dòng 4."""
        self._check_stop()
        w, h = self.cfg.target_width, self.cfg.target_height
        x1 = int(self.cfg.swipe_vip9_start_ratio[0] * w)
        y1 = int(self.cfg.swipe_vip9_start_ratio[1] * h)
        x2 = int(self.cfg.swipe_vip9_end_ratio[0] * w)
        y2 = int(self.cfg.swipe_vip9_end_ratio[1] * h)
        logger.info(f"[VIP9] Đang cuộn khay item lên: từ ({x1}, {y1}) -> ({x2}, {y2})...")
        self.capture.swipe(x1, y1, x2, y2, duration=0.45)
        time.sleep(self.cfg.wait_after_scroll)

    def _swipe_vip9_down(self):
        """Vuốt cuộn khay item VIP9 xuống để trở về vị trí đầu, hiện full Dòng 1."""
        self._check_stop()
        w, h = self.cfg.target_width, self.cfg.target_height
        x1 = int(self.cfg.swipe_vip9_end_ratio[0] * w)
        y1 = int(self.cfg.swipe_vip9_end_ratio[1] * h)
        x2 = int(self.cfg.swipe_vip9_start_ratio[0] * w)
        y2 = int(self.cfg.swipe_vip9_start_ratio[1] * h)
        logger.info(f"[VIP9] Đang cuộn khay item xuống lại đầu trang: từ ({x1}, {y1}) -> ({x2}, {y2})...")
        self.capture.swipe(x1, y1, x2, y2, duration=0.45)
        time.sleep(self.cfg.wait_after_scroll)

    def classify_ok_popup(self, frame: np.ndarray) -> str:
        """
        Phân biệt chính xác nội dung chữ trong popup cuộn thư (Hỗ trợ Song ngữ Việt - Anh):
        - 'WARRIOR_GEM': Chứa chữ "Warrior Gem" hoặc có mũ Arale (Bấm OK và tiếp tục lượt chơi).
        - 'EXHAUSTED':
          + Tiếng Anh: "Exchange not available" hoặc "Not enough item(s) in inventory."
          + Tiếng Việt: "Không còn lượt đổi nào" hoặc "Không đủ vật phẩm trong kho đồ."
          (Bấm OK và chuyển dòng).
        """
        # 1. Kiểm tra chữ Warrior Gem bản Tiếng Anh (English UI)
        match_wg_full_en = self.vision.find_template(frame, "warrior_gem_full_en", threshold=0.75)
        if match_wg_full_en.found:
            logger.info("✨ [Popup] Nhận diện popup: 'warrior gem exchange(s) have been rolled' (English)")
            return "WARRIOR_GEM"

        match_wg_en = self.vision.find_template(frame, "warrior_gem_en", threshold=0.75)
        if match_wg_en.found:
            logger.info("✨ [Popup] Nhận diện popup: 'warrior gem' (English)")
            return "WARRIOR_GEM"

        # 2. Kiểm tra chữ Warrior Gem bản Tiếng Việt
        match_wg = self.vision.find_template(frame, "warrior_gem_text", threshold=0.55)
        if match_wg.found:
            logger.info("✨ [Popup] Nhận diện popup: 'Warrior Gem' (Tiếng Việt)")
            return "WARRIOR_GEM"

        # 3. Kiểm tra mũ Arale đặc trưng (chỉ xuất hiện trên popup quay trúng Warrior Gem)
        match_arale = self.vision.find_template(frame, "arale_header", threshold=0.80)
        if match_arale.found:
            logger.info("✨ [Popup] Nhận diện popup Warrior Gem qua mũ Arale!")
            return "WARRIOR_GEM"

        # 4. Kiểm tra thông báo hết lượt / hết vật phẩm (English UI)
        match_out_en = self.vision.find_template(frame, "out_of_items_en", threshold=0.60)
        if match_out_en.found:
            logger.info("ℹ️ [Popup] Nhận diện thông báo: 'Not enough item(s) in inventory.'")
            return "EXHAUSTED"

        match_title_en = self.vision.find_template(frame, "exchange_not_available_en", threshold=0.60)
        if match_title_en.found:
            logger.info("ℹ️ [Popup] Nhận diện tiêu đề: 'Exchange not available'")
            return "EXHAUSTED"

        # 5. Kiểm tra thông báo hết lượt / hết vật phẩm (Tiếng Việt)
        match_no_turns = self.vision.find_template(frame, "no_turns_text", threshold=0.55)
        if match_no_turns.found:
            return "EXHAUSTED"

        match_out = self.vision.find_template(frame, "out_of_items_text", threshold=0.55)
        if match_out.found:
            return "EXHAUSTED"

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
        """
        match_new = self.vision.find_template(
            frame, "ok_btn", threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
        )
        if match_new.found:
            return match_new, "ok_btn"

        match_old = self.vision.find_template(
            frame, "ok_btn_vi", threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
        )
        if match_old.found:
            return match_old, "ok_btn_vi"

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

            # 1. Kiểm tra nút Rút lui / Withdraw (Song ngữ Việt - Anh)
            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🔔 [Popup {btn_name}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm {btn_name}!")
                self._tap(cx, cy, label=f"Click {btn_name}")
                self._confirm_button_closed(btn_key, self.cfg.rut_lui_threshold, self.cfg.rut_lui_roi, (cx, cy))
                dismissed_any = True
                t_start = time.perf_counter()
                continue

            # 2. Kiểm tra nút OK (Giao diện mới & cũ)
            match_ok, ok_key = self._find_ok_button(frame)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                popup_label = "Warrior Gem" if p_type == "WARRIOR_GEM" else "Hết lượt / Vật phẩm"
                logger.info(f"🔔 [Popup {popup_label}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm OK!")
                self._tap(cx, cy, label=f"Click OK ({popup_label})")
                self._confirm_button_closed(ok_key, self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                dismissed_any = True
                t_start = time.perf_counter()
                continue

            # Nếu không thấy popup nào xuất hiện nữa -> màn hình sạch, thoát ngay không chờ
            if not dismissed_any:
                break
            time.sleep(0.005)

        return dismissed_any

    def dismiss_popup_if_present(self, max_attempts: int = 1) -> bool:
        """Kiểm tra nhanh xem có popup nào đang kẹt không và bấm đóng ngay (không chờ vô nghĩa)."""
        return self.wait_and_dismiss_all_popups(max_wait_sec=0.4)

    # ==================== CÁC STATE CHI TIẾT ====================

    def enter_vip_section(self, vip_type: str = "vip7") -> bool:
        """Chuyển vào Tab 3 (VIP7) hoặc Tab 4 (VIP9) tức thì bằng toạ độ cố định qua Persistent Shell."""
        self._check_stop()
        logger.info(f"=== [STATE] Vào Tab {vip_type.upper()} ===")
        pos = self.cfg.vip7_tab_pos if vip_type == "vip7" else self.cfg.vip9_tab_pos
        # Bấm Tab ngay lập tức qua Persistent Shell (<5ms)
        self._tap(pos[0], pos[1], label=f"Click Tab {vip_type.upper()}")
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
        CHỜ THEO DÕI MÀN HÌNH (PURE EVENT-DRIVEN):
        Chờ xúc xắc quay và theo dõi màn hình xem khi nào xuất hiện:
        1. Nút 'Rút lui' (rut_lui_btn):
           -> Bấm Rút lui, đảm bảo biến mất khỏi màn hình, trả về 'SUCCESS'
        2. Nút 'OK' (ok_btn):
           -> Phân biệt nội dung thông báo:
              - Warrior Gem: Bấm OK, đảm bảo biến mất, trả về 'WARRIOR_GEM' để tiếp tục vòng chơi!
              - Hết lượt / Hết vật phẩm: Bấm OK, đảm bảo biến mất, trả về 'OUT_OF_ITEMS' để chuyển dòng ngay!
        
        Tuyệt đối không bấm mò/blind tap theo giây cố định mà theo dõi trực tiếp hình ảnh màn hình.
        """
        wait_limit = max_wait_sec or self.cfg.api_loading_timeout
        t_start = time.perf_counter()
        logger.info(f"⏳ Đang theo dõi màn hình chờ xúc xắc xong và nút Rút lui / Popup xuất hiện...")

        while time.perf_counter() - t_start < wait_limit:
            self._check_stop()
            try:
                frame = self._wait_for_frame()
            except BotStoppedException:
                raise
            except Exception:
                time.sleep(0.005)
                continue

            elapsed = time.perf_counter() - t_start

            # 1. Kiểm tra nếu xuất hiện nút [Rút lui] / [Withdraw] (Song ngữ Việt - Anh)
            match_btn, btn_key = self._find_reward_button(frame)
            if match_btn and match_btn.found:
                cx, cy = match_btn.center
                btn_name = "Rút lui" if btn_key == "rut_lui_btn" else "Withdraw"
                logger.info(f"🎉 [Nhận quà] Màn hình đã xuất hiện nút '{btn_name}' sau {elapsed:.2f}s (conf: {match_btn.confidence:.2f}) -> Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label=f"Click {btn_name}")
                # Xác nhận nút đã đóng hoàn toàn
                self._confirm_button_closed(btn_key, self.cfg.rut_lui_threshold, self.cfg.rut_lui_roi, (cx, cy))
                return "SUCCESS"

            # 2. Kiểm tra nếu xuất hiện popup [OK] trong ROI popup
            match_ok, ok_key = self._find_ok_button(frame)
            if match_ok and match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                if p_type == "WARRIOR_GEM":
                    logger.info(f"✨ [Warrior Gem] Màn hình xuất hiện popup Warrior Gem sau {elapsed:.2f}s! Bấm OK tại ({cx}, {cy}) và tiếp tục chơi.")
                    self._tap(cx, cy, label="Click OK (Warrior Gem)")
                    self._confirm_button_closed(ok_key, self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                    return "WARRIOR_GEM"
                else:
                    logger.warning(f"⚠️ [Hết lượt / Hết vật phẩm] Màn hình xuất hiện popup hết lượt sau {elapsed:.2f}s! Bấm OK tại ({cx}, {cy}) để chuyển dòng.")
                    self._tap(cx, cy, label="Click OK (Het luot doi)")
                    self._confirm_button_closed(ok_key, self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                    return "OUT_OF_ITEMS"

            time.sleep(0.005)

        # Kiểm tra dọn dẹp popup còn sót trước khi kết thúc
        if self.wait_and_dismiss_all_popups(max_wait_sec=1.5):
            logger.info("✅ Đã xử lý đóng popup còn sót trên màn hình.")
            return "SUCCESS"

        logger.info(f"ℹ️ Không có nút Rút lui hay Popup nào xuất hiện sau {wait_limit:.1f}s -> Dòng này đã hết lượt chơi.")
        return "NO_POPUP"

    def play_diamond_row(self, max_rounds: int, vip_name: str = "VIP") -> bool:
        """
        Chơi các lượt nhận quà cho 1 dòng Kim Cương.
        - Bấm cược Even/Odd ngay lập tức (không delay).
        - Theo dõi phản hồi: nếu thiếu item, game hiện popup lỗi -> bấm OK đóng và chuyển dòng ngay.
        - Nếu hợp lệ: xúc xắc quay và hiện nút Rút lui/Withdraw -> bấm nhận quà.
        """
        self._check_stop()
        logger.info(f"--- [CHƠI DÒNG KIM CƯƠNG ({vip_name})] Chuỗi tối đa {max_rounds} lượt nhận quà ---")

        round_idx = 1
        while round_idx <= max_rounds:
            self._check_stop()
            logger.info(f"👉 [{vip_name}] Lượt chơi #{round_idx}/{max_rounds}...")

            # Bấm ngay nút EVEN hoặc ODD theo chiến thuật (toạ độ cố định, 0s delay)
            self.choose_even_odd()

            # Chờ phản hồi từ game (Loading -> Kết quả xúc xắc & Rút lui HOẶC Popup không đủ vật phẩm)
            status = self.wait_and_handle_reward_popup(max_wait_sec=self.cfg.api_loading_timeout)

            if status == "OUT_OF_ITEMS":
                logger.warning(f"[{vip_name}] Dòng này không đủ vật phẩm / hết lượt ở lượt #{round_idx}. Chuyển sang dòng khác ngay!")
                self.dismiss_popup_if_present()
                return False
            elif status == "WARRIOR_GEM":
                logger.info(f"[{vip_name}] Đã đóng popup Warrior Gem, tiếp tục thực hiện lượt #{round_idx}...")
                self.dismiss_popup_if_present()
                continue
            elif status == "NO_POPUP":
                logger.info(f"[{vip_name}] Tab {vip_name} không còn popup nhận quà -> Hoàn tất dòng này.")
                self.dismiss_popup_if_present()
                return True
            else:  # SUCCESS
                logger.info(f"✅ [{vip_name}] Hoàn thành xong lượt #{round_idx}/{max_rounds}.")
                round_idx += 1
                self.dismiss_popup_if_present()

        logger.info(f"🎉 [{vip_name}] Đã hoàn thành đủ {max_rounds}/{max_rounds} lượt nhận quà.")
        self.dismiss_popup_if_present()
        return True

    def process_vip_section(self, vip_type: str = "vip7"):
        """
        Quản lý toàn bộ quy trình cho 1 tab VIP:
        - Chuyển vào Tab VIP 1 lần duy nhất khi bắt đầu.
        - Quét tất cả các dòng trong tab VIP.
        - Nếu có dòng nào xuất hiện Kim Cương (ngưỡng >= 0.80): Chơi hết số lượt cho dòng đó.
        - Sau khi chơi xong 1 dòng (đang ở sẵn trong tab VIP), tiếp tục quét ngay các dòng còn lại mà không cần bấm lại Tab.
        - Chỉ chuyển sang VIP tiếp theo (hoặc Reset) khi đã kiểm tra và chơi hết TẤT CẢ các dòng có Kim Cương!
        """
        self._check_stop()
        max_rounds = self.cfg.vip7_rounds_per_row if vip_type == "vip7" else self.cfg.vip9_rounds_per_row
        processed_rows: Set[int] = set()

        if vip_type == "vip7":
            # 1. Chuyển vào Tab VIP7 1 lần duy nhất
            self.enter_vip_section("vip7")
            rows = self.cfg.vip7_rows

            for idx, target_row in enumerate(rows):
                self._check_stop()
                self.dismiss_popup_if_present()
                frame = self._wait_for_frame()
                match, target_type = self.vision.check_row_for_targets(
                    frame=frame,
                    row_roi=target_row,
                    min_threshold=self.cfg.diamond_threshold,
                    enable_phuc_tung=self.cfg.enable_phuc_tung,
                    phuc_tung_threshold=self.cfg.phuc_tung_threshold
                )

                if match.found:
                    cx, cy = target_row.center
                    item_label = "Kim Cương" if target_type == "DIAMOND" else "Phục Tùng C (Obedient C)"
                    logger.info(f"💎 [VIP7] Phát hiện {item_label} ở DÒNG #{idx + 1} (conf: {match.confidence:.3f}). Bấm tại ({cx}, {cy})")
                    self._tap(cx, cy, label=f"Click Center Row #{idx + 1}")
                    self.play_diamond_row(max_rounds, vip_name="VIP7")
                else:
                    logger.info(f"[VIP7] Dòng #{idx + 1} không có Kim Cương / Phục Tùng (conf: {match.confidence:.3f}). Bỏ qua.")

            logger.info("[VIP7] Đã kiểm tra xong lần lượt tất cả các dòng của VIP7. Chuyển sang VIP9.")

        else:
            # 1. Chuyển vào Tab VIP9 1 lần duy nhất từ VIP7
            self.enter_vip_section("vip9")
            initial_rows = self.cfg.vip9_initial_rows

            # Quét lần lượt từ trên xuống dưới các dòng ban đầu (Dòng 1 -> Dòng 2 -> Dòng 3)
            for idx, target_row in enumerate(initial_rows):
                self._check_stop()
                self.dismiss_popup_if_present()
                frame = self._wait_for_frame()
                match, target_type = self.vision.check_row_for_targets(
                    frame=frame,
                    row_roi=target_row,
                    min_threshold=self.cfg.diamond_threshold,
                    enable_phuc_tung=self.cfg.enable_phuc_tung,
                    phuc_tung_threshold=self.cfg.phuc_tung_threshold
                )

                if match.found:
                    cx, cy = target_row.center
                    item_label = "Kim Cương" if target_type == "DIAMOND" else "Phục Tùng C (Obedient C)"
                    logger.info(f"💎 [VIP9] Phát hiện {item_label} ở DÒNG #{idx + 1} (conf: {match.confidence:.3f}). Bấm tại ({cx}, {cy})")
                    self._tap(cx, cy, label=f"Click Center Row #{idx + 1}")
                    self.play_diamond_row(max_rounds, vip_name="VIP9")
                else:
                    logger.info(f"[VIP9] Dòng #{idx + 1} không có Kim Cương / Phục Tùng (conf: {match.confidence:.3f}). Bỏ qua.")

            # 2. Kiểm tra tiếp Dòng 4 của VIP9 (đang ở sẵn VIP9, chỉ cần vuốt cuộn lên)
            self._check_stop()
            logger.info("[VIP9] Cuộn khay item lên để kiểm tra Dòng 4...")
            self.dismiss_popup_if_present()
            self._swipe_vip9_up()

            scrolled_rows = self.cfg.vip9_scrolled_rows
            self._check_stop()
            frame = self._wait_for_frame()

            # Tự động lưu ảnh Dòng 4 vào thư mục line_4 để người dùng kiểm tra trực quan
            try:
                line4_dir = Path("line_4")
                line4_dir.mkdir(parents=True, exist_ok=True)
                if scrolled_rows:
                    r4 = scrolled_rows[0]
                    cropped_r4 = frame[r4.y : r4.y2, r4.x : r4.x2]
                    cv2.imwrite(str(line4_dir / "vip9_dong_4.png"), cropped_r4)
            except Exception as e:
                logger.debug(f"Lỗi lưu ảnh debug line_4: {e}")

            if scrolled_rows:
                self._check_stop()
                r4 = scrolled_rows[0]
                match_r4, target_type_r4 = self.vision.check_row_for_targets(
                    frame=frame,
                    row_roi=r4,
                    min_threshold=self.cfg.diamond_threshold,
                    enable_phuc_tung=self.cfg.enable_phuc_tung,
                    phuc_tung_threshold=self.cfg.phuc_tung_threshold
                )

                if match_r4.found:
                    cx, cy = r4.center
                    item_label = "Kim Cương" if target_type_r4 == "DIAMOND" else "Phục Tùng C (Obedient C)"
                    logger.info(f"💎 [VIP9] Phát hiện {item_label} ở DÒNG 4 (conf: {match_r4.confidence:.3f}). Bấm tại ({cx}, {cy})")
                    self._tap(cx, cy, label="Click Row 4")
                    self.play_diamond_row(max_rounds, vip_name="VIP9")
                else:
                    logger.info(f"[VIP9] Không có Kim Cương / Phục Tùng ở Dòng 4 (conf: {match_r4.confidence:.3f}).")

            # Kết thúc Dòng 4 -> Luôn cuộn trả khay item về lại đầu trang với cùng lực kéo đối xứng
            self.dismiss_popup_if_present()
            self._swipe_vip9_down()

    def reset_cycle(self) -> bool:
        """
        Bấm Refresh/Reset để làm mới vòng lặp.
        - Bấm trực tiếp toạ độ cố định tại nút Refresh tức thì qua Persistent Shell (<5ms).
        - Dọn dẹp popup nếu có thông báo đột xuất (ví dụ Warrior Gem) rồi tiếp tục ngay!
        """
        self._check_stop()
        logger.info("=== [STATE] Bấm Reset (Refresh) ===")
        self.dismiss_popup_if_present()
        self._check_stop()

        cx, cy = self.cfg.reset_btn_pos
        logger.info(f"🔄 Bấm nút Reset tại ({cx}, {cy})")
        self._tap(cx, cy, label="Reset Cycle")

        # Dọn dẹp nếu có popup đột xuất
        time.sleep(self.cfg.wait_after_reset)
        self.dismiss_popup_if_present()
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
            # 0. Tự động đóng popup nếu có từ trước
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
            logger.info(f"✅ Hoàn thành vòng #{self.cycle_count} trong {total_time_sec:.2f}s! (Vòng kế tiếp sẽ bắt đầu từ: {self.current_vip.upper()})")
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
