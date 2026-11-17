import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from src.core.config import BotConfig
from src.core.vision import VisionEngine

def test_frequency_zero_detection():
    cfg = BotConfig(target_width=1080, target_height=1920)
    v = VisionEngine(cfg.templates)

    img_now = cv2.imread(str(ROOT / "images" / "live_vip7_r1_now.png"))
    img_q = cv2.imread(str(ROOT / "debug_crops" / "live_user_question.png"))
    if img_q is None:
        img_q = cv2.imread(str(ROOT / "images" / "live_vip7_r1_dia_err.png"))

    # 1. North Kai ở Dòng 1 có Frequency: 0 -> Bắt buộc là True!
    if img_now is not None:
        r1 = cfg.vip7_initial_rows[0]
        assert v.is_frequency_zero(img_now, r1) is True, "North Kai Frequency 0 MUST be True!"

        # Dòng 2 Fox Mask có Frequency: 3 -> Bắt buộc là False!
        r2 = cfg.vip7_initial_rows[1]
        assert v.is_frequency_zero(img_now, r2) is False, "Fox Mask Frequency 3 MUST be False!"

    # 2. Dòng có Frequency: 3 -> Bắt buộc là False!
    if img_q is not None:
        r1_q = cfg.vip7_initial_rows[0]
        assert v.is_frequency_zero(img_q, r1_q) is False, "Row with Frequency 3 MUST be False!"

    print("ALL_FREQUENCY_TESTS_PASSED")

if __name__ == "__main__":
    test_frequency_zero_detection()
