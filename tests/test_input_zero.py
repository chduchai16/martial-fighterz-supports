import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from src.core.config import BotConfig, Rect
from src.core.vision import VisionEngine

def test_zero_detection():
    cfg = BotConfig(target_width=1080, target_height=1920)
    vision = VisionEngine(cfg.templates)
    img = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    assert img is not None, "Live sample image must exist"

    # Row 1 (45 items): must NOT be zero
    r1 = Rect(630, 1109, 230, 250)
    q1 = cfg.get_input_quantity_roi(r1)
    assert not vision.is_input_zero(img, q1), "Row 1 (45 items) must NOT be detected as zero"

    # Row 2 (0962 items): must NOT be zero (leading zero in 4 digits)
    r2 = Rect(630, 1372, 230, 250)
    q2 = cfg.get_input_quantity_roi(r2)
    assert not vision.is_input_zero(img, q2), "Row 2 (0962 items) must NOT be detected as zero"

    # Row 3 (0 items): MUST be zero
    r3 = Rect(630, 1636, 230, 250)
    q3 = cfg.get_input_quantity_roi(r3)
    assert vision.is_input_zero(img, q3), "Row 3 (0 items) MUST be detected as zero"

    print("ALL_ZERO_ASSERTIONS_PASSED")

if __name__ == "__main__":
    test_zero_detection()
