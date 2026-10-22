import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
line_p = ROOT_DIR / "debug_crops" / "cuts" / "line3_full.png"
line_img = cv2.imread(str(line_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# 1. Căn lại số 0 chính xác (tránh bị lệch sang phải):
# Dịch sang phải và xuống dưới một chút để ôm trọn số 0:
# x: từ 144 đến 176 (rộng 32px), y: từ 70 đến 106 (cao 36px)
crop_zero = line_img[70:106, 144:176]
cv2.imwrite(str(cuts_dir / "crop_digit_zero.png"), crop_zero)
cv2.imwrite(str(templates_dir / "input_zero.png"), crop_zero)
cv2.imwrite(str(images_dir / "input_zero.png"), crop_zero)

# 2. Căn lại chữ số 300000 đầy đủ:
# x: từ 620 đến 762 (rộng 142px), y: từ 66 đến 116 (cao 50px)
crop_300000 = line_img[66:116, 620:762]
cv2.imwrite(str(cuts_dir / "crop_text_300000.png"), crop_300000)
cv2.imwrite(str(templates_dir / "coin_300000_text.png"), crop_300000)
cv2.imwrite(str(images_dir / "coin_300000_text.png"), crop_300000)

print("Re-cropped perfectly!")
