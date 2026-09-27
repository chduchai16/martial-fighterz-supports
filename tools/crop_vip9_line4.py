"""
Script chụp ảnh và nhận diện chính xác 4 Dòng của VIP 9:
- Dòng 1, 2, 3: Chụp ở màn hình ban đầu (chưa cuộn)
- Dòng 4: Chụp sau khi vuốt cuộn lên
Lưu đúng 4 file ảnh tương ứng vào thư mục 'line_4'.
"""
from pathlib import Path
import shutil
import sys
import time

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import cv2
import numpy as np

from capture import FastCapture
from config import config
from vision import VisionEngine


def main():
    output_dir = Path("line_4")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Dọn dẹp các file cũ trong thư mục line_4
    for f in output_dir.glob("*.png"):
        try:
            f.unlink()
        except Exception:
            pass

    print(f"📁 Thư mục lưu 4 dòng VIP 9: {output_dir.resolve()}\n")

    cap = FastCapture(device_serial=config.device_serial)
    vision = VisionEngine(config.templates)
    cap.start()

    try:
        # 1. Bấm vào Tab VIP 9
        vip9_pos = config.vip9_tab_pos
        print(f"👉 1. Mở Tab VIP 9 tại toạ độ {vip9_pos}...")
        cap.tap(vip9_pos[0], vip9_pos[1])
        time.sleep(1.0)

        # Lấy frame ban đầu (chưa cuộn)
        initial_frame = cap.get_latest_frame(timeout=3.5)
        if initial_frame is None:
            print("❌ Không chụp được ảnh màn hình!")
            return

        print("📸 2. Cắt và nhận diện 3 dòng đầu (Dòng 1, Dòng 2, Dòng 3)...")
        initial_rows = config.vip9_initial_rows
        for idx, row in enumerate(initial_rows):
            cropped = initial_frame[row.y : row.y2, row.x : row.x2]
            filename = output_dir / f"vip9_dong_{idx+1}.png"
            cv2.imwrite(str(filename), cropped)

            match = vision.find_template(cropped, "kim_cuong", threshold=0.50)
            status = "💎 CÓ KIM CƯƠNG" if match.confidence >= config.diamond_threshold else "❌ Không có"
            print(f"   🔹 Dòng {idx+1} -> File: {filename.name} | Conf: {match.confidence:.3f} -> {status}")

        # 2. Vuốt cuộn lên để chụp Dòng 4
        w, h = config.target_width, config.target_height
        x1 = int(config.swipe_vip9_start_ratio[0] * w)
        y1 = int(config.swipe_vip9_start_ratio[1] * h)
        x2 = int(config.swipe_vip9_end_ratio[0] * w)
        y2 = int(config.swipe_vip9_end_ratio[1] * h)
        print(f"\n👉 3. Vuốt cuộn lên ({x1}, {y1}) -> ({x2}, {y2}) để lấy Dòng 4...")
        cap.swipe(x1, y1, x2, y2, duration=0.4)
        time.sleep(1.2)

        scrolled_frame = cap.get_latest_frame(timeout=3.5)
        if scrolled_frame is None:
            print("❌ Không chụp được ảnh sau khi cuộn!")
            return

        print("📸 4. Cắt và nhận diện Dòng 4...")
        scrolled_rows = config.vip9_scrolled_rows
        if scrolled_rows:
            r4 = scrolled_rows[0]
            cropped_r4 = scrolled_frame[r4.y : r4.y2, r4.x : r4.x2]
            filename = output_dir / "vip9_dong_4.png"
            cv2.imwrite(str(filename), cropped_r4)

            match4 = vision.find_template(cropped_r4, "kim_cuong", threshold=0.50)
            status4 = "💎 CÓ KIM CƯƠNG" if match4.confidence >= config.diamond_threshold else "❌ Không có"
            print(f"   🔹 Dòng 4 -> File: {filename.name} | Conf: {match4.confidence:.3f} -> {status4}")

        # Cuộn trả khay item về đầu trang để hiện full Dòng 1
        print(f"\n🔄 5. Đang cuộn trả khay item về lại đầu trang (hiện full Dòng 1)...")
        cap.swipe(x2, y2, x1, y1, duration=0.4)
        time.sleep(0.8)

        print(f"\n✅ Đã hoàn tất! Trong thư mục 'line_4' hiện tại lưu đúng 4 file:")
        print("   - vip9_dong_1.png")
        print("   - vip9_dong_2.png")
        print("   - vip9_dong_3.png")
        print("   - vip9_dong_4.png")

    finally:
        cap.stop()


if __name__ == "__main__":
    main()
