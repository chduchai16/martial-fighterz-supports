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
    - Dev mode:        tìm thư mục gốc chứa images/ hoặc assets/.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    
    curr = Path(__file__).resolve().parent
    for p in [curr, curr.parent, curr.parent.parent]:
        if ((p / "images").exists() and any((p / "images").iterdir())) or (p / "assets" / "templates").exists():
            return p
    return curr


def _resolve_writable_dir() -> Path:
    """
    Trả về thư mục có thể ghi được (logs, debug) cạnh exe khi frozen,
    hoặc gốc dự án khi dev mode.
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    
    curr = Path(__file__).resolve().parent
    for p in [curr, curr.parent, curr.parent.parent]:
        if (p / "main.py").exists() or (p / "gui_app.py").exists():
            return p
    return curr


# Thư mục gốc dự án (bundled assets)
BASE_DIR = _resolve_base_dir()
# Thư mục có thể ghi (logs, debug) - cạnh exe khi frozen
WRITABLE_DIR = _resolve_writable_dir()

def _resolve_images_dir(base: Path) -> Path:
    img_dir = base / "images"
    tpl_dir = base / "assets" / "templates"
    if img_dir.exists() and any(img_dir.iterdir()):
        return img_dir
    if tpl_dir.exists():
        return tpl_dir
    return img_dir

IMAGES_DIR = _resolve_images_dir(BASE_DIR)
DEBUG_DIR = WRITABLE_DIR / "debug_dumps"
LOGS_DIR = WRITABLE_DIR / "logs"

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
    ok_threshold: float = 0.76

    # Chiến lược chọn Even/Odd (Mặc định chọn CHẴN)
    even_odd_strategy: str = "even"

    # Tuỳ chọn ăn thêm Phục Tùng C & D, xả Coin 300k và Ngôn ngữ game
    enable_phuc_tung: bool = False
    dump_coin_300k: bool = True  # Tự động xả Coin 300k khi input item > 30
    coin_threshold: float = 0.75  # Ngưỡng nhận diện reward 300,000 Coin (đặt 0.75 an toàn, chống trượt)
    game_language: str = "auto"  # "auto", "vi", "en"

    # Số lần nhận quà tối đa cho mỗi dòng item
    vip7_rounds_per_row: int = 2  # VIP7 tối đa 2 lần
    vip9_rounds_per_row: int = 3  # VIP9 tối đa 3 lần

    # Số lần thử lại tối đa
    max_retries_per_step: int = 4
    retry_interval_sec: float = 0.3

    # Thời gian chờ phản hồi tối ưu (giây) - Phản xạ nhanh, không đứng im vô nghĩa
    api_loading_timeout: float = 60.0   # Chờ API xúc xắc + mở quà tối đa 60s (1 phút khi server lag)
    round_claim_timeout: float = 60.0   # Chờ nút Withdraw hoặc popup OK tối đa 60s (1 phút)
    reset_api_timeout: float = 8.0      # Chờ API Reset tối đa 8s
    wait_after_tap: float = 0.04        # Giảm còn 40ms
    wait_after_vip_open: float = 0.25   # Đợi 250ms cho tab VIP chuyển cảnh ổn định
    wait_after_even_odd: float = 0.04   # Giảm còn 40ms sau khi bấm Even/Odd
    wait_after_rut_lui: float = 0.05    # Giảm còn 50ms sau khi bấm Rút lui
    wait_after_reset: float = 0.20      # Giảm còn 200ms sau khi bấm Reset
    wait_after_scroll: float = 0.35     # Đợi swipe và quán tính cuộn dừng hẳn (350ms)

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
        "input_zero": IMAGES_DIR / "input_zero.png",
        "digit_1": IMAGES_DIR / "digit_1.png",
        "digit_2": IMAGES_DIR / "digit_2.png",
        "digit_3": IMAGES_DIR / "digit_3.png",
        "coin_300k": IMAGES_DIR / "coin_300k.png",
        "coin_300000_text": IMAGES_DIR / "coin_300000_text.png",
        "loading_text": IMAGES_DIR / "loading_text.png",
    })

    # Toạ độ Ô THỨ 1 (Min Earning) chuẩn xác ôm trọn khung vật phẩm (230x250 px)
    # Slot 1: x_ratio = 0.5833 (x=630), w_ratio = 0.2130 (w=230), h_ratio = 0.1302 (h=250)
    # Dòng 1: y=1110 (ratio 0.5781), Dòng 2: y=1373 (ratio 0.7151)
    vip7_initial_rows_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.5833, 0.5781, 0.2130, 0.1302),  # Ô 1 Dòng 1 VIP7 (x=630, y=1110, w=230, h=250) -> Kim Cương (conf >= 0.88)
        (0.5833, 0.7151, 0.2130, 0.1302),  # Ô 1 Dòng 2 VIP7 (x=630, y=1373, w=230, h=250) -> Kim Cương (conf >= 0.88)
    ])

    # Toạ độ Ô THỨ 1 Dòng 3 của VIP7 sau khi cuộn lên
    # CHÚ Ý: Sau khi cuộn, Dòng 2 bị trôi lên trên (y ≈ 1220, cy ≈ 1343).
    # Dòng 3 THỰC SỰ mới trồi lên ở vị trí đáy (y ≈ 1490 -> 1550, cy ≈ 1620 -> 1675).
    vip7_scrolled_row3_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.5833, 0.7760, 0.2130, 0.1302),  # Ô 1 Dòng 3 VIP7 thực sự sau cuộn (y=1490, cy=1615)
        (0.5833, 0.8042, 0.2130, 0.1302),  # Dự phòng vị trí cuộn sâu hơn (y=1544, cy=1669)
    ])

    # Toạ độ Ô THỨ 1 (Min Earning) của VIP9 ban đầu (Dòng 1, Dòng 2)
    vip9_initial_rows_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.5833, 0.5781, 0.2130, 0.1302),  # Ô 1 Dòng 1 VIP9 (x=630, y=1110, w=230, h=250)
        (0.5833, 0.7151, 0.2130, 0.1302),  # Ô 1 Dòng 2 VIP9 (x=630, y=1373, w=230, h=250)
    ])

    # Toạ độ Ô THỨ 1 Dòng 3 của VIP9 sau khi cuộn 1 lần duy nhất
    vip9_scrolled_row3_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.5833, 0.6354, 0.2130, 0.1302),  # Ô 1 Dòng 3 VIP9 (y=1220)
        (0.5833, 0.6661, 0.2130, 0.1302),  # Dự phòng (y=1279)
    ])

    # Toạ độ Ô THỨ 1 Dòng 4 của VIP9 sau khi cuộn 1 lần duy nhất
    vip9_scrolled_row4_ratio: List[Tuple[float, float, float, float]] = field(default_factory=lambda: [
        (0.5833, 0.7700, 0.2130, 0.1302),  # Ô 1 Dòng 4 VIP9 (y=1478)
        (0.5833, 0.8042, 0.2130, 0.1302),  # Dự phòng (y=1544)
    ])

    # Toạ độ vuốt cuộn nằm an toàn bên trong khay item (tránh thanh điều hướng Home/Adventure ở đáy)
    # Swipe UP: Chạm tại Y=82% vuốt lên Y=60%
    # Swipe DOWN: Chạm tại Y=60% vuốt xuống Y=82%
    swipe_vip9_start_ratio: Tuple[float, float] = (0.40, 0.82)
    swipe_vip9_end_ratio: Tuple[float, float] = (0.40, 0.60)

    @property
    def vip7_initial_rows(self) -> List[Rect]:
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip7_initial_rows_ratio
        ]

    @property
    def vip7_scrolled_row3_candidates(self) -> List[Rect]:
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip7_scrolled_row3_ratio
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
    def vip9_scrolled_row3_candidates(self) -> List[Rect]:
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip9_scrolled_row3_ratio
        ]

    @property
    def vip9_scrolled_row4_candidates(self) -> List[Rect]:
        return [
            Rect(
                x=int(r[0] * self.target_width),
                y=int(r[1] * self.target_height),
                w=int(r[2] * self.target_width),
                h=int(r[3] * self.target_height),
            )
            for r in self.vip9_scrolled_row4_ratio
        ]

    # Thuộc tính tương thích ngược
    @property
    def vip7_rows(self) -> List[Rect]:
        return self.vip7_initial_rows

    @property
    def vip9_scrolled_rows(self) -> List[Rect]:
        return self.vip9_scrolled_row4_candidates

    # Toạ độ click trực tiếp dự phòng
    @property
    def vip7_tab_pos(self) -> Tuple[int, int]:
        return int(0.785 * self.target_width), int(0.228 * self.target_height)

    @property
    def vip9_tab_pos(self) -> Tuple[int, int]:
        return int(0.913 * self.target_width), int(0.228 * self.target_height)

    @property
    def even_btn_pos(self) -> Tuple[int, int]:
        return int(0.875 * self.target_width), int(0.422 * self.target_height)

    @property
    def odd_btn_pos(self) -> Tuple[int, int]:
        return int(0.875 * self.target_width), int(0.328 * self.target_height)

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
        """Vùng xuất hiện nút OK (bao quát cả popup nhỏ y=1334 lẫn popup Arale y=1685, Y từ 62% đến 92%)."""
        return Rect(
            x=int(0.20 * self.target_width),
            y=int(0.62 * self.target_height),
            w=int(0.60 * self.target_width),
            h=int(0.30 * self.target_height)
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
        return int(0.135 * self.target_width), int(0.233 * self.target_height)

    def get_input_quantity_roi(self, row_roi: Rect) -> Rect:
        """
        Vùng số lượng nguyên liệu đầu vào ở chân avatar bên trái.
        row_roi là ô phần thưởng bên phải của cùng dòng.
        """
        w, h = self.target_width, self.target_height
        qx = int(0.120 * w)
        qw = int(0.070 * w)
        qy = row_roi.y + int(36 * (h / 1920.0))
        qh = int(44 * (h / 1920.0))
        return Rect(x=qx, y=qy, w=qw, h=qh)


config = BotConfig()
