"""
Script debug: Doc anh live_debug.png, resize ve 1080x1920,
cat tung dong theo toa do config, ve khung annotated, tinh matching score.
"""
import sys
from pathlib import Path
import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import config, IMAGES_DIR

# 1. Doc anh live da chup
SRC = ROOT_DIR / "sample_images" / "live_debug.png"
OUT_DIR = ROOT_DIR / "sample_images"

frame_raw = cv2.imread(str(SRC))
if frame_raw is None:
    print("[ERR] Khong doc duoc " + str(SRC))
    sys.exit(1)

f_h, f_w = frame_raw.shape[:2]
print("[OK] Anh goc: {}x{}".format(f_w, f_h))

# Resize ve dung target 1080x1920
frame = cv2.resize(frame_raw, (config.target_width, config.target_height))
print("     Sau resize: {}x{}".format(config.target_width, config.target_height))

# 2. Dinh nghia templates can test
TEMPLATES = {
    "kim_cuong_inner":          IMAGES_DIR / "kim_cuong_inner.png",
    "kim_cuong_icon":           IMAGES_DIR / "kim_cuong_icon.png",
    "diamond_crystal_clean_en": IMAGES_DIR / "diamond_crystal_clean_en.png",
    "phuc_tung_c_inner":        IMAGES_DIR / "phuc_tung_c_inner.png",
}

def best_match(roi, templates):
    best_name, best_score = "none", 0.0
    details = {}
    for name, path in templates.items():
        tmpl = cv2.imread(str(path))
        if tmpl is None:
            details[name] = 0.0
            continue
        th, tw = tmpl.shape[:2]
        rh, rw = roi.shape[:2]
        if tw > rw or th > rh:
            details[name] = 0.0
            continue
        res = cv2.matchTemplate(roi, tmpl, cv2.TM_CCOEFF_NORMED)
        _, val, _, _ = cv2.minMaxLoc(res)
        details[name] = float(val)
        if val > best_score:
            best_score = val
            best_name = name
    return best_name, best_score, details

# 3. Cac dong can kiem tra
rows_info = (
    [("VIP9 Dong {}".format(i+1), r) for i, r in enumerate(config.vip9_initial_rows)] +
    [("VIP9 Dong 4 (cuon)", r) for r in config.vip9_scrolled_rows] +
    [("VIP7 Dong {}".format(i+1), r) for i, r in enumerate(config.vip7_rows)]
)

# 4. Annotate + crop tung dong
annotated = frame.copy()
PALETTE = [(0,230,0), (255,165,0), (0,120,255), (200,0,200)]

print("\n" + "="*85)
print("{:<22} {:<30} {:<28} {}".format("Label", "ROI(x,y,w,h)", "BestTemplate", "Score"))
print("="*85)

for idx, (label, row) in enumerate(rows_info):
    x1 = max(0, row.x);  x2 = min(frame.shape[1], row.x2)
    y1 = max(0, row.y);  y2 = min(frame.shape[0], row.y2)
    roi = frame[y1:y2, x1:x2]

    if roi.size > 0:
        best_name, best_score, details = best_match(roi, TEMPLATES)
    else:
        best_name, best_score, details = "none", 0.0, {}

    color = PALETTE[idx % len(PALETTE)]
    flag = "[HIT]" if best_score >= 0.80 else "[---]"

    print("{:<22} ({:4},{:4},{:4},{:3})   {:<28} {:.4f} {}".format(
        label, row.x, row.y, row.w, row.h, best_name, best_score, flag))
    for tname, sc in details.items():
        print("  {:>22}  {:<28} {:.4f}".format("", tname, sc))
    print()

    # Ve khung len annotated
    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 4)
    txt_label = "#{} {}".format(idx+1, label)
    cv2.putText(annotated, txt_label, (x1+6, y1+36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.80, (0,0,0), 4)
    cv2.putText(annotated, txt_label, (x1+6, y1+36),
                cv2.FONT_HERSHEY_SIMPLEX, 0.80, color, 2)
    txt_score = "{} {:.3f} {}".format(flag, best_score, best_name)
    cv2.putText(annotated, txt_score, (x1+6, y2-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,0,0), 3)
    cv2.putText(annotated, txt_score, (x1+6, y2-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255,255,255), 1)

    # Luu crop rieng
    if roi.size > 0:
        safe = label.replace(" ","_").replace("(","").replace(")","").replace("/","_")
        cv2.imwrite(str(OUT_DIR / "crop_{}.png".format(safe)), roi)

# 5. Luu annotated
out_path = OUT_DIR / "live_debug_annotated.png"
cv2.imwrite(str(out_path), annotated)
print("[OK] Annotated: " + str(out_path))
print("[OK] Crops: sample_images/crop_*.png")
