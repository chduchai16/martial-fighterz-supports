import cv2
import numpy as np

# Load ảnh số 45 (Recoome), 31 (Videl) và số 0 (Ginyu)
img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
img_0 = cv2.imread("debug_crops/qty_d3_exact.png")

t_zero = cv2.imread("assets/templates/input_zero.png")

# Kiểm tra template matching số 0:
res_0 = cv2.minMaxLoc(cv2.matchTemplate(img_0, t_zero, cv2.TM_CCOEFF_NORMED))[1]
res_45 = cv2.minMaxLoc(cv2.matchTemplate(img_45, t_zero, cv2.TM_CCOEFF_NORMED))[1]

print("Match Zero on 0: ", res_0)
print("Match Zero on 45:", res_45)
