import cv2
from pathlib import Path

BASE = Path('d:/python/martial-fighterz-supports')
img = cv2.imread(str(BASE / 'sample_images' / 'fifth_step.png'))
tpl = cv2.imread(str(BASE / 'images' / 'rut_lui_button.png'))

res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)

print(f"Rut lui match confidence on fifth_step.png: {max_v:.4f} at {max_l}")
