import cv2
import numpy as np

# Load ảnh số 45 và số 0
img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
img_0 = cv2.imread("debug_crops/qty_d3_exact.png")

# Template số 0
t_zero = cv2.imread("assets/templates/input_zero.png")

res_on_0 = cv2.minMaxLoc(cv2.matchTemplate(img_0, t_zero, cv2.TM_CCOEFF_NORMED))
res_on_45 = cv2.minMaxLoc(cv2.matchTemplate(img_45, t_zero, cv2.TM_CCOEFF_NORMED))

print(f"Match template input_zero on Num 0: conf = {res_on_0[1]:.4f}")
print(f"Match template input_zero on Num 45: conf = {res_on_45[1]:.4f}")
