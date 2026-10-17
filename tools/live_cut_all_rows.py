import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# Thêm thư mục gốc vào sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Đảm bảo in tiếng Việt / emoji an toàn trên Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from capture import FastCapture
from src.core.config import config
from src.core.coordinates import Rect
from src.core.vision import VisionEngine

def main():
    out_dir = ROOT_DIR / "live_crops"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 Bắt đầu live cut CHỈ Ô THỨ 1 (Min Earning) của 4 dòng từ giả lập...")
    cap = FastCapture(device_serial=config.device_serial)
    vision = VisionEngine(config.templates)
    cap.start()

    try:
        time.sleep(0.5)

        # 1. Bấm vào Tab VIP9
        vip9_tab_x, vip9_tab_y = 986, 437
        print(f"👉 Chuyển sang Tab VIP9 tại ({vip9_tab_x}, {vip9_tab_y})...")
        cap.tap(vip9_tab_x, vip9_tab_y)
        time.sleep(0.6)

        # 2. Chụp màn hình trạng thái ban đầu (Dòng 1 và Dòng 2)
        frame_unscrolled = cap.get_latest_frame(timeout=3.5)
        if frame_unscrolled is None:
            print("❌ Lỗi: Không thể chụp frame ban đầu!")
            return

        h, w = frame_unscrolled.shape[:2]
        print(f"📸 Đã chụp màn hình ban đầu: {w}x{h}")

        # Lấy trực tiếp toạ độ ROI từ file config chính để đảm bảo trùng khớp 100%
        roi_d1 = config.vip9_initial_rows[0]
        roi_d2 = config.vip9_initial_rows[1]

        # Cắt Ô 1 Dòng 1 & Dòng 2
        d1_o1 = frame_unscrolled[roi_d1.y : roi_d1.y2, roi_d1.x : roi_d1.x2]
        d1_full = frame_unscrolled[roi_d1.y : roi_d1.y2, 10:1070]
        cv2.imwrite(str(out_dir / "dong_1_o1_min_earning.png"), d1_o1)
        cv2.imwrite(str(out_dir / "dong_1_full.png"), d1_full)

        d2_o1 = frame_unscrolled[roi_d2.y : roi_d2.y2, roi_d2.x : roi_d2.x2]
        d2_full = frame_unscrolled[roi_d2.y : roi_d2.y2, 10:1070]
        cv2.imwrite(str(out_dir / "dong_2_o1_min_earning.png"), d2_o1)
        cv2.imwrite(str(out_dir / "dong_2_full.png"), d2_full)

        # 3. Thực hiện vuốt cuộn lên (Swipe UP) 1 lần duy nhất
        x1 = int(config.swipe_vip9_start_ratio[0] * w)
        y1 = int(config.swipe_vip9_start_ratio[1] * h)
        x2 = int(config.swipe_vip9_end_ratio[0] * w)
        y2 = int(config.swipe_vip9_end_ratio[1] * h)

        print(f"👉 Đang cuộn khay item lên: ({x1}, {y1}) -> ({x2}, {y2})...")
        cap.swipe(x1, y1, x2, y2, duration=0.45)
        time.sleep(config.wait_after_scroll + 0.3)

        # 4. Chụp màn hình sau khi cuộn (Dòng 3 và Dòng 4)
        frame_scrolled = cap.get_latest_frame(timeout=3.5)
        if frame_scrolled is None:
            print("❌ Lỗi: Không thể chụp frame sau khi cuộn!")
            return

        print(f"📸 Đã chụp màn hình sau khi cuộn: {w}x{h}")

        roi_d3 = config.vip9_scrolled_row3_candidates[0]
        roi_d4 = config.vip9_scrolled_row4_candidates[0]

        # Cắt Ô 1 Dòng 3 & Dòng 4
        d3_o1 = frame_scrolled[roi_d3.y : roi_d3.y2, roi_d3.x : roi_d3.x2]
        d3_full = frame_scrolled[roi_d3.y : roi_d3.y2, 10:1070]
        cv2.imwrite(str(out_dir / "dong_3_o1_min_earning.png"), d3_o1)
        cv2.imwrite(str(out_dir / "dong_3_full.png"), d3_full)

        d4_o1 = frame_scrolled[roi_d4.y : roi_d4.y2, roi_d4.x : roi_d4.x2]
        d4_full = frame_scrolled[roi_d4.y : roi_d4.y2, 10:1070]
        cv2.imwrite(str(out_dir / "dong_4_o1_min_earning.png"), d4_o1)
        cv2.imwrite(str(out_dir / "dong_4_full.png"), d4_full)

        # 5. Tạo 2 ảnh tổng quan chỉ vẽ khung khoanh đúng Ô THỨ 1
        # Frame 1: Dòng 1 & 2
        vis1 = frame_unscrolled.copy()
        cv2.rectangle(vis1, (roi_d1.x, roi_d1.y), (roi_d1.x2, roi_d1.y2), (0, 255, 255), 3)
        cv2.putText(vis1, "DONG 1: [O 1 DUY NHAT]", (roi_d1.x - 100, roi_d1.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.rectangle(vis1, (roi_d2.x, roi_d2.y), (roi_d2.x2, roi_d2.y2), (0, 255, 255), 3)
        cv2.putText(vis1, "DONG 2: [O 1 DUY NHAT]", (roi_d2.x - 100, roi_d2.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imwrite(str(out_dir / "00_tong_quan_soi_o1_dong_1_va_2.png"), vis1)

        # Frame 2: Dòng 3 & 4
        vis2 = frame_scrolled.copy()
        cv2.rectangle(vis2, (roi_d3.x, roi_d3.y), (roi_d3.x2, roi_d3.y2), (0, 255, 255), 3)
        cv2.putText(vis2, "DONG 3: [O 1 DUY NHAT]", (roi_d3.x - 100, roi_d3.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.rectangle(vis2, (roi_d4.x, roi_d4.y), (roi_d4.x2, roi_d4.y2), (0, 255, 255), 3)
        cv2.putText(vis2, "DONG 4: [O 1 DUY NHAT]", (roi_d4.x - 100, roi_d4.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.imwrite(str(out_dir / "00_tong_quan_soi_o1_dong_3_va_4.png"), vis2)

        # 6. Cuộn trả lại vị trí ban đầu
        print(f"🔄 Cuộn trả khay item về lại đầu trang: ({x2}, {y2}) -> ({x1}, {y1})...")
        cap.swipe(x2, y2, x1, y1, duration=0.45)
        time.sleep(0.4)

        # 7. Phân tích nhận diện THỰC TẾ chỉ trên Ô THỨ 1
        print("\n" + "="*60)
        print("📊 KẾT QUẢ NHẬN DIỆN THỰC TẾ (CHỈ QUÉT Ô THỨ 1 - MIN EARNING):")
        print("="*60)
        slots_data = [
            ("Dòng 1 - Ô 1", frame_unscrolled, roi_d1),
            ("Dòng 2 - Ô 1", frame_unscrolled, roi_d2),
            ("Dòng 3 - Ô 1", frame_scrolled, roi_d3),
            ("Dòng 4 - Ô 1", frame_scrolled, roi_d4),
        ]

        for name, frame_ref, roi in slots_data:
            match, target_type = vision.check_row_for_targets(frame_ref, roi, min_threshold=config.diamond_threshold)
            status = f"💎 CÓ KIM CƯƠNG (conf: {match.confidence:.4f})" if match.found else f"❌ Không có (conf: {match.confidence:.4f})"
            print(f"👉 {name}: {status}")

        print(f"\n✅ Đã lưu toàn bộ ảnh crop Ô THỨ 1 tại: {out_dir}")

    finally:
        cap.stop()

if __name__ == "__main__":
    main()
