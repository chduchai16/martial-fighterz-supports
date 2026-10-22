import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ trước: x: 654 -> 874 (w = 220). Bị thừa bên phải (lấn sang nền đen/dòng khác).
# Thu gọn bên phải lại: chỉ lấy x: 630 -> 820 (w = 190), y: 1595 -> 1725
# Cắt vừa khít khung gỗ vàng của ô Min Earning:
coin_trimmed = img[1595:1725, 630:820]
cv2.imwrite("assets/templates/coin_300k.png", coin_trimmed)
cv2.imwrite("images/coin_300k.png", coin_trimmed)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_trimmed)

# Cắt riêng cụm text 300000 vừa khít:
text_trimmed = img[1670:1722, 630:810]
cv2.imwrite("assets/templates/text_300000.png", text_trimmed)
cv2.imwrite("images/text_300000.png", text_trimmed)

print("TRIMMED_DONE:", coin_trimmed.shape, text_trimmed.shape)
