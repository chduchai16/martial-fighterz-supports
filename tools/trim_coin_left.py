import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ trước: x: 627 -> 830 (w = 203)
# Cắt bớt bên trái 10% chiều rộng (khoảng 20px): x bắt đầu từ 647 -> 830 (w = 183)
coin_trimmed_left = img[1600:1725, 647:830]
cv2.imwrite("assets/templates/coin_300k.png", coin_trimmed_left)
cv2.imwrite("images/coin_300k.png", coin_trimmed_left)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_trimmed_left)

print("COIN_TRIMMED_LEFT_DONE:", coin_trimmed_left.shape)
