import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
templates_dir.mkdir(parents=True, exist_ok=True)
images_dir.mkdir(parents=True, exist_ok=True)

# 1. Cắt số 0 của dòng Ginyu:
# Avatar Ginyu ở dòng 3: y khoảng 1630-1710, x khoảng 125-175
# Tìm chính xác số 0 cạnh ngôi sao xanh
crop_zero = img[1665:1705, 130:175]
cv2.imwrite(str(templates_dir / "input_zero.png"), crop_zero)
cv2.imwrite(str(images_dir / "input_zero.png"), crop_zero)

# 2. Cắt cụm 300000 Coin(s) ở ô Min Earning dòng 3:
# Ô thưởng dòng 3: y khoảng 1635-1725, x khoảng 630-760
crop_coin_300k = img[1635:1725, 630:765]
cv2.imwrite(str(templates_dir / "coin_300k.png"), crop_coin_300k)
cv2.imwrite(str(images_dir / "coin_300k.png"), crop_coin_300k)

# 3. Cắt thêm bản zoom cận cảnh tiền vàng + chữ 300000 để kiểm tra
crop_coin_text = img[1670:1715, 630:760]
cv2.imwrite(str(templates_dir / "coin_300000_text.png"), crop_coin_text)
cv2.imwrite(str(images_dir / "coin_300000_text.png"), crop_coin_text)

print("Đã cắt xong:")
print("- input_zero.png:", crop_zero.shape)
print("- coin_300k.png:", crop_coin_300k.shape)
print("- coin_300000_text.png:", crop_coin_text.shape)
