import cv2
import numpy as np

img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
img_0 = cv2.imread("debug_crops/qty_d3_exact.png")

lower_yellow = np.array([10, 140, 160], dtype=np.uint8)
upper_yellow = np.array([35, 255, 255], dtype=np.uint8)

mask_45 = cv2.inRange(cv2.cvtColor(img_45, cv2.COLOR_BGR2HSV), lower_yellow, upper_yellow)
mask_0 = cv2.inRange(cv2.cvtColor(img_0, cv2.COLOR_BGR2HSV), lower_yellow, upper_yellow)

pts_45 = cv2.findNonZero(mask_45)
x45, y45, w45, h45 = cv2.boundingRect(pts_45) if pts_45 is not None else (0,0,0,0)

pts_0 = cv2.findNonZero(mask_0)
x0, y0, w0, h0 = cv2.boundingRect(pts_0) if pts_0 is not None else (0,0,0,0)

print(f"Num 45: width = {w45}px, height = {h45}px, nonzeros = {np.count_nonzero(mask_45)}")
print(f"Num 0:  width = {w0}px, height = {h0}px, nonzeros = {np.count_nonzero(mask_0)}")
