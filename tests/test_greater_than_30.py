import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from src.core.config import BotConfig, Rect
from src.core.vision import VisionEngine

def test_greater_than_30_cases():
    cfg = BotConfig(target_width=1080, target_height=1920)
    vision = VisionEngine(cfg.templates)

    img = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    assert img is not None, "Live sample image must exist"

    # Case 1: Row 1 Recoome có số lượng là 45 (> 30) -> Phải trả về True!
    r1 = Rect(630, 1109, 230, 250)
    res_45 = vision.is_input_greater_than_30(img, r1)
    print("Test Row 1 (45):", res_45)
    assert res_45 is True, "Recoome (45) MUST be > 30!"

    # Case 2: Row 2 Saiyan có số lượng là 0962 (> 30, 4 chữ số) -> Phải trả về True!
    r2 = Rect(630, 1372, 230, 250)
    res_962 = vision.is_input_greater_than_30(img, r2)
    print("Test Row 2 (0962):", res_962)
    assert res_962 is True, "Saiyan (0962) MUST be > 30!"

    # Case 3: Row 3 Ginyu có số lượng là 0 (<= 30, 1 chữ số) -> Phải trả về False!
    r3 = Rect(630, 1636, 230, 250)
    res_0 = vision.is_input_greater_than_30(img, r3)
    print("Test Row 3 (0):", res_0)
    assert res_0 is False, "Ginyu (0) MUST NOT be > 30!"

    # Case 4: Giả lập số 12 và 25 trên nền r1:
    # Thay box hàng chục của 45 thành template 1 (tạo số 15) -> phải là False
    tpl_1 = cv2.imread(str(ROOT / "assets" / "templates" / "digit_1.png"))
    h1, w1 = tpl_1.shape[:2]
    # Tọa độ số 4 của Recoome trên full image: y ≈ 1135..1175, x ≈ 138..175
    # Strip y1 = 1234 - 100 = 1134
    mock_15 = img.copy()
    # Vẽ đè template 1 vào vị trí số 4 (x: 140, y: 1154)
    # Xóa nền số 4 cũ bằng màu đen
    mock_15[1150:1185, 135:168] = [10, 10, 10]
    mock_15[1154:1154+h1, 142:142+w1] = tpl_1
    res_15 = vision.is_input_greater_than_30(mock_15, r1)
    print("Test Mock 15 (hang chuc la 1):", res_15)
    assert res_15 is False, "Mock (15) MUST NOT be > 30!"

    # Case 5: Giả lập số 25 (hàng chục là 2) -> phải là False
    tpl_2 = cv2.imread(str(ROOT / "assets" / "templates" / "digit_2.png"))
    h2, w2 = tpl_2.shape[:2]
    mock_25 = img.copy()
    mock_25[1150:1185, 135:172] = [10, 10, 10]
    mock_25[1153:1153+h2, 138:138+w2] = tpl_2
    res_25 = vision.is_input_greater_than_30(mock_25, r1)
    print("Test Mock 25 (hang chuc la 2):", res_25)
    assert res_25 is False, "Mock (25) MUST NOT be > 30!"

    # Case 6: Giả lập số 30 đúng (hàng chục là 3, đơn vị là 0) -> phải là False
    tpl_3 = cv2.imread(str(ROOT / "assets" / "templates" / "digit_3.png"))
    tpl_0 = cv2.imread(str(ROOT / "assets" / "templates" / "input_zero.png"))
    h3, w3 = tpl_3.shape[:2]
    h0, w0 = tpl_0.shape[:2]
    mock_30 = img.copy()
    mock_30[1150:1185, 135:205] = [10, 10, 10]
    mock_30[1153:1153+h3, 138:138+w3] = tpl_3
    mock_30[1153:1153+h0, 170:170+w0] = tpl_0
    res_30 = vision.is_input_greater_than_30(mock_30, r1)
    print("Test Mock 30 (hang chuc 3, don vi 0):", res_30)
    assert res_30 is False, "Mock (30) MUST NOT be > 30!"

    # Case 7: Giả lập số 35 (hàng chục là 3, đơn vị là 5) -> phải là True
    mock_35 = img.copy()
    # Giữ nguyên số 5 của Recoome, chỉ thay số 4 thành số 3:
    mock_35[1150:1185, 135:168] = [10, 10, 10]
    mock_35[1153:1153+h3, 138:138+w3] = tpl_3
    res_35 = vision.is_input_greater_than_30(mock_35, r1)
    print("Test Mock 35 (hang chuc 3, don vi 5):", res_35)
    assert res_35 is True, "Mock (35) MUST be > 30!"

    print("ALL_GREATER_THAN_30_TESTS_PASSED_100_PERCENT")

if __name__ == "__main__":
    test_greater_than_30_cases()
