import cv2
import numpy as np

# Load ảnh live màn hình 1080x1920
img = cv2.imread("debug_crops/live_current_vip7.png")
h, w = img.shape[:2]

# Cắt vùng hiển thị số lượng của 3 dòng để so sánh:
# Dòng 1: Saiyan Soul -> 7342 (hoặc 45 ở Recoome trên ảnh live_current_vip7)
# Dòng 2: Saiyan Soul -> 0962
# Dòng 3: Ginyu -> 0

# Tọa độ vùng text số lượng input (ngay sau ngôi sao xanh):
# x: khoảng 130 -> 215
# Dòng 1: y: 1180 -> 1225
# Dòng 2: y: 1445 -> 1490
# Dòng 3: y: 1675 -> 1715

d1_qty = img[1180:1225, 130:215]
d2_qty = img[1445:1490, 130:215]
d3_qty = img[1675:1715, 130:215]

cv2.imwrite("debug_crops/qty_d1.png", d1_qty)
cv2.imwrite("debug_crops/qty_d2.png", d2_qty)
cv2.imwrite("debug_crops/qty_d3.png", d3_qty)

print("SAVED_QTY_CROPS")
