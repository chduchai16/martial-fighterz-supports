import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ chính xác ô phần thưởng Dòng 3 (Min Earning)
# Ô nằm x: 610 -> 830, y: 1590 -> 1730
# Cắt trọn vẹn icon đống tiền vàng + toàn bộ số 300000:
coin_full = img[1590:1725, 610:830]
cv2.imwrite("assets/templates/coin_300k.png", coin_full)
cv2.imwrite("images/coin_300k.png", coin_full)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_full)

# Cắt riêng cụm text 300000 trọn vẹn:
text_300k = img[1670:1725, 612:825]
cv2.imwrite("assets/templates/text_300000.png", text_300k)
cv2.imwrite("images/text_300000.png", text_300k)
cv2.imwrite("debug_crops/text_300000_preview.png", text_300k)

# Số 0 gọn gàng sạch viền:
zero = img[1679:1711, 156:179]
cv2.imwrite("assets/templates/input_zero.png", zero)
cv2.imwrite("images/input_zero.png", zero)
cv2.imwrite("debug_crops/input_zero_preview.png", zero)

print("RECROP_DONE")
