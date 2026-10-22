import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
line_p = ROOT_DIR / "debug_crops" / "cuts" / "line3_full.png"
line_img = cv2.imread(str(line_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# 1. Số 0 chuẩn:
# Dịch xuống một tí để số 0 nằm chính giữa: y: 73 -> 103, x: 154 -> 176
zero_perfect = line_img[73:103, 154:176]
cv2.imwrite(str(cuts_dir / "zero_perfect.png"), zero_perfect)
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_perfect)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_perfect)

# 2. Cắt trọn vẹn số 300000:
# Nhìn vào test_300k_area: số 300000 bắt đầu từ x: 635 đến 762, y: 72 đến 104
# (ở 615-635 là viền khung bên trái, số 3 bắt đầu từ 635)
text_300k_perfect = line_img[72:104, 634:764]
cv2.imwrite(str(cuts_dir / "text_300k_perfect.png"), text_300k_perfect)
cv2.imwrite(str(templates_dir / "coin_300000_text.png"), text_300k_perfect)
cv2.imwrite(str(images_dir / "coin_300000_text.png"), text_300k_perfect)

# 3. Cắt cả cụm Đống tiền vàng + 300000:
# x: 625 -> 770, y: 0 -> 106
coin_reward_perfect = line_img[0:106, 625:770]
cv2.imwrite(str(cuts_dir / "coin_reward_perfect.png"), coin_reward_perfect)
cv2.imwrite(str(templates_dir / "coin_300k.png"), coin_reward_perfect)
cv2.imwrite(str(images_dir / "coin_300k.png"), coin_reward_perfect)

print("All perfect templates saved!")
