from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"

# Vi tri that bao tron so 0: x tu 152 den 179, y tu 1679 den 1712
zero_exact = img[1679:1712, 152:179]
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_exact)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_exact)
cv2.imwrite(str(ROOT_DIR / "debug_crops" / "template_zero_exact.png"), zero_exact)

print("ZERO_EXACT_SAVED:", zero_exact.shape)
