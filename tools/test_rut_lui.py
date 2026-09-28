import cv2
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sample_dir = ROOT_DIR / "assets" / "samples" if (ROOT_DIR / "assets" / "samples").exists() else ROOT_DIR / "sample_images"
template_dir = ROOT_DIR / "assets" / "templates" if (ROOT_DIR / "assets" / "templates").exists() else ROOT_DIR / "images"

img = cv2.imread(str(sample_dir / 'fifth_step.png'))
tpl = cv2.imread(str(template_dir / 'rut_lui_button.png'))

res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
min_v, max_v, min_l, max_l = cv2.minMaxLoc(res)

print(f"Rut lui match confidence on fifth_step.png: {max_v:.4f} at {max_l}")
