import cv2
import numpy as np

# Load ảnh số 45 và ảnh số 0
img_45 = cv2.imread("debug_crops/qty_d1_exact.png")
img_0 = cv2.imread("debug_crops/qty_d3_exact.png")

lower_yellow = np.array([10, 140, 160], dtype=np.uint8)
upper_yellow = np.array([35, 255, 255], dtype=np.uint8)

# Phân tích contours chữ số
def get_digit_count(img):
    mask = cv2.inRange(cv2.cvtColor(img, cv2.COLOR_BGR2HSV), lower_yellow, upper_yellow)
    # Lọc nhiễu nhẹ
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    mask_clean = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    
    contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid_digits = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if h >= 18 and w >= 8: # Tiêu chuẩn của 1 chữ số
            valid_digits.append((x, y, w, h))
            
    valid_digits.sort(key=lambda b: b[0])
    return len(valid_digits), valid_digits

print("Digit count for 45:", get_digit_count(img_45))
print("Digit count for 0: ", get_digit_count(img_0))
