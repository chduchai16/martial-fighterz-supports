"""
Cấu hình hệ thống bot tự động hoá game trên MuMu Player / LDPlayer.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys


def _resolve_base_dir() -> Path:
    """
    Trả về thư mục gốc chứa images/, assets/ ... (read-only bundled data).
    - PyInstaller 6.x: data files nằm trong sys._MEIPASS (_internal/).
    - Dev mode (src/core): tính ngược 3 cấp để về gốc dự án.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        return Path(__file__).resolve().parent.parent.parent


def _resolve_writable_dir() -> Path:
    """
    Trả về thư mục có thể ghi được (logs, debug) cạnh exe khi frozen,
    hoặc gốc dự án khi dev mode.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    else:
        return Path(__file__).resolve().parent.parent.parent


# Thư mục gốc dự án (bundled assets)
BASE_DIR = _resolve_base_dir()
# Thư mục có thể ghi (logs, debug) - cạnh exe khi frozen
WRITABLE_DIR = _resolve_writable_dir()
# Ưu tiên thư mục assets/templates nếu có, fallback về images/
IMAGES_DIR = BASE_DIR / "assets" / "templates" if (BASE_DIR / "assets" / "templates").exists() else BASE_DIR / "images"
DEBUG_DIR = WRITABLE_DIR / "debug_dumps"
LOGS_DIR = WRITABLE_DIR / "logs"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)



@dataclass
class Rect:
    """Đại diện cho 1 vùng chữ nhật (x, y, width, height)"""
    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return self.x, self.y, self.w, self.h


@dataclass
class BotConfig:
    # Cấu hình thiết bị ADB (MuMu Player: 16384/7555, LDPlayer: 5555)
    adb_host: str = "127.0.0.1"
    adb_port: int = 16384
    device_serial: Optional[str] = None
    
    # Độ phân giải cố định (Logic trong Android: W x H)
    target_width: int = 1080
    target_height: int = 1920

    # Cấu hình capture
    scrcpy_max_fps: int = 30
    scrcpy_bitrate: int = 8000000
    
    # Template matching thresholds (Kim Cương >= 0.80 theo yêu cầu)
    default_threshold: float = 0.80
    diamond_threshold: float = 0.80  # Ngưỡng nhận diện Kim Cương >= 0.80
    phuc_tung_threshold: float = 0.78  # Ngưỡng nhận diện Phục Tùng (C & D)
    button_threshold: float = 0.78
    rut_lui_threshold: float = 0.72  # Ngưỡng nhận diện nút Rút lui (kèm ROI chống nhận diện nhầm)
    ok_threshold: float = 0.72

    # Chiến lược chọn Even/Odd (Mặc định chọn CHẴN)
    even_odd_strategy: str = "even"

    # Tuỳ chọn ăn thêm Phục Tùng C & D và Ngôn ngữ game
    enable_phuc_tung: bool = False
    game_language: str = "auto"  # "auto", "vi", "en"

    # Số lần nhận quà tối đa cho mỗi dòng item
    vip7_rounds_per_row: int = 2  # VIP7 tối đa 2 lần
    vip9_rounds_per_row: int = 3  # VIP9 tối đa 3 lần

    # Số lần thử lại tối đa
    max_retries_per_step: int = 4
    retry_interval_sec: float = 0.3

    # Thời gian chờ phản hồi tối ưu (giây) - Phản xạ nhanh, không đứng im vô nghĩa
    api_loading_timeout: float = 15.0   # Chờ API xúc xắc + mở quà tối đa 15s (sẽ click ngay lập tức khi xuất hiện)
    reset_api_timeout: float = 8.0      # Chờ API Reset tối đa 8s
    wait_after_tap: float = 0.08        # Giảm từ 0.25s -> 0.08s sau cú tap
    wait_after_vip_open: float = 0.15   # Giảm từ 0.6s -> 0.15s sau khi bấm Tab VIP
    wait_after_even_odd: float = 0.15   # Giảm từ 0.5s -> 0.15s sau khi bấm Even/Odd
    wait_after_rut_lui: float = 0.10    # Giảm từ 0.4s -> 0.10s sau khi bấm Rút lui
    wait_after_reset: float = 0.50      # Giảm từ 1.0s -> 0.50s sau khi bấm Reset
    wait_after_scroll: float = 0.25     # Giảm từ 0.5s -> 0.25s sau khi cuộn trang

    # Độ lệch pixel ngẫu nhiên khi tap
    tap_jitter_px: int = 4

    # Đường dẫn template ảnh mẫu
    templates: Dict[str, Path] = field(default_factory=lambda: {
        "kim_cuong": IMAGES_DIR / "kim_cuong_icon.png",
        "kim_cuong_inner": IMAGES_DIR / "kim_cuong_inner.png",
        "kim_cuong_clean_en": IMAGES_DIR / "diamond_crystal_clean_en.png",
        "phuc_tung_c_icon": IMAGES_DIR / "phuc_tung_c_icon.png",
        "phuc_tung_c_inner": IMAGES_DIR / "phuc_tung_c_inner.png",
        "phuc_tung_c_text": IMAGES_DIR / "phuc_tung_c_text.png",
        "vip7_tab": IMAGES_DIR / "vip7_tab.png",
        "vip9_tab": IMAGES_DIR / "vip9_tab.png",
        "even_btn": IMAGES_DIR / "even_button.png",
        "odd_btn": IMAGES_DIR / "odd_button.png",
        "rut_lui_btn": IMAGES_DIR / "rut_lui_button.png",
        "withdraw_btn": IMAGES_DIR / "withdraw_button.png",
        "ok_btn": IMAGES_DIR / "ok_button.png",
        "ok_btn_vi": IMAGES_DIR / "ok_button_vi.png",
        "out_of_items_en": IMAGES_DIR / "out_of_items_en.png",
        "exchange_not_available_en": IMAGES_DIR / "exchange_not_available_en.png",
        "arale_header": IMAGES_DIR / "arale_header.png",
        "no_turns_text": IMAGES_DIR / "no_turns_text.png",
        "out_of_items_text": IMAGES_DIR / "out_of_items_text.png",
        "warrior_gem_text": IMAGES_DIR / "warrior_gem_text.png",
        "warrior_gem_en": IMAGES_DIR / "warrior_gem_en.png",
        "warrior_gem_full_en": IMAGES_DIR / "warrior_gem_full_en.png",
        "reset_btn": IMAGES_DIR / "reset_button.png",
    })

    # Toạ độ 3 dòng VIP7
    vip7_rows_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.0088, 0.5848, 0.9824, 0.1262),  # Dòng 1 VIP7
        (0.0088, 0.7219, 0.9824, 0.1262),  # Dòng 2 VIP7
        (0.0088, 0.8599, 0.9824, 0.1000),  # Dòng 3 VIP7
    ])

    # Toạ độ 3 dòng VIP9 ban đầu (Dòng 1, 2, 3 - không cần cuộn)
    vip9_initial_rows_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.0088, 0.5848, 0.9824, 0.1262),  # Dòng 1 VIP9 (Top)
        (0.0088, 0.7219, 0.9824, 0.1262),  # Dòng 2 VIP9 (Mid)
        (0.0088, 0.8150, 0.9824, 0.1262),  # Dòng 3 VIP9 (Bot - chưa cuộn)
    ])

    # Toạ độ duy nhất cho DÒNG 4 VIP9 sau khi cuộn lên (nhích cao lên: y/H = 0.8150)
    vip9_scrolled_rows_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.0088, 0.8150, 0.9824, 0.1262),  # Duy nhất Dòng 4 VIP9 sau khi cuộn
    ])

    # Toạ độ vuốt cuộn nằm hoàn toàn bên trong khung khay item (Y từ 62% đến 90% màn hình)
    # Swipe UP: Chạm tại 90% kéo lên 62%
    # Swipe DOWN: Chạm tại 62% kéo xuống 90%
    swipe_vip9_start_ratio: Tuple[float, float] = (0.50, 0.90)
    swipe_vip9_end_ratio: Tuple[float, float] = (0.50, 0.62)

    @property
    def vip7_rows(self) -> List[Rect]:
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip7_rows_ratio
        ]

    @property
    def vip9_initial_rows(self) -> List[Rect]:
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip9_initial_rows_ratio
        ]

    @property
    def vip9_scrolled_rows(self) -> List[Rect]:
        """Danh sách chứa duy nhất Dòng 4 của VIP9 sau khi cuộn lên."""
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip9_scrolled_rows_ratio
        ]

    # Toạ độ click trực tiếp dự phòng
    @property
    def vip7_tab_pos(self) -> Tuple[int, int]:
        return int(0.785 * self.target_width), int(0.228 * self.target_height)

    @property
    def vip9_tab_pos(self) -> Tuple[int, int]:
        return int(0.913 * self.target_width), int(0.228 * self.target_height)

    @property
    def even_btn_pos(self) -> Tuple[int, int]:
        return int(0.871 * self.target_width), int(0.420 * self.target_height)

    @property
    def odd_btn_pos(self) -> Tuple[int, int]:
        return int(0.871 * self.target_width), int(0.327 * self.target_height)

    @property
    def rut_lui_roi(self) -> Rect:
        """Vùng xuất hiện nút Rút lui (ở giữa màn hình dọc theo trục Y từ 50% đến 75%)."""
        return Rect(
            x=int(0.15 * self.target_width),
            y=int(0.50 * self.target_height),
            w=int(0.70 * self.target_width),
            h=int(0.25 * self.target_height)
        )

    @property
    def ok_roi(self) -> Rect:
        """Vùng xuất hiện nút OK (ở nửa dưới màn hình dọc theo trục Y từ 55% đến 91%, bao quát cả popup mới lẫn popup Warrior Gem/cũ)."""
        return Rect(
            x=int(0.15 * self.target_width),
            y=int(0.55 * self.target_height),
            w=int(0.70 * self.target_width),
            h=int(0.36 * self.target_height)
        )

    @property
    def rut_lui_btn_pos(self) -> Tuple[int, int]:
        return int(0.500 * self.target_width), int(0.630 * self.target_height)  # (540, 1210)

    @property
    def ok_btn_pos(self) -> Tuple[int, int]:
        """Toạ độ nút OK trên giao diện cuộn thư mới (542, 1340 trên 1080x1920)."""
        return int(0.502 * self.target_width), int(0.698 * self.target_height)

    @property
    def reset_btn_pos(self) -> Tuple[int, int]:
        return int(0.127 * self.target_width), int(0.232 * self.target_height)


config = BotConfig()
