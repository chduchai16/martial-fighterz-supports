import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

out_dir = ROOT_DIR / "debug_crops" / "cuts"
out_dir.mkdir(parents=True, exist_ok=True)

# Cắt nguyên toàn bộ Line 3 (Ginyu): y từ 1600 đến 1880, full chiều rộng
line3_full = img[1600:1880, 0:1080]
cv2.imwrite(str(out_dir / "line3_full.png"), line3_full)

# Cắt ô Avatar Ginyu bên trái:
avatar_area = img[1610:1730, 80:230]
cv2.imwrite(str(out_dir / "line3_avatar.png"), avatar_area)

# Cắt ô thưởng Coins bên phải:
reward_area = img[1610:1740, 610:770]
cv2.imwrite(str(out_dir / "line3_reward.png"), reward_area)

print("Saved line3_full, line3_avatar, line3_reward")
