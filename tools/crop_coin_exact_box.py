import cv2
from pathlib import Path

img_p = Path("debug_crops/live_current_vip7.png")
img = cv2.imread(str(img_p))

# Toạ độ thực sự của ô Min Earning Dòng 3 trên 1080x1920:
# Viền trái của ô bắt đầu từ x = 627, viền phải kết thúc tại x = 765
# Cắt chính xác tâm ô:
coin_final = img[1600:1725, 627:765]
cv2.imwrite("assets/templates/coin_300k.png", coin_final)
cv2.imwrite("images/coin_300k.png", coin_final)
cv2.imwrite("debug_crops/coin_300k_full_preview.png", coin_final)

print("COIN_FINAL_DONE:", coin_final.shape)
