import sys
from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

out_dir = ROOT_DIR / "debug_crops"
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Cat toan bo Line 3 (Ginyu -> 300000 Coin(s))
# Line 3 bat dau tu khoang y=1620 den y=1880
line3_full = img[1615:1880, 0:1080]
cv2.imwrite(str(out_dir / "line3_full.png"), line3_full)

# 2. Cat avatar Ginyu kem so 0
ginyu_avatar = img[1630:1750, 75:235]
cv2.imwrite(str(out_dir / "line3_ginyu_avatar.png"), ginyu_avatar)

# 3. Cat rieng so 0 canh ngoi sao
zero_only = img[1665:1715, 130:175]
cv2.imwrite(str(out_dir / "line3_zero_candidate.png"), zero_only)

# 4. Cat o thuong 1 (Min Earning: 300000 Coin(s))
coin_slot1 = img[1630:1755, 620:775]
cv2.imwrite(str(out_dir / "line3_coin_slot1.png"), coin_slot1)

# 5. Cat chu 300000 kem dong tien vang
coin_300k_exact = img[1650:1725, 630:765]
cv2.imwrite(str(out_dir / "line3_coin_300k_exact.png"), coin_300k_exact)

print("CROP_DONE")
