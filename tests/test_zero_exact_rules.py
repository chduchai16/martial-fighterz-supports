import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from src.core.config import BotConfig
from src.core.vision import VisionEngine

def test_production():
    cfg = BotConfig(target_width=1080, target_height=1920)
    v = VisionEngine(cfg.templates)
    
    # Load ảnh live VIP9
    img = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    
    # 1. Dòng 2 (Karin's Stick = 0) -> Bắt buộc True
    r2 = cfg.vip9_initial_rows[1]
    assert v.is_input_zero(img, r2), "Karin's Stick (0) MUST be Zero!"
    
    # 2. Dòng 1 (Saiyan Soul 3152) -> Bắt buộc False
    r1 = cfg.vip9_initial_rows[0]
    assert not v.is_input_zero(img, r1), "Saiyan Soul 3152 MUST NOT be Zero!"
    
    # 3. Giả lập số 10, 20, 30 trên Karin's Stick -> Bắt buộc False
    mock_20 = img.copy()
    mock_20[1539:1571, 130:152] = [0, 220, 255] # Chữ số 2
    assert not v.is_input_zero(mock_20, r2), "Number 20 MUST NOT be Zero!"
    
    mock_10 = img.copy()
    mock_10[1539:1571, 140:150] = [0, 220, 255] # Chữ số 1
    assert not v.is_input_zero(mock_10, r2), "Number 10 MUST NOT be Zero!"
    
    mock_30 = img.copy()
    mock_30[1539:1571, 130:152] = [0, 220, 255] # Chữ số 3
    assert not v.is_input_zero(mock_30, r2), "Number 30 MUST NOT be Zero!"
    
    print("ALL_UNIT_TESTS_PASSED_100_PERCENT")

if __name__ == "__main__":
    test_production()
