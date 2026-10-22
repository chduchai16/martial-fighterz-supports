from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

out_dir = ROOT_DIR / "debug_crops"

# Cat line 3 chuan tu anh chua cuon
# y tu 1580 den 1780 (vua khit khung Line 3, khong bi lem xuong duoi)
line3_clean = img[1580:1780, 0:1080]
cv2.imwrite(str(out_dir / "line3_clean.png"), line3_clean)

# Avatar Ginyu
ginyu_box = img[1590:1735, 70:240]
cv2.imwrite(str(out_dir / "ginyu_box.png"), ginyu_box)

# So 0 chuan canh sao xanh
# Canh toa do: x tu 130 den 175, y tu 1665 den 1715
zero_clean = img[1665:1715, 130:175]
cv2.imwrite(str(out_dir / "zero_clean.png"), zero_clean)

# O thuong Min Earning (Dong tien vang + chu 300000)
coin_300k_box = img[1595:1735, 610:775]
cv2.imwrite(str(out_dir / "coin_300k_box.png"), coin_300k_box)

print("CROP_CLEAN_DONE")
