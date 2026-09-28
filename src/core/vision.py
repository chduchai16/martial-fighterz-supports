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

from config import DEBUG_DIR, Rect

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
        best_res = MatchResult(found=False, confidence=0.0)

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

        return best_res

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
        # Nếu đang tìm kim cương, thử cả cụm kim cương inner lẫn icon đầy đủ
        template_keys = [template_key_or_path]
        if str(template_key_or_path) == "kim_cuong":
            template_keys = ["kim_cuong_inner", "kim_cuong"]

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
