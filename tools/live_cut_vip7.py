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
    out_dir = ROOT_DIR / "live_crops_vip7"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 Bắt đầu live cut VIP7 trực tiếp từ giả lập...")
    cap = FastCapture(device_serial=config.device_serial)
    vision = VisionEngine(config.templates)
    cap.start()

    try:
        time.sleep(0.5)

        # 1. Bấm vào Tab VIP7
        vip7_tab_x, vip7_tab_y = 847, 437
        print(f"👉 Chuyển sang Tab VIP7 tại ({vip7_tab_x}, {vip7_tab_y})...")
        cap.tap(vip7_tab_x, vip7_tab_y)
        time.sleep(0.6)

        # 2. Chụp màn hình trạng thái ban đầu (Dòng 1 và Dòng 2 của VIP7)
        frame_unscrolled = cap.get_latest_frame(timeout=3.5)
        if frame_unscrolled is None:
            print("❌ Lỗi: Không thể chụp frame ban đầu!")
            return

        h, w = frame_unscrolled.shape[:2]
        print(f"📸 Đã chụp màn hình ban đầu VIP7: {w}x{h}")
        cv2.imwrite(str(out_dir / "00_vip7_full_truoc_cuon.png"), frame_unscrolled)

        # Lấy toạ độ từ config
        roi_d1 = config.vip7_initial_rows[0]
        roi_d2 = config.vip7_initial_rows[1]

        # Cắt Dòng 1 & Dòng 2
        d1_o1 = frame_unscrolled[roi_d1.y : roi_d1.y2, roi_d1.x : roi_d1.x2]
        d1_full = frame_unscrolled[roi_d1.y - 19 : roi_d1.y2 + 48, 10:1070]
        cv2.imwrite(str(out_dir / "vip7_dong_1_o1.png"), d1_o1)
        cv2.imwrite(str(out_dir / "vip7_dong_1_full.png"), d1_full)

        d2_o1 = frame_unscrolled[roi_d2.y : roi_d2.y2, roi_d2.x : roi_d2.x2]
        d2_full = frame_unscrolled[roi_d2.y - 19 : roi_d2.y2 + 48, 10:1070]
        cv2.imwrite(str(out_dir / "vip7_dong_2_o1.png"), d2_o1)
        cv2.imwrite(str(out_dir / "vip7_dong_2_full.png"), d2_full)

        # 3. Cuộn khay lên 1 lần để soi Dòng 3 của VIP7
        x1 = int(config.swipe_vip9_start_ratio[0] * w)
        y1 = int(config.swipe_vip9_start_ratio[1] * h)
        x2 = int(config.swipe_vip9_end_ratio[0] * w)
        y2 = int(config.swipe_vip9_end_ratio[1] * h)

        print(f"👉 Đang cuộn khay item VIP7 lên: ({x1}, {y1}) -> ({x2}, {y2})...")
        cap.swipe(x1, y1, x2, y2, duration=0.45)
        time.sleep(config.wait_after_scroll + 0.3)

        # 4. Chụp màn hình sau khi cuộn
        frame_scrolled = cap.get_latest_frame(timeout=3.5)
        if frame_scrolled is None:
            print("❌ Lỗi: Không thể chụp frame sau khi cuộn!")
            return

        print(f"📸 Đã chụp màn hình sau khi cuộn VIP7: {w}x{h}")
        cv2.imwrite(str(out_dir / "00_vip7_full_sau_cuon.png"), frame_scrolled)

        roi_d3 = config.vip7_scrolled_row3_candidates[0]
        d3_o1 = frame_scrolled[roi_d3.y : roi_d3.y2, roi_d3.x : roi_d3.x2]
        d3_full = frame_scrolled[roi_d3.y - 19 : roi_d3.y2 + 48, 10:1070]
        cv2.imwrite(str(out_dir / "vip7_dong_3_o1.png"), d3_o1)
        cv2.imwrite(str(out_dir / "vip7_dong_3_full.png"), d3_full)

        # Vẽ khung đánh dấu để người dùng đối chiếu trực quan
        vis1 = frame_unscrolled.copy()
        cv2.rectangle(vis1, (roi_d1.x, roi_d1.y), (roi_d1.x2, roi_d1.y2), (0, 255, 255), 3)
        cv2.putText(vis1, "VIP7 - DONG 1 [O 1]", (roi_d1.x - 100, roi_d1.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.rectangle(vis1, (roi_d2.x, roi_d2.y), (roi_d2.x2, roi_d2.y2), (0, 255, 255), 3)
        cv2.putText(vis1, "VIP7 - DONG 2 [O 1]", (roi_d2.x - 100, roi_d2.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imwrite(str(out_dir / "00_tong_quan_soi_o1_vip7_dong_1_va_2.png"), vis1)

        vis2 = frame_scrolled.copy()
        cv2.rectangle(vis2, (roi_d3.x, roi_d3.y), (roi_d3.x2, roi_d3.y2), (0, 255, 255), 3)
        cv2.putText(vis2, "VIP7 - DONG 3 [O 1]", (roi_d3.x - 100, roi_d3.y - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imwrite(str(out_dir / "00_tong_quan_soi_o1_vip7_dong_3.png"), vis2)

        # 5. Cuộn trả lại vị trí ban đầu
        print(f"🔄 Cuộn trả khay item VIP7 về lại đầu trang: ({x2}, {y2}) -> ({x1}, {y1})...")
        cap.swipe(x2, y2, x1, y1, duration=0.45)
        time.sleep(0.4)

        # 6. Đánh giá nhận diện từng dòng
        print("\n" + "="*60)
        print("📊 KẾT QUẢ NHẬN DIỆN THỰC TẾ TRÊN CÁC DÒNG VIP7:")
        print("="*60)
        vip7_slots = [
            ("VIP7 Dòng 1", frame_unscrolled, roi_d1),
            ("VIP7 Dòng 2", frame_unscrolled, roi_d2),
            ("VIP7 Dòng 3", frame_scrolled, roi_d3),
        ]

        for name, frame_ref, roi in vip7_slots:
            match, target_type = vision.check_row_for_targets(frame_ref, roi, min_threshold=config.diamond_threshold)
            status = f"💎 CÓ KIM CƯƠNG (conf: {match.confidence:.4f})" if match.found else f"❌ Không có (conf: {match.confidence:.4f})"
            print(f"👉 {name} ({roi.x}, {roi.y}, {roi.w}, {roi.h}): {status}")

        # 7. Quét toàn màn hình để tìm xem Kim Cương thực tế đang ở toạ độ nào trên màn hình VIP7!
        print("\n🔍 QUÉT TOÀN BỘ KHAY ITEM VIP7 ĐỂ TÌM VỊ TRÍ THỰC TẾ CỦA KIM CƯƠNG:")
        tray_all = Rect(x=0, y=int(0.55 * h), w=w, h=int(0.38 * h))
        for t_name in ["kim_cuong_clean_en", "kim_cuong_inner", "kim_cuong"]:
            m_before = vision.find_template(frame_unscrolled, t_name, threshold=0.50, roi=tray_all)
            m_after = vision.find_template(frame_scrolled, t_name, threshold=0.50, roi=tray_all)
            print(f"   [Trước cuộn] Mẫu '{t_name}': conf={m_before.confidence:.4f}, center=({m_before.center[0]}, {m_before.center[1]})")
            print(f"   [Sau cuộn]   Mẫu '{t_name}': conf={m_after.confidence:.4f}, center=({m_after.center[0]}, {m_after.center[1]})")

        print(f"\n✅ Đã lưu toàn bộ ảnh VIP7 vào thư mục: {out_dir}")

    finally:
        cap.stop()

if __name__ == "__main__":
    main()
