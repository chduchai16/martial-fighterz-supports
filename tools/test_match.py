import cv2
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sample_dir = ROOT_DIR / "assets" / "samples" if (ROOT_DIR / "assets" / "samples").exists() else ROOT_DIR / "sample_images"
template_dir = ROOT_DIR / "assets" / "templates" if (ROOT_DIR / "assets" / "templates").exists() else ROOT_DIR / "images"

img = cv2.imread(str(sample_dir / 'fourth_step.png'))
tpl = cv2.imread(str(template_dir / 'kim_cuong_icon.png'))

res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

print(f"Match confidence on fourth_step.png: {max_val:.4f} at location {max_loc}")
