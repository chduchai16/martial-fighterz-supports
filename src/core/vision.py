"""
Module Vision: Xử lý template matching và so khớp hình ảnh với tính năng Auto-Scale đa độ phân giải.
Tự động scale template theo kích thước màn hình thực tế của giả lập (so với ảnh gốc 567x1006).
"""
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import cv2
import numpy as np

try:
    from src.core.config import DEBUG_DIR, Rect
except ImportError:
    from .config import DEBUG_DIR, Rect

logger = logging.getLogger("GameBot.Vision")

# Kích thước ảnh chuẩn lúc crop template
REF_WIDTH = 567.0
REF_HEIGHT = 1006.0


@dataclass
class MatchResult:
    """Kết quả so khớp template."""
    found: bool
    confidence: float
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


class VisionEngine:
    def __init__(self, templates_dict: Optional[Dict[str, Union[str, Path]]] = None):
        self._raw_templates: Dict[str, np.ndarray] = {}
        self._scaled_cache: Dict[str, Dict[float, np.ndarray]] = {}
        if templates_dict:
            for key, path in templates_dict.items():
                self.load_template(key, path)

    def load_template(self, key: str, path: Union[str, Path]) -> bool:
        """Tải template gốc từ file vào cache."""
        p = Path(path)
        if not p.exists():
            logger.debug(f"File template '{key}' chưa có (sẽ dùng toạ độ fallback): {p}")
            return False

        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            return False

        self._raw_templates[key] = img
        self._scaled_cache[key] = {}
        logger.debug(f"Đã nạp template '{key}': kích thước gốc {img.shape[1]}x{img.shape[0]}")
        return True

    def get_scaled_template(self, key: str, scale: float) -> Optional[np.ndarray]:
        """Lấy template đã được scale theo tỷ lệ màn hình thực tế."""
        if key not in self._raw_templates:
            return None

        # Làm tròn scale 2 chữ số thập phân để cache
        scale_key = round(scale, 2)
        if scale_key == 1.0:
            return self._raw_templates[key]

        if scale_key not in self._scaled_cache[key]:
            orig = self._raw_templates[key]
            orig_h, orig_w = orig.shape[:2]
            new_w = max(4, int(orig_w * scale))
            new_h = max(4, int(orig_h * scale))
            resized = cv2.resize(orig, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
            self._scaled_cache[key][scale_key] = resized

        return self._scaled_cache[key][scale_key]

    def find_template(
        self,
        frame: np.ndarray,
        template_key_or_path: Union[str, Path],
        threshold: float = 0.75,
        roi: Optional[Rect] = None,
        method: int = cv2.TM_CCOEFF_NORMED
    ) -> MatchResult:
        """
        Tìm kiếm template trong frame hoặc trong vùng ROI.
        Tự động tính scale factor dựa trên độ phân giải thực tế của frame.
        """
        key = str(template_key_or_path)
        if key not in self._raw_templates:
            # Thử nạp nếu là đường dẫn
            if not self.load_template(key, template_key_or_path):
                return MatchResult(found=False, confidence=0.0)

        f_h, f_w = frame.shape[:2]
        scale = f_w / REF_WIDTH

        # Thử nghiệm các mức scale lân cận để đạt độ khớp cao nhất
        scales_to_try = [scale, scale * 0.95, scale * 1.05]
        best_res = MatchResult(found=False, confidence=-1.0)

        offset_x, offset_y = 0, 0
        search_area = frame
        if roi is not None:
            offset_x, offset_y = roi.x, roi.y
            y1 = max(0, min(roi.y, f_h))
            y2 = max(0, min(roi.y + roi.h, f_h))
            x1 = max(0, min(roi.x, f_w))
            x2 = max(0, min(roi.x + roi.w, f_w))
            search_area = frame[y1:y2, x1:x2]

        sa_h, sa_w = search_area.shape[:2]

        for s in scales_to_try:
            tpl = self.get_scaled_template(key, s)
            if tpl is None:
                continue
            t_h, t_w = tpl.shape[:2]
            if sa_h < t_h or sa_w < t_w:
                continue

            res = cv2.matchTemplate(search_area, tpl, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            score = float(max_val) if method in (cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED) else float(1.0 - min_val)

            if score > best_res.confidence:
                match_x, match_y = max_loc if method in (cv2.TM_CCOEFF_NORMED, cv2.TM_CCORR_NORMED) else min_loc
                best_res = MatchResult(
                    found=(score >= threshold),
                    confidence=score,
                    x=match_x + offset_x,
                    y=match_y + offset_y,
                    w=t_w,
                    h=t_h
                )

        if best_res.confidence < 0:
            best_res.confidence = 0.0

        return best_res

    def check_row_for_diamond(
        self,
        frame: np.ndarray,
        row_roi: Rect,
        min_threshold: float = 0.80
    ) -> MatchResult:
        """
        Kiểm tra một dòng cụ thể xem có chứa Kim Cương hay không.
        Sử dụng DUY NHẤT một mẫu chuẩn 'kim_cuong' (kim_cuong_icon.png) theo yêu cầu.
        """
        match = self.find_template(
            frame=frame,
            template_key_or_path="kim_cuong",
            threshold=min_threshold,
            roi=row_roi
        )
        return match

    def is_input_zero(self, frame: np.ndarray, row_roi: Rect) -> bool:
        """
        Kiểm tra số lượng nguyên liệu đầu vào ở ô avatar bên trái có phải là số 0 không.
        row_roi: Ô phần thưởng bên phải của dòng.

        Quy tắc cấu trúc chữ số game:
        1. Quét dải chân avatar: Y [cy_reward - 100 .. cy_reward + 120], X [120 .. 220].
        2. Chữ số 0 khớp template input_zero với ngưỡng >= 0.82.
        3. Phân biệt số 0 đơn lẻ (= 0) với các số 10, 20, 30, 40...:
           - Số 10, 20, 30...: Chữ số 0 nằm ở hàng đơn vị (bên phải), BÊN TRÁI NÓ có chữ số hàng chục (1, 2, 3...) màu vàng!
           - Số 0 đơn lẻ: BÊN TRÁI NÓ là cành ngôi sao xanh / nền rác, pixel màu vàng rất ít (< 120px).
           -> Nếu bên trái số 0 có pixel chữ số màu vàng (>= 120px) -> Là số 10, 20, 30... -> Trả về False!
        """
    def _extract_digit_boxes(self, frame: np.ndarray, row_roi: Rect) -> Tuple[np.ndarray, List[Tuple[int, int, int, int]]]:
        """
        Trích xuất cụm box chữ số số lượng chân avatar:
        1. Vùng cắt Y [cy - 100 .. cy + 70], X [120 .. 192] bao trọn cả trạng thái ban đầu và cuộn lỡ.
        2. Lọc dải màu vàng cam [12..30, 160..255, 160..255] loại trừ tóc Salza và kính Scouter (H > 35).
        3. Tiêu chuẩn viền đen đậm (black_cnt >= 40) loại bỏ hoàn toàn các mảng sáng nền avatar.
        4. Gom cụm các chữ số liền kề nhau (cùng baseline Y <= 6px VÀ khoảng cách X <= 16px).
        """
        h, w = frame.shape[:2]
        scale = w / 1080.0
        cy_reward = row_roi.y + row_roi.h // 2

        y1 = max(0, int((cy_reward - 100) * scale))
        y2 = min(h, int((cy_reward + 70) * scale))
        x1 = int(120 * scale)
        x2 = int(192 * scale)

        strip = frame[y1:y2, x1:x2]
        if strip.size == 0:
            return strip, []

        hsv = cv2.cvtColor(strip, cv2.COLOR_BGR2HSV)
        lower_yellow = np.array([12, 160, 160], dtype=np.uint8)
        upper_yellow = np.array([30, 255, 255], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower_yellow, upper_yellow)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        clean_boxes = []
        for c in contours:
            if cv2.contourArea(c) > 20:
                bx, by, bw, bh = cv2.boundingRect(c)
                if (14 * scale <= bh <= 34 * scale) and (4 * scale <= bw <= 30 * scale):
                    patch = strip[max(0, by - 2):min(strip.shape[0], by + bh + 2), max(0, bx - 2):min(strip.shape[1], bx + bw + 2)]
                    black_cnt = np.count_nonzero((patch[:, :, 0] < 50) & (patch[:, :, 1] < 50) & (patch[:, :, 2] < 50))
                    # Chữ số game có viền đen đậm (black_cnt >= 35), hoặc khối số mock test có diện tích >= 250px
                    if black_cnt >= 35 or cv2.contourArea(c) >= 250:
                        clean_boxes.append((bx, by, bw, bh))

        clean_boxes.sort(key=lambda b: b[0])
        clusters = []
        for b in clean_boxes:
            added = False
            cy_b = b[1] + b[3] / 2.0
            for cl in clusters:
                last = cl[-1]
                cy_last = last[1] + last[3] / 2.0
                dist_x = b[0] - (last[0] + last[2])
                # Các chữ số cùng hàng phải đồng trục tâm Y (<= 3.5px) và khoảng cách X từ 1px đến 14px (không đè chồng nhau)
                if abs(cy_b - cy_last) <= int(3.5 * scale) and (int(1 * scale) <= dist_x <= int(14 * scale)):
                    cl.append(b)
                    added = True
                    break
            if not added:
                clusters.append([b])

        # Lọc bỏ các cụm đơn lẻ ở rìa trái (bx < 35) vì số 1 chữ số trong game luôn canh lề phải ở bx >= 35
        valid_clusters = []
        for cl in clusters:
            if len(cl) >= 2 or cl[0][0] >= int(35 * scale):
                valid_clusters.append(cl)

        if not valid_clusters:
            return strip, []

        # Chọn cụm số: ưu tiên cụm có nhiều chữ số (số 2 chữ số trở lên), nếu cùng số chữ số thì chọn cụm nằm ở đáy chân avatar (bottom Y lớn nhất)
        best_cl = max(valid_clusters, key=lambda cl: (len(cl), max(b[1] + b[3] for b in cl)))
        best_cl.sort(key=lambda b: b[0])
        return strip, best_cl

    def is_input_zero(self, frame: np.ndarray, row_roi: Rect) -> bool:
        """
        Kiểm tra ô avatar có số lượng = 0 hay không:
        1. Phải có duy nhất 1 chữ số ở chân avatar.
        2. Chữ số đó phải có cấu trúc hình học lỗ rỗng màu đen ở tâm.
        3. Phân biệt với số 9: Số 0 là vòng tròn đối xứng đều ở nửa dưới (tỉ lệ pixel vàng trái/phải >= 0.88),
           trong khi số 9 có đuôi thò sang phải và nửa dưới bên trái rỗng (tỉ lệ < 0.75).
        4. Phân biệt với số 6: Số 0 có vòng cung vàng khép kín ở góc trên bên phải (top_right_yellow >= 35),
           trong khi số 6 có đuôi vểnh sang trái nên góc trên bên phải rỗng (< 25px vàng).
        """
        strip, digits = self._extract_digit_boxes(frame, row_roi)
        if len(digits) != 1:
            return False

        bx, by, bw, bh = digits[0]
        patch = strip[by:by + bh, bx:bx + bw]
        py, px = patch.shape[0] // 2, patch.shape[1] // 2
        center_area = patch[max(0, py - 3):min(patch.shape[0], py + 4), max(0, px - 3):min(patch.shape[1], px + 4)]
        if center_area.size == 0:
            return False

        black_cnt = np.count_nonzero((center_area[:, :, 0] < 65) & (center_area[:, :, 1] < 65) & (center_area[:, :, 2] < 65))
        if black_cnt < 12:
            return False

        h_p, w_p = patch.shape[:2]
        scale = frame.shape[1] / 1080.0

        # Phân biệt số 0 và số 6: Góc trên bên phải của số 0 là vòng cung vàng đầy đủ (>= 35px),
        # trong khi số 6 có nét móc sang trái nên góc trên bên phải rỗng (< 25px)
        top_right = patch[:int(0.35 * h_p), int(0.55 * w_p):]
        if top_right.size > 0:
            hsv_tr = cv2.cvtColor(top_right, cv2.COLOR_BGR2HSV)
            mask_tr = cv2.inRange(hsv_tr, np.array([12, 160, 160], dtype=np.uint8), np.array([30, 255, 255], dtype=np.uint8))
            if np.count_nonzero(mask_tr) < int(35 * (scale * scale)):
                return False  # Góc trên bên phải rỗng -> Là số 6, không phải số 0!

        # Phân biệt số 0 và số 9 dựa trên tính đối xứng nửa dưới:
        bottom_patch = patch[int(0.40 * h_p):, :]
        mid_x = bottom_patch.shape[1] // 2
        hsv_b = cv2.cvtColor(bottom_patch, cv2.COLOR_BGR2HSV)
        mask_b = cv2.inRange(hsv_b, np.array([12, 160, 160], dtype=np.uint8), np.array([30, 255, 255], dtype=np.uint8))

        cnt_l = np.count_nonzero(mask_b[:, :mid_x])
        cnt_r = np.count_nonzero(mask_b[:, mid_x:])
        symmetry_ratio = cnt_l / max(1, cnt_r)

        return symmetry_ratio >= 0.88

    def is_input_greater_than_30(self, frame: np.ndarray, row_roi: Rect) -> bool:
        """
        Kiểm tra số lượng nguyên liệu đầu vào ở ô avatar bên trái có lớn hơn 30 hay không (> 30).
        Quy tắc:
        1. Cắt strip chân avatar chuẩn xác qua _extract_digit_boxes.
        2. Phân loại theo số lượng chữ số:
           - Số lượng chữ số <= 1 (tức 0..9): Không > 30 -> False.
           - Số lượng chữ số >= 3 (tức >= 100): Chắc chắn > 30 -> True.
           - Số lượng chữ số == 2 (tức 10..99):
             + So khớp chữ số hàng chục với template:
             + Nếu hàng chục là '1' (conf >= 0.78) -> 10..19 -> False.
             + Nếu hàng chục là '2' (conf >= 0.78) -> 20..29 -> False.
             + Nếu hàng chục là '3' (conf >= 0.78) -> 30..39:
                 Kiểm tra chữ số hàng đơn vị: nếu là '0' (conf >= 0.78) -> Đúng 30 (Không > 30) -> False.
                 Nếu hàng đơn vị khác '0' -> 31..39 -> True.
             + Nếu hàng chục không phải 1, 2, 3 (là 4, 5, 6, 7, 8, 9) -> > 30 -> True.
        """
        strip, digit_boxes = self._extract_digit_boxes(frame, row_roi)
        num_digits = len(digit_boxes)

        if num_digits <= 1:
            return False
        if num_digits >= 3:
            return True

        # Đang có đúng 2 chữ số (10..99)
        # Bóc tách chữ số hàng chục (box đầu tiên) kèm viền đệm 4px
        scale = frame.shape[1] / 1080.0
        t_bx, t_by, t_bw, t_bh = digit_boxes[0]
        pad = int(4 * scale)
        py1 = max(0, t_by - pad)
        py2 = min(strip.shape[0], t_by + t_bh + pad)
        px1 = max(0, t_bx - pad)
        px2 = min(strip.shape[1], t_bx + t_bw + pad)
        crop_tens = strip[py1:py2, px1:px2]

        def _match_digit_tpl(crop_img: np.ndarray, tpl_key: str) -> float:
            tpl = self._raw_templates.get(tpl_key)
            if tpl is None:
                return 0.0
            if abs(scale - 1.0) > 0.05:
                tpl = cv2.resize(tpl, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            if crop_img.shape[0] < tpl.shape[0] or crop_img.shape[1] < tpl.shape[1]:
                # Mở rộng canvas nếu crop nhỏ hơn template một chút
                new_h = max(crop_img.shape[0], tpl.shape[0] + 4)
                new_w = max(crop_img.shape[1], tpl.shape[1] + 4)
                padded = np.zeros((new_h, new_w, 3), dtype=np.uint8)
                padded[:crop_img.shape[0], :crop_img.shape[1]] = crop_img
                crop_img = padded
            res = cv2.matchTemplate(crop_img, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_v, _, _ = cv2.minMaxLoc(res)
            return float(max_v)

        conf_1 = _match_digit_tpl(crop_tens, "digit_1")
        if conf_1 >= 0.78:
            return False  # Hàng chục là 1 (10..19) -> không > 30

        conf_2 = _match_digit_tpl(crop_tens, "digit_2")
        if conf_2 >= 0.78:
            return False  # Hàng chục là 2 (20..29) -> không > 30

        conf_3 = _match_digit_tpl(crop_tens, "digit_3")
        if conf_3 >= 0.78:
            # Hàng chục là 3: Kiểm tra chữ số hàng đơn vị (box thứ hai)
            u_bx, u_by, u_bw, u_bh = digit_boxes[1]
            uy1 = max(0, u_by - pad)
            uy2 = min(strip.shape[0], u_by + u_bh + pad)
            ux1 = max(0, u_bx - pad)
            ux2 = min(strip.shape[1], u_bx + u_bw + pad)
            crop_units = strip[uy1:uy2, ux1:ux2]
            conf_0 = _match_digit_tpl(crop_units, "input_zero")
            if conf_0 >= 0.78:
                return False  # Là số 30 đúng nghĩa -> không > 30
            return True  # 31..39 -> > 30

        # Hàng chục không phải 1, 2, 3 (là 4, 5, 6, 7, 8, 9) -> chắc chắn > 30
        return True

        num_digits = len(digit_boxes)

        if num_digits <= 1:
            return False
        if num_digits >= 3:
            return True

        # Đang có đúng 2 chữ số (10..99)
        # Bóc tách chữ số hàng chục (box đầu tiên) kèm viền đệm 4px
        t_bx, t_by, t_bw, t_bh = digit_boxes[0]
        pad = int(4 * scale)
        py1 = max(0, t_by - pad)
        py2 = min(strip.shape[0], t_by + t_bh + pad)
        px1 = max(0, t_bx - pad)
        px2 = min(strip.shape[1], t_bx + t_bw + pad)
        crop_tens = strip[py1:py2, px1:px2]

        def _match_digit_tpl(crop_img: np.ndarray, tpl_key: str) -> float:
            tpl = self._raw_templates.get(tpl_key)
            if tpl is None:
                return 0.0
            if abs(scale - 1.0) > 0.05:
                tpl = cv2.resize(tpl, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            if crop_img.shape[0] < tpl.shape[0] or crop_img.shape[1] < tpl.shape[1]:
                # Mở rộng canvas nếu crop nhỏ hơn template một chút
                new_h = max(crop_img.shape[0], tpl.shape[0] + 4)
                new_w = max(crop_img.shape[1], tpl.shape[1] + 4)
                padded = np.zeros((new_h, new_w, 3), dtype=np.uint8)
                padded[:crop_img.shape[0], :crop_img.shape[1]] = crop_img
                crop_img = padded
            res = cv2.matchTemplate(crop_img, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_v, _, _ = cv2.minMaxLoc(res)
            return float(max_v)

        conf_1 = _match_digit_tpl(crop_tens, "digit_1")
        if conf_1 >= 0.78:
            return False  # Hàng chục là 1 (10..19) -> không > 30

        conf_2 = _match_digit_tpl(crop_tens, "digit_2")
        if conf_2 >= 0.78:
            return False  # Hàng chục là 2 (20..29) -> không > 30

        conf_3 = _match_digit_tpl(crop_tens, "digit_3")
        if conf_3 >= 0.78:
            # Hàng chục là 3: Kiểm tra chữ số hàng đơn vị (box thứ hai)
            u_bx, u_by, u_bw, u_bh = digit_boxes[1]
            uy1 = max(0, u_by - pad)
            uy2 = min(strip.shape[0], u_by + u_bh + pad)
            ux1 = max(0, u_bx - pad)
            ux2 = min(strip.shape[1], u_bx + u_bw + pad)
            crop_units = strip[uy1:uy2, ux1:ux2]
            conf_0 = _match_digit_tpl(crop_units, "input_zero")
            if conf_0 >= 0.78:
                return False  # Là số 30 đúng nghĩa -> không > 30
            return True  # 31..39 -> > 30

        # Hàng chục không phải 1, 2, 3 (là 4, 5, 6, 7, 8, 9) -> chắc chắn > 30
        return True

        num_digits = len(digit_boxes)

        if num_digits <= 1:
            return False
        if num_digits >= 3:
            return True

        # Đang có đúng 2 chữ số (10..99)
        # Bóc tách chữ số hàng chục (box đầu tiên) kèm viền đệm 4px
        t_bx, t_by, t_bw, t_bh = digit_boxes[0]
        pad = int(4 * scale)
        py1 = max(0, t_by - pad)
        py2 = min(strip.shape[0], t_by + t_bh + pad)
        px1 = max(0, t_bx - pad)
        px2 = min(strip.shape[1], t_bx + t_bw + pad)
        crop_tens = strip[py1:py2, px1:px2]

        def _match_digit_tpl(crop_img: np.ndarray, tpl_key: str) -> float:
            tpl = self._raw_templates.get(tpl_key)
            if tpl is None:
                return 0.0
            if abs(scale - 1.0) > 0.05:
                tpl = cv2.resize(tpl, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)
            if crop_img.shape[0] < tpl.shape[0] or crop_img.shape[1] < tpl.shape[1]:
                # Mở rộng canvas nếu crop nhỏ hơn template một chút
                new_h = max(crop_img.shape[0], tpl.shape[0] + 4)
                new_w = max(crop_img.shape[1], tpl.shape[1] + 4)
                padded = np.zeros((new_h, new_w, 3), dtype=np.uint8)
                padded[:crop_img.shape[0], :crop_img.shape[1]] = crop_img
                crop_img = padded
            res = cv2.matchTemplate(crop_img, tpl, cv2.TM_CCOEFF_NORMED)
            _, max_v, _, _ = cv2.minMaxLoc(res)
            return float(max_v)

        conf_1 = _match_digit_tpl(crop_tens, "digit_1")
        if conf_1 >= 0.80:
            return False  # Hàng chục là 1 (10..19) -> không > 30

        conf_2 = _match_digit_tpl(crop_tens, "digit_2")
        if conf_2 >= 0.80:
            return False  # Hàng chục là 2 (20..29) -> không > 30

        conf_3 = _match_digit_tpl(crop_tens, "digit_3")
        if conf_3 >= 0.80:
            # Hàng chục là 3: Kiểm tra chữ số hàng đơn vị (box thứ hai)
            u_bx, u_by, u_bw, u_bh = digit_boxes[1]
            uy1 = max(0, u_by - pad)
            uy2 = min(strip.shape[0], u_by + u_bh + pad)
            ux1 = max(0, u_bx - pad)
            ux2 = min(strip.shape[1], u_bx + u_bw + pad)
            crop_units = strip[uy1:uy2, ux1:ux2]
            conf_0 = _match_digit_tpl(crop_units, "input_zero")
            if conf_0 >= 0.78:
                return False  # Là số 30 đúng nghĩa -> không > 30
            return True  # 31..39 -> > 30

        # Hàng chục không phải 1, 2, 3 (là 4, 5, 6, 7, 8, 9) -> chắc chắn > 30
        return True

    def check_row_for_targets(
        self,
        frame: np.ndarray,
        row_roi: Rect,
        min_threshold: float = 0.80,
        enable_phuc_tung: bool = False,
        phuc_tung_threshold: float = 0.78,
        enable_coin_300k: bool = False,
        coin_threshold: float = 0.80
    ) -> Tuple[MatchResult, str]:
        """
        Kiểm tra một dòng cụ thể xem có chứa mục tiêu nhận quà hay không:
        1. Luôn ưu tiên kiểm tra Kim Cương: 'kim_cuong_inner', 'kim_cuong'
        2. Nếu bật enable_phuc_tung: kiểm tra thêm Phục Tùng C ('phuc_tung_c_inner', 'phuc_tung_c_icon', 'phuc_tung_c_text')
        3. Nếu bật enable_coin_300k: kiểm tra thêm phần thưởng 300,000 Coin ('coin_300k', 'coin_300000_text')
        Trả về (MatchResult, target_type) với target_type là 'DIAMOND', 'PHUC_TUNG_C', 'COIN_300K' hoặc 'NONE'.
        """
        # 1. Ưu tiên kiểm tra Kim Cương
        diamond_match = self.check_row_for_diamond(frame, row_roi, min_threshold)
        if diamond_match.found:
            return diamond_match, "DIAMOND"

        # 2. Nếu bật săn thêm Phục Tùng
        if enable_phuc_tung:
            best_pt = MatchResult(found=False, confidence=0.0)
            pt_keys = ["phuc_tung_c_inner", "phuc_tung_c_icon", "phuc_tung_c_text"]
            for pt_key in pt_keys:
                match_pt = self.find_template(
                    frame=frame,
                    template_key_or_path=pt_key,
                    threshold=0.0,
                    roi=row_roi
                )
                if match_pt.confidence > best_pt.confidence:
                    best_pt = match_pt

            if best_pt.confidence >= phuc_tung_threshold:
                best_pt.found = True
                return best_pt, "PHUC_TUNG_C"

        # 3. Nếu bật xả kho Coin 300k
        if enable_coin_300k:
            best_coin = MatchResult(found=False, confidence=0.0)
            coin_keys = ["coin_300k", "coin_300000_text"]
            for c_key in coin_keys:
                match_c = self.find_template(
                    frame=frame,
                    template_key_or_path=c_key,
                    threshold=0.0,
                    roi=row_roi
                )
                if match_c.confidence > best_coin.confidence:
                    best_coin = match_c

            if best_coin.confidence >= coin_threshold:
                best_coin.found = True
                return best_coin, "COIN_300K"

        return diamond_match, "NONE"

    def find_best_matching_row(
        self,
        frame: np.ndarray,
        template_key_or_path: Union[str, Path],
        rows: List[Rect],
        min_threshold: float = 0.80
    ) -> Tuple[Optional[int], Optional[MatchResult], List[float]]:
        """
        Quét tất cả các dòng (ROIs), so khớp template và trả về dòng có điểm cao nhất.
        """
        # Sử dụng duy nhất mẫu 'kim_cuong'
        template_keys = [template_key_or_path]
        if str(template_key_or_path) == "kim_cuong":
            template_keys = ["kim_cuong"]

        best_overall_idx = None
        best_overall_match = None
        best_overall_scores = []
        highest_score = -1.0

        f_h, f_w = frame.shape[:2]

        for t_key in template_keys:
            scores: List[float] = []
            matches: List[MatchResult] = []

            for i, row_roi in enumerate(rows):
                match = self.find_template(
                    frame=frame,
                    template_key_or_path=t_key,
                    threshold=0.0,
                    roi=row_roi
                )
                scores.append(match.confidence)
                matches.append(match)

            if scores:
                idx = int(np.argmax(scores))
                if scores[idx] > highest_score:
                    highest_score = scores[idx]
                    best_overall_idx = idx
                    best_overall_match = matches[idx]
                    best_overall_scores = scores

        if best_overall_scores:
            logger.info(f"Frame ({f_w}x{f_h}) -> Điểm quét từng dòng: {[round(s, 3) for s in best_overall_scores]} (Dòng cao nhất: #{best_overall_idx+1}: {highest_score:.3f})")

        if highest_score >= min_threshold and best_overall_match is not None:
            best_overall_match.found = True
            return best_overall_idx, best_overall_match, best_overall_scores
        else:
            logger.warning(f"Không có dòng nào đạt ngưỡng {min_threshold:.2f} (Điểm cao nhất: #{best_overall_idx+1 if best_overall_idx is not None else '?'} = {highest_score:.3f})")
            return None, best_overall_match, best_overall_scores

    def save_debug_image(
        self,
        frame: np.ndarray,
        label: str,
        highlight_rects: Optional[List[Union[Rect, Tuple[int, int, int, int]]]] = None,
        highlight_points: Optional[List[Tuple[int, int]]] = None
    ) -> Path:
        """Lưu ảnh debug kèm các vùng highlight."""
        debug_img = frame.copy()

        if highlight_rects:
            for r in highlight_rects:
                if isinstance(r, Rect):
                    cv2.rectangle(debug_img, (r.x, r.y), (r.x2, r.y2), (0, 255, 0), 2)
                elif isinstance(r, (tuple, list)) and len(r) == 4:
                    cv2.rectangle(debug_img, (r[0], r[1]), (r[0] + r[2], r[1] + r[3]), (0, 255, 0), 2)

        if highlight_points:
            for pt in highlight_points:
                cv2.circle(debug_img, pt, 8, (0, 0, 255), -1)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{label}.png"
        out_path = DEBUG_DIR / filename
        cv2.imwrite(str(out_path), debug_img)
        logger.info(f"Đã lưu ảnh debug: {out_path}")
        return out_path
