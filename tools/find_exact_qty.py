import cv2

img = cv2.imread("debug_crops/live_current_vip7.png")
# Tọa độ Avatar Recoome ở Dòng 1: y từ 570 đến 615 trên ảnh 567x1014 -> trên 1080x1920: y: 1100 -> 1220
# Ngôi sao và số lượng nằm ở đáy avatar:
# x: 120 -> 220
# Dòng 1 (Recoome 45): y khoảng 1150 -> 1185
d1_star_qty = img[1145:1185, 120:220]
cv2.imwrite("debug_crops/qty_d1_exact.png", d1_star_qty)

# Dòng 2 (Saiyan Soul 0962):
d2_star_qty = img[1410:1450, 120:220]
cv2.imwrite("debug_crops/qty_d2_exact.png", d2_star_qty)

# Dòng 3 (Ginyu 0):
d3_star_qty = img[1675:1715, 120:220]
cv2.imwrite("debug_crops/qty_d3_exact.png", d3_star_qty)

print("EXACT_QTY_SAVED")
