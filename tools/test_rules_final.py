import cv2
import numpy as np

# Load ảnh số 45 (Recoome), 31 (Videl) và số 0 (Ginyu)
img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
img_0 = cv2.imread("debug_crops/qty_d3_exact.png")

t_zero = cv2.imread("assets/templates/input_zero.png")

def is_input_zero(qty_crop):
    """Nếu khớp số 0 với conf > 0.85 -> Input = 0"""
    res = cv2.matchTemplate(qty_crop, t_zero, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    return max_val >= 0.85

def has_large_quantity(qty_crop):
    """
    Kiểm tra số lượng input:
    1. Không phải là số 0.
    2. Chiều rộng cụm pixel chữ số màu vàng (HSV) >= 70px -> Bắt buộc có từ 2-4 chữ số (>= 10, 31, 45, 962).
       Số 0 chỉ rộng ~24px. Các số 1 chữ số chỉ rộng 20-30px.
    """
    if is_input_zero(qty_crop):
        return False
        
    lower_yellow = np.array([10, 140, 160], dtype=np.uint8)
    upper_yellow = np.array([35, 255, 255], dtype=np.uint8)
    mask = cv2.inRange(cv2.cvtColor(qty_crop, cv2.COLOR_BGR2HSV), lower_yellow, upper_yellow)
    
    pts = cv2.findNonZero(mask)
    if pts is None:
        return False
    x, y, w, h = cv2.boundingRect(pts)
    
    # 2 chữ số trở lên có bề rộng bounding box >= 45px (số 45 rộng 84px, số 31 rộng 75px)
    return w >= 45

print("Rule on Num 0:  is_zero =", is_input_zero(img_0), "| is_large (>30) =", has_large_quantity(img_0))
print("Rule on Num 45: is_zero =", is_input_zero(img_45), "| is_large (>30) =", has_large_quantity(img_45))
