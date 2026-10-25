import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from src.core.config import BotConfig, Rect
from src.core.vision import VisionEngine

def test_all():
    cfg = BotConfig(target_width=1080, target_height=1920)
    v = VisionEngine(cfg.templates)
    
    # 1. Ảnh live VIP9 sau cuộn (Curse Collar = 0):
    f_scroll = cv2.imread(str(ROOT / "debug_crops" / "live_vip9_scrolled.png"))
    # Dòng 4 sau cuộn roi_r4 có cy ≈ 1634 (Rect(614, 1468, 230, 316) hoặc dyn_roi):
    r4 = Rect(614, 1504, 230, 260) # cy = 1634
    assert v.is_input_zero(f_scroll, r4), "Dòng 4 VIP9 (Curse Collar = 0) PHẢI phát hiện là Zero!"

    # 2. Ảnh live VIP7:
    f_init = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    # Row 1 (Recoome 45, cy = 1233):
    assert not v.is_input_zero(f_init, cfg.vip7_initial_rows[0]), "Dòng 1 VIP7 (45) KHÔNG được là Zero!"
    # Row 2 (Saiyan 0962, cy = 1496):
    assert not v.is_input_zero(f_init, cfg.vip7_initial_rows[1]), "Dòng 2 VIP7 (0962) KHÔNG được là Zero!"
    # Row 3 (Ginyu 0, cy ≈ 1662):
    r3_vip7 = Rect(630, 1636, 230, 250)
    assert v.is_input_zero(f_init, r3_vip7), "Dòng 3 VIP7 (Ginyu 0) PHẢI phát hiện là Zero!"

    print("ALL_TEST_ASSERTIONS_PASSED_100_PERCENT!")

if __name__ == "__main__":
    test_all()
