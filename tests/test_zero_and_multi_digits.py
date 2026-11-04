import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from src.core.config import BotConfig, Rect
from src.core.vision import VisionEngine

def test_production_vision():
    cfg = BotConfig(target_width=1080, target_height=1920)
    v = VisionEngine(cfg.templates)
    
    # 1. Ảnh live VIP7: Row 1 Recoome (45), Row 2 Saiyan (0962), Row 3 Ginyu (0)
    img = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    
    r1 = cfg.vip7_initial_rows[0]  # Recoome 45
    r2 = cfg.vip7_initial_rows[1]  # Saiyan 0962
    r3 = Rect(630, 1636, 230, 250) # Ginyu 0
    
    assert not v.is_input_zero(img, r1), "Recoome 45 KHÔNG được là Zero!"
    assert not v.is_input_zero(img, r2), "Saiyan 0962 KHÔNG được là Zero!"
    assert v.is_input_zero(img, r3), "Ginyu (0) BẮT BUỘC phải là Zero!"
    
    # 2. Test giả lập số 10, 20, 30:
    # Lấy vùng số 0 của Ginyu (r3):
    y1 = r3.y + r3.h // 2 - 100
    y2 = r3.y + r3.h // 2 + 120
    strip_sim = img[y1:y2, 120:220].copy()
    
    # Ghép thêm chữ số 2 bên trái số 0 (giả lập số 20):
    strip_sim[1679-y1:1711-y1, 130-120:152-120] = [0, 220, 255] # Pixel vàng cam
    
    mock_frame = img.copy()
    mock_frame[y1:y2, 120:220] = strip_sim
    assert not v.is_input_zero(mock_frame, r3), "Số 20 giả lập KHÔNG ĐƯỢC coi là Zero!"
    
    print("ALL_TESTS_PASSED_100_PERCENT")

if __name__ == "__main__":
    test_production_vision()
