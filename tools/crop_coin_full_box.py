import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ trọn vẹn cả ô phần thưởng: x: 627 -> 810 (w = 183)
# Bao gồm cả số 300000 đầy đủ từ số 3 đến số 0 cuối cùng:
coin_full_box = img[1600:1725, 627:810]
cv2.imwrite("assets/templates/coin_300k.png", coin_full_box)
cv2.imwrite("images/coin_300k.png", coin_full_box)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_full_box)

print("COIN_FULL_BOX_DONE:", coin_full_box.shape)
