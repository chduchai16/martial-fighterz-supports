import cv2
import numpy as np

# Load các ảnh số lượng mẫu hiện có:
# 1. Số 45 (2 chữ số > 30): debug_crops/qty_d1_exact.png
# 2. Số 0962 (4 chữ số): debug_crops/qty_d2_exact.png
# 3. Số 0: debug_crops/qty_d3_exact.png
# 4. Số 4 (1 chữ số ở Liuli trên fourth_step.png)
img_sample = cv2.imread("assets/samples/fourth_step.png")
# Liuli ở Dòng 1 trên 562x1005: x khoảng 120-170, y khoảng 650-680
# Hãy crop số 4 của Liuli
crop_liuli_4 = img_sample[650:690, 120:170]
cv2.imwrite("debug_crops/qty_liuli_4.png", crop_liuli_4)

print("LIULI_CROPPED")
