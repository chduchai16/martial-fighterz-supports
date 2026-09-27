import cv2
import numpy as np
from pathlib import Path

BASE = Path('d:/python/martial-fighterz-supports')
img = cv2.imread(str(BASE / 'sample_images' / 'fourth_step.png'))
tpl = cv2.imread(str(BASE / 'images' / 'kim_cuong_icon.png'))

res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

print(f"Match confidence on fourth_step.png: {max_val:.4f} at location {max_loc}")
