import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ cũ: x: 610 -> 830, w = 220
# Dịch sang phải 20% của chiều rộng (220 * 0.20 = 44px):
# Toạ độ mới: x: 654 -> 874, y: 1590 -> 1725
coin_shifted = img[1590:1725, 654:874]

cv2.imwrite("assets/templates/coin_300k.png", coin_shifted)
cv2.imwrite("images/coin_300k.png", coin_shifted)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_shifted)

# Cắt riêng cụm text 300000 dịch sang phải tương ứng
text_shifted = img[1670:1725, 654:874]
cv2.imwrite("assets/templates/text_300000.png", text_shifted)
cv2.imwrite("images/text_300000.png", text_shifted)

print("COIN_SHIFTED_DONE")
