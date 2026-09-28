"""
Quản lý toạ độ các nút, box và các item trên giao diện game.
Tự động scale theo tỷ lệ màn hình (từ ảnh gốc 565x1009 sang 1080x1920 hoặc kích thước thật của LDPlayer).
"""
import json
from pathlib import Path
from typing import Dict, Tuple

from config import Rect

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
COORD_FILE = (
    ROOT_DIR / "assets" / "coordinates.json"
    if (ROOT_DIR / "assets" / "coordinates.json").exists()
    else ROOT_DIR / "coordinates.json"
)


class CoordinateManager:
    def __init__(self, target_w: int = 1080, target_h: int = 1920):
        self.target_w = target_w
        self.target_h = target_h
        self.data = {}
        self.load()

    def load(self):
        if COORD_FILE.exists():
            with open(COORD_FILE, "r", encoding="utf-8") as f:
                self.data = json.load(f)

    def set_target_resolution(self, w: int, h: int):
        self.target_w = w
        self.target_h = h

    def get_rect(self, element_key: str) -> Rect:
        """Lấy Rect(x, y, w, h) của phần tử đã được scale theo độ phân giải hiện tại."""
        elem = self.data.get("elements", {}).get(element_key)
        if not elem:
            raise KeyError(f"Không tìm thấy phần tử '{element_key}' trong coordinates.json")

        ratio = elem["ratio"]
        x = int(ratio["x"] * self.target_w)
        y = int(ratio["y"] * self.target_h)
        w = int(ratio["w"] * self.target_w)
        h = int(ratio["h"] * self.target_h)
        return Rect(x=x, y=y, w=w, h=h)

    def get_center(self, element_key: str) -> Tuple[int, int]:
        """Lấy toạ độ điểm chính giữa (cx, cy) để tap."""
        r = self.get_rect(element_key)
        return r.center

    def update_element(self, element_key: str, description: str, rect_tuple: Tuple[int, int, int, int], ref_w: int, ref_h: int):
        """Cập nhật hoặc thêm mới toạ độ 1 phần tử."""
        x, y, w, h = rect_tuple
        if "elements" not in self.data:
            self.data["elements"] = {}

        self.data["elements"][element_key] = {
            "description": description,
            "box_raw": {"x": x, "y": y, "w": w, "h": h},
            "ratio": {
                "x": round(x / ref_w, 4),
                "y": round(y / ref_h, 4),
                "w": round(w / ref_w, 4),
                "h": round(h / ref_h, 4)
            }
        }
        with open(COORD_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)


# Instance toàn cục
coords = CoordinateManager()
