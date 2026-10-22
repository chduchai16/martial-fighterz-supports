import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
line_p = ROOT_DIR / "debug_crops" / "cuts" / "line3_full.png"
line_img = cv2.imread(str(line_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# 1. Cắt chính xác số 0 (ngay cạnh ngôi sao 4 của Ginyu):
# Trong line3_full.png:
# Ngôi sao xanh x: 62-118, y: 55-115
# Số 0 vàng viền đen: x từ 140 đến 175, y từ 70 đến 105
crop_zero = line_img[68:105, 140:175]
cv2.imwrite(str(cuts_dir / "crop_digit_zero.png"), crop_zero)
cv2.imwrite(str(templates_dir / "input_zero.png"), crop_zero)
cv2.imwrite(str(images_dir / "input_zero.png"), crop_zero)

# 2. Cắt chính xác chữ số "300000" màu vàng viền đen:
# Số 300000 ở ô Min Earning: x từ 618 đến 758, y từ 84 đến 122
crop_300000 = line_img[84:122, 618:758]
cv2.imwrite(str(cuts_dir / "crop_text_300000.png"), crop_300000)
cv2.imwrite(str(templates_dir / "coin_300000_text.png"), crop_300000)
cv2.imwrite(str(images_dir / "coin_300000_text.png"), crop_300000)

# 3. Cắt nguyên cả ô thưởng 300000 Coin(s) gồm cả đống tiền vàng và chữ 300000:
# x từ 615 đến 762, y từ 0 đến 125
crop_coin_full = line_img[0:125, 615:762]
cv2.imwrite(str(cuts_dir / "crop_coin_300k_full.png"), crop_coin_full)
cv2.imwrite(str(templates_dir / "coin_300k.png"), crop_coin_full)
cv2.imwrite(str(images_dir / "coin_300k.png"), crop_coin_full)

print("Extraction completed!")
