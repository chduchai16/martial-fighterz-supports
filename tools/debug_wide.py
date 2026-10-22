import cv2
import numpy as np
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
live_img = cv2.imread(str(ROOT_DIR / "debug_crops" / "live_current_vip7.png"))

cuts_dir = ROOT_DIR / "debug_crops" / "cuts"

# Hãy cắt một mảng rộng quanh ô thưởng dòng 3: y từ 1660 đến 1750, x từ 600 đến 800
wide_box = live_img[1660:1750, 600:800]
cv2.imwrite(str(cuts_dir / "wide_reward_box.png"), wide_box)

# Hãy cắt một mảng rộng quanh avatar dòng 3: y từ 1660 đến 1740, x từ 120 đến 220
wide_avatar = live_img[1660:1740, 120:220]
cv2.imwrite(str(cuts_dir / "wide_avatar_box.png"), wide_avatar)

print("Saved wide boxes")
