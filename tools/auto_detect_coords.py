import cv2
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
line_p = ROOT_DIR / "debug_crops" / "cuts" / "line3_full.png"
line_img = cv2.imread(str(line_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# 1. Tìm chính xác số 0 qua contour màu vàng viền đen:
# Số 0 nằm ở x từ 145 đến 185, y từ 65 đến 110
# Hãy crop rộng vùng số 0 một chút để xem tọa độ thực:
test_zero_box = line_img[65:110, 145:185]
cv2.imwrite(str(cuts_dir / "test_zero_box.png"), test_zero_box)

# Dịch sang phải để lấy trọn số 0: x: 152 -> 180, y: 72 -> 104
crop_zero_exact = line_img[72:104, 150:180]
cv2.imwrite(str(cuts_dir / "crop_digit_zero_exact.png"), crop_zero_exact)
cv2.imwrite(str(templates_dir / "input_zero.png"), crop_zero_exact)
cv2.imwrite(str(images_dir / "input_zero.png"), crop_zero_exact)

# 2. Cắt chữ 300000 trọn vẹn từ số 3 đến hết số 0 cuối cùng:
# Trong line3_full, ô thưởng bên phải x: 615 -> 770
# Chữ số 300000 nằm ở x: 620 -> 765, y: 80 -> 122
crop_300k_exact = line_img[80:122, 620:765]
cv2.imwrite(str(cuts_dir / "crop_300k_exact.png"), crop_300k_exact)
cv2.imwrite(str(templates_dir / "coin_300000_text.png"), crop_300k_exact)
cv2.imwrite(str(images_dir / "coin_300000_text.png"), crop_300k_exact)

print("Exact cuts saved!")
