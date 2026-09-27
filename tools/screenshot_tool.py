"""
Script tiện ích chụp nhanh ảnh màn hình từ LDPlayer lưu vào thư mục images/ hoặc debug_dumps/
"""
import argparse
from datetime import datetime
from pathlib import Path
import sys

import cv2
import numpy as np

# Thêm thư mục gốc vào sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import DEBUG_DIR, IMAGES_DIR


def capture_screenshot(serial: str = None, save_dir: Path = IMAGES_DIR, filename: str = None):
    try:
        import adbutils
    except ImportError:
        print("Vui lòng cài đặt: pip install adbutils")
        return

    if serial:
        device = adbutils.adb.device(serial)
    else:
        devices = adbutils.adb.device_list()
        if not devices:
            print("❌ Không tìm thấy thiết bị ADB nào đang kết nối!")
            return
        device = devices[0]

    print(f"Đang chụp màn hình thiết bị {device.serial}...")
    pil_img = device.screenshot()
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    if not filename:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{ts}.png"
    elif not filename.endswith(".png"):
        filename += ".png"

    save_path = save_dir / filename
    cv2.imwrite(str(save_path), img)
    print(f"✅ Đã lưu ảnh chụp: {save_path} (Kích thước: {img.shape[1]}x{img.shape[0]})")
    return save_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chụp ảnh màn hình từ LDPlayer")
    parser.add_argument("--serial", "-s", type=str, help="ADB Serial của thiết bị")
    parser.add_argument("--name", "-n", type=str, help="Tên file lưu (VD: vip7_screen.png)")
    parser.add_argument("--debug", action="store_true", help="Lưu vào debug_dumps thay vì images")
    args = parser.parse_args()

    target_dir = DEBUG_DIR if args.debug else IMAGES_DIR
    capture_screenshot(serial=args.serial, save_dir=target_dir, filename=args.name)
