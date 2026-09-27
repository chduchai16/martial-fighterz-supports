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

    def start(self):
        """Khởi động hệ thống capture và nạp template."""
        logger.info("Đang khởi động GameBot...")
        self.capture.start()
        logger.info("GameBot đã sẵn sàng hoạt động.")

    def stop(self):
        """Dừng GameBot an toàn."""
        logger.info("Đang dừng GameBot...")
        self.capture.stop()
        logger.info("GameBot đã dừng.")

    def _wait_for_frame(self, timeout: float = 3.5) -> np.ndarray:
        """Lấy frame mới nhất và tự động đồng bộ độ phân giải."""
        frame = self.capture.get_latest_frame(timeout=timeout)
        if frame is None:
            raise TimeoutError("Không nhận được frame từ thiết bị!")
        
        f_h, f_w = frame.shape[:2]
        if self.cfg.target_width != f_w or self.cfg.target_height != f_h:
            logger.info(f"Đồng bộ độ phân giải giả lập: {f_w}x{f_h}")
            self.cfg.target_width = f_w
            self.cfg.target_height = f_h

        return frame

    def _tap(self, x: int, y: int, label: str = "Tap"):
        """Gửi lệnh tap vào toạ độ (x, y)."""
        logger.info(f"[{label}] -> Tap tại điểm ({x}, {y})")
        self.capture.tap(x, y, jitter_px=self.cfg.tap_jitter_px)
        time.sleep(self.cfg.wait_after_tap)

    def _swipe_vip9_up(self):
        """Vuốt cuộn khay item VIP9 lên để lộ Dòng 4."""
        w, h = self.cfg.target_width, self.cfg.target_height
        x1 = int(self.cfg.swipe_vip9_start_ratio[0] * w)
        y1 = int(self.cfg.swipe_vip9_start_ratio[1] * h)
        x2 = int(self.cfg.swipe_vip9_end_ratio[0] * w)
        y2 = int(self.cfg.swipe_vip9_end_ratio[1] * h)
        logger.info(f"[VIP9] Đang cuộn khay item lên: từ ({x1}, {y1}) -> ({x2}, {y2})...")
        self.capture.swipe(x1, y1, x2, y2, duration=0.35)
        time.sleep(self.cfg.wait_after_scroll)

    def _swipe_vip9_down(self):
        """Vuốt cuộn khay item VIP9 xuống để trở về vị trí đầu, hiện full Dòng 1."""
        w, h = self.cfg.target_width, self.cfg.target_height
        # Vuốt ngược lại từ trên xuống dưới
        x1 = int(self.cfg.swipe_vip9_end_ratio[0] * w)
        y1 = int(self.cfg.swipe_vip9_end_ratio[1] * h)
        x2 = int(self.cfg.swipe_vip9_start_ratio[0] * w)
        y2 = int(self.cfg.swipe_vip9_start_ratio[1] * h)
        logger.info(f"[VIP9] Đang cuộn khay item xuống lại đầu trang: từ ({x1}, {y1}) -> ({x2}, {y2})...")
        self.capture.swipe(x1, y1, x2, y2, duration=0.35)
        time.sleep(self.cfg.wait_after_scroll)

    def classify_ok_popup(self, frame: np.ndarray) -> str:
        """
        Phân biệt chính xác nội dung chữ trong popup cuộn thư Arale:
        - 'WARRIOR_GEM': Chứa chữ "Warrior Gem" (Bấm OK và tiếp tục lượt chơi).
        - 'EXHAUSTED': Chứa chữ "Không còn lượt đổi nào" hoặc "Không đủ vật phẩm trong kho đồ" (Bấm OK và chuyển dòng).
        """
        # 1. Kiểm tra chữ Warrior Gem
        match_wg = self.vision.find_template(frame, "warrior_gem_text", threshold=0.55)
        if match_wg.found:
            return "WARRIOR_GEM"

        # 2. Kiểm tra chữ Hết lượt đổi
        match_no_turns = self.vision.find_template(frame, "no_turns_text", threshold=0.55)
        if match_no_turns.found:
            return "EXHAUSTED"

        # 3. Kiểm tra chữ Hết vật phẩm kho đồ
        match_out = self.vision.find_template(frame, "out_of_items_text", threshold=0.55)
        if match_out.found:
            return "EXHAUSTED"

        return "EXHAUSTED"

    def _confirm_button_closed(self, template_key: str, threshold: float, roi: Rect, tap_pos: Tuple[int, int], max_wait: float = 4.0) -> bool:
        """
        ĐẢM BẢO BẤM THÀNH CÔNG:
        Theo dõi màn hình liên tục cho tới khi nút/popup biến mất hoàn toàn.
        Nếu sau 0.35s nút vẫn còn hiển thị, bấm lại tại toạ độ tap_pos cho tới khi màn hình cập nhật đóng hẳn!
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
                
                # Nếu quá 0.35s mà nút vẫn còn trên màn hình -> tap lại
                if time.perf_counter() - last_retry > 0.35:
                    logger.info(f"🔄 Nút/Popup '{template_key}' vẫn còn (conf: {re_match.confidence:.2f}) -> Bấm lại tại ({tap_pos[0]}, {tap_pos[1]})...")
                    self._tap(tap_pos[0], tap_pos[1], label=f"Retry {template_key}")
                    last_retry = time.perf_counter()
            except Exception:
                pass
            time.sleep(0.06)
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
            try:
                frame = self._wait_for_frame()
                match = self.vision.find_template(frame, template_key, threshold=thresh, roi=roi)
                if match.found:
                    elapsed = time.perf_counter() - t_start
                    logger.info(f"👁️ [{lbl}] Màn hình đã xuất hiện '{template_key}' sau {elapsed:.2f}s (conf: {match.confidence:.2f}) tại {match.center}")
                    return match
            except Exception:
                pass
            time.sleep(0.06)
        return None

    def wait_and_dismiss_all_popups(self, max_wait_sec: float = 3.5) -> bool:
        """
        Theo dõi màn hình và bấm đóng tất cả các popup (OK / Rút lui / Warrior Gem) cho tới khi màn hình hoàn toàn sạch.
        Đảm bảo phải bấm thành công và popup biến mất mới kết thúc!
        """
        t_start = time.perf_counter()
        dismissed_any = False

        while time.perf_counter() - t_start < max_wait_sec:
            try:
                frame = self._wait_for_frame()
            except Exception:
                time.sleep(0.06)
                continue

            # 1. Kiểm tra nút Rút lui
            match_rut_lui = self.vision.find_template(
                frame, "rut_lui_btn", threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi
            )
            if match_rut_lui.found:
                cx, cy = match_rut_lui.center
                logger.info(f"🔔 [Popup Rút lui] Đang xuất hiện tại ({cx}, {cy}) -> Bấm Rút lui!")
                self._tap(cx, cy, label="Click Rut Lui")
                self._confirm_button_closed("rut_lui_btn", self.cfg.rut_lui_threshold, self.cfg.rut_lui_roi, (cx, cy))
                dismissed_any = True
                t_start = time.perf_counter()
                continue

            # 2. Kiểm tra nút OK
            match_ok = self.vision.find_template(
                frame, "ok_btn", threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
            )
            if match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                popup_label = "Warrior Gem" if p_type == "WARRIOR_GEM" else "Hết lượt / Vật phẩm"
                logger.info(f"🔔 [Popup {popup_label}] Đang xuất hiện tại ({cx}, {cy}) -> Bấm OK!")
                self._tap(cx, cy, label=f"Click OK ({popup_label})")
                self._confirm_button_closed("ok_btn", self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                dismissed_any = True
                t_start = time.perf_counter()
                continue

            # Nếu sau 0.8s quét liên tục mà không thấy popup nào xuất hiện nữa -> màn hình đã sạch
            if time.perf_counter() - t_start > 0.8:
                break
            time.sleep(0.06)

        return dismissed_any

    def dismiss_popup_if_present(self, max_attempts: int = 3) -> bool:
        """Kiểm tra và tự động bấm nút OK / Rút lui nếu có bất kỳ popup nào đang kẹt."""
        return self.wait_and_dismiss_all_popups(max_wait_sec=1.5)

    def _tap_template_or_fallback(
        self,
        template_key: str,
        fallback_pos: Tuple[int, int],
        threshold: float = 0.75,
        roi: Optional[Rect] = None,
        label: str = "Action"
    ) -> bool:
        """Tìm template để tap, nếu không thấy thì dùng toạ độ fallback."""
        frame = self._wait_for_frame()
        match = self.vision.find_template(
            frame=frame,
            template_key_or_path=template_key,
            threshold=threshold,
            roi=roi
        )

        if match.found:
            cx, cy = match.center
            logger.info(f"[{label}] Tìm thấy '{template_key}' (conf: {match.confidence:.2f}) tại ({cx}, {cy})")
            self._tap(cx, cy, label=label)
            return True
        else:
            fx, fy = fallback_pos
            logger.info(f"[{label}] Dùng toạ độ fallback ({fx}, {fy})")
            self._tap(fx, fy, label=label)
            return True

    # ==================== CÁC STATE CHI TIẾT ====================

    def enter_vip_section(self, vip_type: str = "vip7", timeout: float = 6.0) -> bool:
        """Chuyển vào Tab 3 (VIP7) hoặc Tab 4 (VIP9) sau khi xác nhận màn hình đã sẵn sàng."""
        logger.info(f"=== [STATE] Vào Tab {vip_type.upper()} ===")
        self.dismiss_popup_if_present()
        template_key = f"{vip_type}_tab"
        fallback_pos = self.cfg.vip7_tab_pos if vip_type == "vip7" else self.cfg.vip9_tab_pos

        match = self.wait_for_template(
            template_key=template_key,
            threshold=self.cfg.button_threshold,
            timeout=timeout,
            label=f"Tab {vip_type.upper()}"
        )
        if match:
            cx, cy = match.center
            self._tap(cx, cy, label=f"Click Tab {vip_type.upper()}")
        else:
            fx, fy = fallback_pos
            logger.warning(f"⚠️ Không nhận diện được '{template_key}' trên màn hình -> Sử dụng toạ độ chuẩn ({fx}, {fy})")
            self._tap(fx, fy, label=f"Click Tab {vip_type.upper()} (Fixed Pos)")

        time.sleep(0.3)
        return True

    def choose_even_odd(self, timeout: float = 8.0) -> bool:
        """
        Chờ màn hình xuất hiện nút CHẴN (EVEN) rồi mới bấm.
        Không bấm mò trước khi màn hình kịp render.
        """
        logger.info("[EVEN] Chờ nút CHẴN (EVEN) xuất hiện trên màn hình...")
        match = self.wait_for_template(
            template_key="even_btn",
            threshold=self.cfg.button_threshold,
            timeout=timeout,
            label="Nút CHẴN (EVEN)"
        )
        if match:
            cx, cy = match.center
            self._tap(cx, cy, label="Select EVEN")
            return True
        else:
            fx, fy = self.cfg.even_btn_pos
            logger.warning(f"[EVEN] Hết thời gian chờ {timeout}s không thấy nút EVEN -> Bấm toạ độ dự phòng ({fx}, {fy})")
            self._tap(fx, fy, label="Select EVEN (Fallback)")
            return False

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
            try:
                frame = self._wait_for_frame()
            except Exception:
                time.sleep(0.06)
                continue

            elapsed = time.perf_counter() - t_start

            # 1. Kiểm tra nếu xuất hiện nút [Rút lui] trong ROI popup
            match_rut_lui = self.vision.find_template(
                frame, "rut_lui_btn", threshold=self.cfg.rut_lui_threshold, roi=self.cfg.rut_lui_roi
            )
            if match_rut_lui.found:
                cx, cy = match_rut_lui.center
                logger.info(f"🎉 [Nhận quà] Màn hình đã xuất hiện nút 'Rút lui' sau {elapsed:.2f}s (conf: {match_rut_lui.confidence:.2f}) -> Bấm tại ({cx}, {cy})")
                self._tap(cx, cy, label="Click Rut Lui")
                # Xác nhận nút Rút lui đã đóng hoàn toàn
                self._confirm_button_closed("rut_lui_btn", self.cfg.rut_lui_threshold, self.cfg.rut_lui_roi, (cx, cy))
                return "SUCCESS"

            # 2. Kiểm tra nếu xuất hiện popup [OK] trong ROI popup
            match_ok = self.vision.find_template(
                frame, "ok_btn", threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
            )
            if match_ok.found:
                cx, cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                if p_type == "WARRIOR_GEM":
                    logger.info(f"✨ [Warrior Gem] Màn hình xuất hiện popup Warrior Gem sau {elapsed:.2f}s! Bấm OK tại ({cx}, {cy}) và tiếp tục chơi.")
                    self._tap(cx, cy, label="Click OK (Warrior Gem)")
                    self._confirm_button_closed("ok_btn", self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                    return "WARRIOR_GEM"
                else:
                    logger.warning(f"⚠️ [Hết lượt / Hết vật phẩm] Màn hình xuất hiện popup hết lượt sau {elapsed:.2f}s! Bấm OK tại ({cx}, {cy}) để chuyển dòng.")
                    self._tap(cx, cy, label="Click OK (Het luot doi)")
                    self._confirm_button_closed("ok_btn", self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                    return "OUT_OF_ITEMS"

            time.sleep(0.06)

        # Kiểm tra dọn dẹp popup còn sót trước khi kết thúc
        if self.wait_and_dismiss_all_popups(max_wait_sec=1.5):
            logger.info("✅ Đã xử lý đóng popup còn sót trên màn hình.")
            return "SUCCESS"

        logger.info(f"ℹ️ Không có nút Rút lui hay Popup nào xuất hiện sau {wait_limit:.1f}s -> Dòng này đã hết lượt chơi.")
        return "NO_POPUP"

    def play_diamond_row(self, max_rounds: int, vip_name: str = "VIP") -> bool:
        """
        Chơi các lượt nhận quà cho 1 dòng Kim Cương.
        Theo dõi màn hình thực tế:
        - Màn hình mở bàn cờ (nút EVEN xuất hiện) -> chơi lượt.
        - Màn hình hiện popup lỗi/hết lượt -> bấm OK và dừng dòng.
        - Màn hình hiện popup Warrior Gem -> bấm OK và tiếp tục.
        """
        logger.info(f"--- [CHƠI DÒNG KIM CƯƠNG ({vip_name})] Chuỗi tối đa {max_rounds} lượt nhận quà ---")
        
        # 1. Chờ màn hình chuyển cảnh: hoặc mở bàn cờ (nút EVEN), hoặc xuất hiện popup OK
        t_open_start = time.perf_counter()
        while time.perf_counter() - t_open_start < 6.0:
            try:
                frame = self._wait_for_frame()
            except Exception:
                time.sleep(0.06)
                continue

            # Kiểm tra nếu xuất hiện popup OK (Hết lượt / Warrior Gem)
            match_init_ok = self.vision.find_template(
                frame, "ok_btn", threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
            )
            if match_init_ok.found:
                cx, cy = match_init_ok.center
                p_type = self.classify_ok_popup(frame)
                if p_type == "WARRIOR_GEM":
                    logger.info(f"✨ [{vip_name}] Màn hình xuất hiện Warrior Gem khi mở dòng! Bấm OK tại ({cx}, {cy}).")
                    self._tap(cx, cy, label="Click OK (Warrior Gem)")
                    self._confirm_button_closed("ok_btn", self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                    time.sleep(0.2)
                    continue
                else:
                    logger.warning(f"⚠️ [{vip_name}] Dòng này đã hết lượt đổi / hết vật phẩm! Bấm OK tại ({cx}, {cy}) và chuyển dòng ngay.")
                    self._tap(cx, cy, label="Click OK (Het luot doi)")
                    self._confirm_button_closed("ok_btn", self.cfg.ok_threshold, self.cfg.ok_roi, (cx, cy))
                    return False

            # Kiểm tra nếu nút EVEN đã xuất hiện (bàn cờ xúc xắc đã mở sẵn sàng trên màn hình)
            match_even = self.vision.find_template(frame, "even_btn", threshold=self.cfg.button_threshold)
            if match_even.found:
                logger.info(f"🎲 [{vip_name}] Màn hình bàn cờ xúc xắc đã xuất hiện sẵn sàng.")
                break

            time.sleep(0.06)

        round_idx = 1
        while round_idx <= max_rounds:
            logger.info(f"👉 [{vip_name}] Lượt chơi #{round_idx}/{max_rounds}...")
            # Chờ và bấm nút EVEN khi nó xuất hiện trên màn hình
            self.choose_even_odd(timeout=6.0)

            # Chờ theo dõi kết quả xúc xắc & nút Rút lui / Popup xuất hiện trên màn hình
            status = self.wait_and_handle_reward_popup(max_wait_sec=self.cfg.api_loading_timeout)

            if status == "OUT_OF_ITEMS":
                logger.warning(f"[{vip_name}] Dòng này đã hết lượt đổi/vật phẩm ở lượt #{round_idx}. Chuyển sang dòng khác!")
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
        max_rounds = self.cfg.vip7_rounds_per_row if vip_type == "vip7" else self.cfg.vip9_rounds_per_row
        processed_rows: Set[int] = set()

        if vip_type == "vip7":
            # 1. Chuyển vào Tab VIP7 1 lần duy nhất
            self.enter_vip_section("vip7")
            rows = self.cfg.vip7_rows

            while True:
                available_rows = [r for i, r in enumerate(rows) if i not in processed_rows]
                if not available_rows:
                    logger.info("[VIP7] Đã kiểm tra hết tất cả các dòng của VIP7.")
                    break

                self.dismiss_popup_if_present()
                frame = self._wait_for_frame()
                best_idx, best_match, _ = self.vision.find_best_matching_row(
                    frame=frame,
                    template_key_or_path="kim_cuong",
                    rows=available_rows,
                    min_threshold=self.cfg.diamond_threshold
                )

                if best_idx is not None and best_match is not None:
                    actual_idx = [i for i in range(len(rows)) if i not in processed_rows][best_idx]
                    processed_rows.add(actual_idx)

                    target_row = rows[actual_idx]
                    cx, cy = target_row.center
                    logger.info(f"💎 [VIP7] Phát hiện Kim Cương ở DÒNG #{actual_idx + 1} (conf: {best_match.confidence:.3f} >= {self.cfg.diamond_threshold:.2f}). Click tại ({cx}, {cy})")
                    self._tap(cx, cy, label=f"Click Center Row #{actual_idx+1}")
                    time.sleep(0.4)

                    self.play_diamond_row(max_rounds, vip_name="VIP7")
                else:
                    logger.info(f"[VIP7] Không còn dòng Kim Cương nào chưa chơi (ngưỡng >= {self.cfg.diamond_threshold:.2f}). Chuyển sang VIP9.")
                    break

        else:
            # 1. Chuyển vào Tab VIP9 1 lần duy nhất từ VIP7
            self.enter_vip_section("vip9")
            initial_rows = self.cfg.vip9_initial_rows

            # Quét tất cả các dòng ban đầu (1, 2, 3)
            while True:
                available_rows = [r for i, r in enumerate(initial_rows) if i not in processed_rows]
                if not available_rows:
                    break

                self.dismiss_popup_if_present()
                frame = self._wait_for_frame()
                best_idx, best_match, _ = self.vision.find_best_matching_row(
                    frame=frame,
                    template_key_or_path="kim_cuong",
                    rows=available_rows,
                    min_threshold=self.cfg.diamond_threshold
                )

                if best_idx is not None and best_match is not None:
                    actual_idx = [i for i in range(len(initial_rows)) if i not in processed_rows][best_idx]
                    processed_rows.add(actual_idx)

                    target_row = initial_rows[actual_idx]
                    cx, cy = target_row.center
                    logger.info(f"💎 [VIP9] Phát hiện Kim Cương ở DÒNG #{actual_idx + 1} (conf: {best_match.confidence:.3f} >= {self.cfg.diamond_threshold:.2f}). Click tại ({cx}, {cy})")
                    self._tap(cx, cy, label=f"Click Center Row #{actual_idx+1}")
                    time.sleep(0.4)

                    self.play_diamond_row(max_rounds, vip_name="VIP9")
                else:
                    logger.info(f"[VIP9] Không còn dòng Kim Cương nào ở các dòng đầu (ngưỡng >= {self.cfg.diamond_threshold:.2f}).")
                    break

            # 2. Kiểm tra tiếp Dòng 4 của VIP9 (đang ở sẵn VIP9, chỉ cần vuốt cuộn lên)
            logger.info("[VIP9] Cuộn khay item lên để kiểm tra Dòng 4...")
            self.dismiss_popup_if_present()
            self._swipe_vip9_up()

            scrolled_rows = self.cfg.vip9_scrolled_rows
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

            best_idx, best_match, _ = self.vision.find_best_matching_row(
                frame=frame,
                template_key_or_path="kim_cuong",
                rows=scrolled_rows,
                min_threshold=self.cfg.diamond_threshold
            )

            if best_idx is not None and best_match is not None:
                target_row = scrolled_rows[best_idx]
                cx, cy = target_row.center
                logger.info(f"💎 [VIP9] Phát hiện Kim Cương ở DÒNG 4 (conf: {best_match.confidence:.3f} >= {self.cfg.diamond_threshold:.2f}). Click tại ({cx}, {cy})")
                self._tap(cx, cy, label="Click Row 4")
                time.sleep(0.4)
                self.play_diamond_row(max_rounds, vip_name="VIP9")
            else:
                logger.info("[VIP9] Không có Kim Cương ở Dòng 4.")

            # Kết thúc Dòng 4 -> Luôn cuộn trả khay item về lại đầu trang với cùng lực kéo đối xứng
            self.dismiss_popup_if_present()
            self._swipe_vip9_down()

    def reset_cycle(self) -> bool:
        """
        Bấm Refresh/Reset để làm mới vòng lặp.
        Chờ liên tục cho đến khi nút Reset xuất hiện -> bấm Reset.
        Sau đó chờ liên tục cho đến khi popup xác nhận (nút OK / Warrior Gem) xuất hiện -> bấm OK và đóng sạch.
        Không giới hạn số lần hay đếm giây cố định, ra nút lúc nào bấm lúc đó.
        """
        logger.info("=== [STATE] Bấm Reset (Refresh) ===")
        self.dismiss_popup_if_present()

        # 1. Chờ liên tục cho đến khi nút Reset xuất hiện trên màn hình
        logger.info("⏳ Chờ nút Reset xuất hiện trên màn hình...")
        reset_match = None
        while reset_match is None:
            reset_match = self.wait_for_template(
                template_key="reset_btn",
                threshold=self.cfg.button_threshold,
                timeout=2.0,
                label="Nút Reset (Refresh)"
            )
            if reset_match is None:
                # Nếu có popup nào đang che khuất nút Reset thì dọn dẹp
                self.dismiss_popup_if_present()

        cx, cy = reset_match.center
        logger.info(f"🔄 Bấm nút Reset tại ({cx}, {cy})")
        self._tap(cx, cy, label="Reset Cycle")

        # 2. Chờ liên tục cho đến khi nút OK xác nhận xuất hiện trên màn hình
        logger.info("⏳ Đang theo dõi màn hình chờ nút OK xác nhận Reset xuất hiện...")
        t_wait_start = time.perf_counter()
        while True:
            try:
                frame = self._wait_for_frame()
            except Exception:
                time.sleep(0.06)
                continue

            # Kiểm tra nếu xuất hiện nút OK
            match_ok = self.vision.find_template(
                frame, "ok_btn", threshold=self.cfg.ok_threshold, roi=self.cfg.ok_roi
            )
            if match_ok.found:
                ok_cx, ok_cy = match_ok.center
                p_type = self.classify_ok_popup(frame)
                popup_label = "Warrior Gem" if p_type == "WARRIOR_GEM" else "Xác nhận Reset"
                logger.info(f"🔔 [Popup {popup_label}] Đã xuất hiện nút OK tại ({ok_cx}, {ok_cy}) -> Bấm OK!")
                self._tap(ok_cx, ok_cy, label=f"Click OK ({popup_label})")
                self._confirm_button_closed("ok_btn", self.cfg.ok_threshold, self.cfg.ok_roi, (ok_cx, ok_cy))
                break

            # Nếu game đã làm mới xong trực tiếp và hiển thị lại Tab VIP
            if time.perf_counter() - t_wait_start > 3.0:
                match_vip7 = self.vision.find_template(frame, "vip7_tab", threshold=self.cfg.button_threshold)
                if match_vip7.found:
                    logger.info("✅ Giao diện đã tự động làm mới về màn hình VIP.")
                    break

            time.sleep(0.06)

        # 3. Đảm bảo dọn sạch mọi popup còn sót
        self.dismiss_popup_if_present()
        logger.info("✅ Hoàn tất quá trình Reset.")
        return True

    # ==================== ĐIỀU PHỐI VÒNG LẶP ====================

    def run_one_cycle(self) -> bool:
        """Chạy 1 chu kỳ hoàn chỉnh."""
        self.cycle_count += 1
        cycle_start = time.perf_counter()
        logger.info(f"\n==================== BẮT ĐẦU VÒNG #{self.cycle_count} ====================")

        # 0. Tự động đóng popup nếu có từ trước
        self.dismiss_popup_if_present()

        # 1. VIP7 Flow (Tự quét và chơi tất cả dòng Kim Cương, nếu hết nguyên liệu tự sang dòng khác)
        self.process_vip_section("vip7")

        # 2. VIP9 Flow (Tự quét, cuộn và chơi tất cả dòng Kim Cương)
        self.process_vip_section("vip9")

        # 3. Reset Flow
        self.reset_cycle()

        total_time_sec = time.perf_counter() - cycle_start
        self.success_count += 1
        logger.info(f"✅ Hoàn thành vòng #{self.cycle_count} trong {total_time_sec:.2f}s!")
        return True

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
