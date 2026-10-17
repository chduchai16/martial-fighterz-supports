"""
Script test live chụp và nhận diện Dòng 3, Dòng 4 sau khi cuộn:
- Lưu ảnh full màn hình trước và sau khi cuộn
- Cắt và lưu từng vùng Dòng 3, Dòng 4
- Chạy match template và in ra điểm confidence chi tiết
"""
import sys
from pathlib import Path
import time
import cv2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.capture import FastCapture
from src.core.config import config, IMAGES_DIR
from src.core.vision import VisionEngine

def main():
    out_dir = ROOT_DIR / "line_4"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("🚀 Đang khởi động FastCapture kết nối giả lập...")
    cap = FastCapture(device_serial=config.device_serial)
    vision = VisionEngine(config.templates)
    cap.start()

    try:
        time.sleep(0.5)
        # 1. Chụp frame hiện tại trước khi cuộn
        frame_before = cap.get_latest_frame(timeout=3.5)
        if frame_before is None:
            print("❌ Không chụp được frame hiện tại!")
            return
        
        f_h, f_w = frame_before.shape[:2]
        print(f"📸 Frame hiện tại: {f_w}x{f_h}")
        cv2.imwrite(str(out_dir / "live_before_scroll.png"), frame_before)
        print(f"💾 Đã lưu: {out_dir / 'live_before_scroll.png'}")

        # 2. Thực hiện cuộn lên (Swipe UP)
        w, h = f_w, f_h
        x1 = int(config.swipe_vip9_start_ratio[0] * w)
        y1 = int(config.swipe_vip9_start_ratio[1] * h)
        x2 = int(config.swipe_vip9_end_ratio[0] * w)
        y2 = int(config.swipe_vip9_end_ratio[1] * h)

        print(f"👉 Đang cuộn khay item lên: ({x1}, {y1}) -> ({x2}, {y2})...")
        cap.swipe(x1, y1, x2, y2, duration=0.45)
        time.sleep(config.wait_after_scroll + 0.3)

        # 3. Chụp frame sau khi cuộn lần 1
        frame_after1 = cap.get_latest_frame(timeout=3.5)
        if frame_after1 is None:
            print("❌ Không chụp được frame sau cuộn!")
            return
        cv2.imwrite(str(out_dir / "live_after_scroll1.png"), frame_after1)
        print(f"💾 Đã lưu full màn hình sau cuộn: {out_dir / 'live_after_scroll1.png'}")

        # 4. Kiểm tra các candidate ROIs của Dòng 3 và Dòng 4
        print("\n🔍 ĐANG KIỂM TRA DÒNG 3 (SAU CUỘN LẦN 1):")
        for i, roi in enumerate(config.vip9_scrolled_row3_candidates):
            cropped = frame_after1[roi.y : roi.y2, roi.x : roi.x2]
            crop_path = out_dir / f"live_crop_row3_cand_{i+1}.png"
            cv2.imwrite(str(crop_path), cropped)
            match, target_type = vision.check_row_for_targets(frame_after1, roi, min_threshold=0.50)
            print(f"   Candidate {i+1} ({roi.x},{roi.y},{roi.w},{roi.h}): conf={match.confidence:.4f}, type={target_type} -> Đã lưu {crop_path.name}")

        # 5. Thực hiện cuộn lần 2 để lộ hẳn Dòng 4
        print(f"\n👉 Đang cuộn khay item lần 2 để kiểm tra Dòng 4...")
        cap.swipe(x1, y1, x2, y2, duration=0.45)
        time.sleep(config.wait_after_scroll + 0.3)

        frame_after2 = cap.get_latest_frame(timeout=3.5)
        cv2.imwrite(str(out_dir / "live_after_scroll2.png"), frame_after2)
        print(f"💾 Đã lưu full màn hình sau cuộn lần 2: {out_dir / 'live_after_scroll2.png'}")

        print("\n🔍 ĐANG KIỂM TRA DÒNG 4 (SAU CUỘN LẦN 2):")
        for i, roi in enumerate(config.vip9_scrolled_row4_candidates):
            cropped = frame_after2[roi.y : roi.y2, roi.x : roi.x2]
            crop_path = out_dir / f"live_crop_row4_cand_{i+1}.png"
            cv2.imwrite(str(crop_path), cropped)
            match, target_type = vision.check_row_for_targets(frame_after2, roi, min_threshold=0.50)
            print(f"   Candidate {i+1} ({roi.x},{roi.y},{roi.w},{roi.h}): conf={match.confidence:.4f}, type={target_type} -> Đã lưu {crop_path.name}")

        # 6. Tìm kiếm vị trí thực tế của Kim Cương trên toàn bộ nửa dưới màn hình sau cuộn
        print("\n💎 QUÉT TOÀN BỘ KHAY ITEM ĐỂ TÌM VỊ TRÍ THỰC TẾ KIM CƯƠNG:")
        from src.core.coordinates import Rect
        tray_roi = Rect(x=0, y=int(0.55 * h), w=w, h=int(0.38 * h))
        for t_name in ["kim_cuong_clean_en", "kim_cuong_inner", "kim_cuong"]:
            m = vision.find_template(frame_after2, t_name, threshold=0.50, roi=tray_roi)
            print(f"   Template '{t_name}': found={m.found}, conf={m.confidence:.4f}, center=({m.center[0]},{m.center[1]})")

    finally:
        cap.stop()
        print("\n🏁 Hoàn tất test!")

if __name__ == "__main__":
    main()
