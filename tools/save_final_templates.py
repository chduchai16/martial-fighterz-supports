from pathlib import Path
import cv2

ROOT_DIR = Path(__file__).resolve().parent.parent
img_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
img = cv2.imread(str(img_p))

templates_dir = ROOT_DIR / "assets" / "templates"
images_dir = ROOT_DIR / "images"

# 1. Cat gon so 0 vien den:
# Canh toa do chuan trong zero_clean: y=1676 den 1712, x=135 den 168
zero_crop = img[1676:1712, 137:168]
cv2.imwrite(str(templates_dir / "input_zero.png"), zero_crop)
cv2.imwrite(str(images_dir / "input_zero.png"), zero_crop)
cv2.imwrite(str(ROOT_DIR / "debug_crops" / "template_zero_final.png"), zero_crop)

# 2. Cat gon cum tien vang kem chu 300000:
# Canh toa do: y tu 1600 den 1720, x tu 620 den 760
coin_300k_crop = img[1605:1718, 622:762]
cv2.imwrite(str(templates_dir / "coin_300k.png"), coin_300k_crop)
cv2.imwrite(str(images_dir / "coin_300k.png"), coin_300k_crop)
cv2.imwrite(str(ROOT_DIR / "debug_crops" / "template_coin_300k_final.png"), coin_300k_crop)

# 3. Cat them chu so 300000 rieng biet de ho tro nhan dien chinh xac
text_300k_only = img[1674:1718, 622:762]
cv2.imwrite(str(templates_dir / "text_300000.png"), text_300k_only)
cv2.imwrite(str(images_dir / "text_300000.png"), text_300k_only)

print("TEMPLATES_SAVED")
