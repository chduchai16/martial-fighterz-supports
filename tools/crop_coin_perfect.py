import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ trọn vẹn số 300000: x: 627 -> 830 (w = 203)
coin_full_box = img[1600:1725, 627:830]
cv2.imwrite("assets/templates/coin_300k.png", coin_full_box)
cv2.imwrite("images/coin_300k.png", coin_full_box)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_full_box)

print("COIN_PERFECT_FULL_DONE:", coin_full_box.shape)
