"""
Script chẩn đoán nhanh: Chụp 1 frame thật từ MuMu Player, lưu vào debug_dumps/current_screen.png,
và quét thử tất cả các mức scale để tìm độ khớp tối ưu.
"""
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from capture import FastCapture
from config import DEBUG_DIR, IMAGES_DIR

print("\n--- Đang chụp màn hình thực tế từ MuMu Player qua ADB ---")
cap = FastCapture()
cap.start()
frame = cap.get_latest_frame(timeout=3.0)
cap.stop()

if frame is None:
    print("❌ Không chụp được frame từ thiết bị! Hãy kiểm tra lại kết nối ADB.")
    sys.exit(1)

f_h, f_w = frame.shape[:2]
save_path = DEBUG_DIR / "current_screen.png"
cv2.imwrite(str(save_path), frame)
print(f"✅ Đã chụp thành công: Kích thước {f_w}x{f_h} -> Lưu tại: {save_path}")

# Thử template matching với các file template trong images/
templates = [
    ("kim_cuong_icon", IMAGES_DIR / "kim_cuong_icon.png"),
    ("kim_cuong_inner", IMAGES_DIR / "kim_cuong_inner.png"),
    ("odd_button", IMAGES_DIR / "odd_button.png"),
    ("even_button", IMAGES_DIR / "even_button.png"),
]

print("\n--- Kết quả quét độ khớp trên toàn màn hình với các mức scale: ---")
for t_name, t_path in templates:
    if not t_path.exists():
        continue
    tpl = cv2.imread(str(t_path))
    if tpl is None:
        continue
    
    t_h, t_w = tpl.shape[:2]
    best_score = -1.0
    best_scale = 1.0
    best_loc = (0, 0)

    # Quét dải scale từ 0.5 đến 2.5
    for s in np.linspace(0.8, 2.3, 31):
        nw, nh = int(t_w * s), int(t_h * s)
        if nw >= f_w or nh >= f_h or nw < 10 or nh < 10:
            continue
        resized_tpl = cv2.resize(tpl, (nw, nh))
        res = cv2.matchTemplate(frame, resized_tpl, cv2.TM_CCOEFF_NORMED)
        min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)
        if max_v > best_score:
            best_score = max_v
            best_scale = s
            best_loc = max_l

    status = "✅ TỐT (>0.75)" if best_score >= 0.75 else ("⚠️ TẠM ĐƯỢC (>0.6)" if best_score >= 0.6 else "❌ THẤP (<0.6)")
    print(f" - [{t_name}]: Score cao nhất = {best_score:.3f} tại scale = {best_scale:.2f} (Toạ độ: {best_loc}) -> {status}")
