import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
import numpy as np
from src.core.config import BotConfig
from src.core.vision import VisionEngine

def test_production_vision():
    cfg = BotConfig(target_width=1080, target_height=1920)
    v = VisionEngine(cfg.templates)
    
    # 1. Ảnh live VIP9 (Row 1 Saiyan 3152, Row 2 Karin Stick 0)
    img_vip9 = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    
    r1 = cfg.vip9_initial_rows[0] # Saiyan 3152
    r2 = cfg.vip9_initial_rows[1] # Karin Stick 0
    
    assert not v.is_input_zero(img_vip9, r1), "Saiyan Soul 3152 KHÔNG được là Zero!"
    assert v.is_input_zero(img_vip9, r2), "Karin Stick (0) BẮT BUỘC phải là Zero!"
    
    # 2. Test giả lập số 10, 20, 30:
    # Lấy vùng số 0 của Karin Stick (r2):
    y1 = r2.y + r2.h // 2 - 100
    y2 = r2.y + r2.h // 2 + 120
    strip_sim = img_vip9[y1:y2, 120:220].copy()
    
    # Ghép thêm chữ số 2 bên trái số 0 (giả lập số 20):
    # Số 0 nằm ở x=36, y=143 trên strip_sim.
    # Đặt chữ số 2 ở x=15..32, y=143..165:
    strip_sim[145:167, 14:32] = [0, 220, 255] # Pixel vàng cam
    
    # Test hàm với strip_sim giả lập số 20
    # Ta nhét strip_sim vào một frame giả
    mock_frame = img_vip9.copy()
    mock_frame[y1:y2, 120:220] = strip_sim
    assert not v.is_input_zero(mock_frame, r2), "Số 20 giả lập KHÔNG ĐƯỢC coi là Zero!"
    
    print("ALL_TESTS_PASSED_100_PERCENT")

if __name__ == "__main__":
    test_production_vision()
