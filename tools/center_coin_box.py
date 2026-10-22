import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Khung ô Min Earning thực tế nằm x: 620 -> 770 (w = 150)
# Cắt ôm trọn vẹn 4 cạnh ô vuông màu vàng:
coin_centered_box = img[1598:1725, 620:770]
cv2.imwrite("assets/templates/coin_300k.png", coin_centered_box)
cv2.imwrite("images/coin_300k.png", coin_centered_box)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_centered_box)

print("COIN_CENTERED_BOX_DONE:", coin_centered_box.shape)
