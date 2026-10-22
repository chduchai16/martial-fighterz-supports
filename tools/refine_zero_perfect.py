from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"

# Vi tri that tron ven cua so 0: x tu 148 den 178, y tu 1675 den 1714
zero_perfect = img[1675:1713, 149:179]
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_perfect)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_perfect)
cv2.imwrite(str(ROOT_DIR / "debug_crops" / "template_zero_perfect.png"), zero_perfect)

print("ZERO_PERFECT_SAVED:", zero_perfect.shape)
