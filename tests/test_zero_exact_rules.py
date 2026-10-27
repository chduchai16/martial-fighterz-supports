import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2
from src.core.config import BotConfig, Rect
from src.core.vision import VisionEngine

def test_production():
    cfg = BotConfig(target_width=1080, target_height=1920)
    v = VisionEngine(cfg.templates)
    
    # Load ảnh live VIP7 (trong đó Dòng 3 Ginyu có số 0 ở x=156, y=1679, cy_reward ≈ 1662)
    img = cv2.imread(str(ROOT / "debug_crops" / "live_current_vip7.png"))
    
    # Dòng 3 (Ginyu 0) -> Bắt buộc True
    r3 = Rect(630, 1636, 230, 250)
    assert v.is_input_zero(img, r3), "Ginyu (0) MUST be Zero!"
    
    # Dòng 1 (Recoome 45) -> Bắt buộc False
    r1 = cfg.vip7_initial_rows[0]
    assert not v.is_input_zero(img, r1), "Recoome 45 MUST NOT be Zero!"
    
    # Giả lập số 20 trên Ginyu:
    # Số 0 của Ginyu ở y=1679, x=156
    # Vẽ chữ số 2 bên trái số 0 (x: 130..152, y: 1679..1711)
    mock_20 = img.copy()
    mock_20[1679:1711, 130:152] = [0, 220, 255]
    assert not v.is_input_zero(mock_20, r3), "Number 20 MUST NOT be Zero!"
    
    # Giả lập số 10 trên Ginyu:
    mock_10 = img.copy()
    mock_10[1679:1711, 140:150] = [0, 220, 255]
    assert not v.is_input_zero(mock_10, r3), "Number 10 MUST NOT be Zero!"
    
    # Giả lập số 30 trên Ginyu:
    mock_30 = img.copy()
    mock_30[1679:1711, 130:152] = [0, 220, 255]
    assert not v.is_input_zero(mock_30, r3), "Number 30 MUST NOT be Zero!"
    
    print("ALL_UNIT_TESTS_PASSED_100_PERCENT")

if __name__ == "__main__":
    test_production()
