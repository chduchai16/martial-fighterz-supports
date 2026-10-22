import cv2

img_sample = cv2.imread("assets/samples/fourth_step.png")
# Liuli ở Dòng 1 trên 562x1005: x khoảng 60-120, y khoảng 650-690
crop_liuli_real = img_sample[650:695, 65:125]
cv2.imwrite("debug_crops/qty_liuli_real.png", crop_liuli_real)

print("LIULI_REAL_CROPPED")
