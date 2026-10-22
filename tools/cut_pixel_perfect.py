import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
live_img = cv2.imread(str(ROOT_DIR / "debug_crops" / "live_current_vip7.png"))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"
cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# 1. Số 0 chuẩn từng pixel:
# Trong wide_avatar_box (y bắt đầu từ 1660, x từ 120):
# Số 0 nằm ở y cục bộ: 22 -> 51 (tức y toàn cục: 1682 -> 1711)
# x cục bộ: 34 -> 66 (tức x toàn cục: 154 -> 186)
zero_target = live_img[1682:1712, 154:186]
cv2.imwrite(str(cuts_dir / "zero_target.png"), zero_target)
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_target)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_target)

# 2. Cụm chữ số 300000 chuẩn từng pixel:
# Trong wide_reward_box (y bắt đầu từ 1660, x từ 600):
# Chữ 300000 nằm ở y cục bộ: 21 -> 56 (tức y toàn cục: 1681 -> 1716)
# x bắt đầu từ số 3 (x toàn cục: 635) đến hết số 0 cuối (x toàn cục: 765)
text_300k_target = live_img[1681:1716, 635:765]
cv2.imwrite(str(cuts_dir / "text_300k_target.png"), text_300k_target)
cv2.imwrite(str(templates_dir / "coin_300000_text.png"), text_300k_target)
cv2.imwrite(str(images_dir / "coin_300000_text.png"), text_300k_target)

# 3. Cắt cả ô 300000 Coin(s) (gồm đống tiền vàng + 300000):
# y từ 1605 đến 1720, x từ 615 đến 770
coin_300k_full_target = live_img[1605:1720, 615:770]
cv2.imwrite(str(cuts_dir / "coin_300k_full_target.png"), coin_300k_full_target)
cv2.imwrite(str(templates_dir / "coin_300k.png"), coin_300k_full_target)
cv2.imwrite(str(images_dir / "coin_300k.png"), coin_300k_full_target)

print("Pixel-perfect crops saved!")
