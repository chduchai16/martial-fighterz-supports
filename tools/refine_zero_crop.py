from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"

# Vi tri that cua so 0: x tu 142 den 176, y tu 1675 den 1714
zero_tight = img[1676:1713, 143:175]
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_tight)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_tight)
cv2.imwrite(str(ROOT_DIR / "debug_crops" / "template_zero_tight.png"), zero_tight)

print("ZERO_TIGHT_SAVED:", zero_tight.shape)
