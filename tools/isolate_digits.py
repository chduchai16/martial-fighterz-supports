import cv2
import numpy as np

# Load ảnh số 4 Liuli và ảnh số 45 Recoome
img_4_orig = cv2.imread("debug_crops/qty_liuli_real.png")
# Cắt đúng chữ số 4 (không dính mặt Liuli)
# Liuli trên ảnh gốc 562: số 4 nằm ở đáy góc dưới bên trái
crop_digit_4 = img_4_orig[10:45, 10:40]
cv2.imwrite("debug_crops/digit_4_isolated.png", crop_digit_4)

# Cắt chữ số 4 và 5 của Recoome (45):
img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
# img_45 có kích thước (40, 100):
# Số 4 nằm bên trái: x: 20 -> 50
# Số 5 nằm bên phải: x: 50 -> 80
digit_4_from_45 = img_45[5:38, 20:52]
digit_5_from_45 = img_45[5:38, 50:80]

cv2.imwrite("debug_crops/digit_4_rec.png", digit_4_from_45)
cv2.imwrite("debug_crops/digit_5_rec.png", digit_5_from_45)

print("DIGITS_SAVED")
