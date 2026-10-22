import cv2
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
line_p = ROOT_DIR / "debug_crops" / "cuts" / "line3_full.png"
line_img = cv2.imread(str(line_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# 1. Cắt số 0 chính giữa hoàn hảo:
# Trong test_zero_box, số 0 nằm từ y: 72 đến 104, x: 154 đến 176 (rộng 22, cao 32)
# Cắt chính xác:
zero_clean = line_img[72:103, 155:177]
cv2.imwrite(str(cuts_dir / "zero_clean.png"), zero_clean)
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_clean)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_clean)

# 2. Cắt chữ 300000 đầy đủ:
# Trong line3_full, ô thưởng x từ 615 đến 770
# Hãy crop từ x: 615 đến 760, y: 55 đến 110 để xem số 300000 nằm từ đâu đến đâu
test_300k = line_img[55:110, 615:760]
cv2.imwrite(str(cuts_dir / "test_300k_area.png"), test_300k)

print("Saved zero_clean and test_300k_area")
