import cv2
import numpy as np

# Scale ảnh Liuli lên chuẩn 1080x1920 (nhân hệ số 1080/562 = 1.9217)
scale = 1080.0 / 562.0
img_4_orig = cv2.imread("debug_crops/qty_liuli_real.png")
img_4 = cv2.resize(img_4_orig, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_LINEAR)

img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
img_0 = cv2.imread("debug_crops/qty_d3_exact.png")

lower_yellow = np.array([10, 140, 160], dtype=np.uint8)
upper_yellow = np.array([35, 255, 255], dtype=np.uint8)

def get_stats(img):
    mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), lower_yellow, upper_yellow)
    pts = cv2.findNonZero(mask)
    if pts is None: return 0, 0, 0
    x, y, w, h = cv2.boundingRect(pts)
    return w, h, np.count_nonzero(mask)

w4, h4, c4 = get_stats(img_4)
w45, h45, c45 = get_stats(img_45)
w0, h0, c0 = get_stats(img_0)

print(f"So 4  (1 chu so): width = {w4}px, nonzeros = {c4}")
print(f"So 0  (1 chu so): width = {w0}px, nonzeros = {c0}")
print(f"So 45 (2 chu so): width = {w45}px, nonzeros = {c45}")
