"""
Tool tương tác Region Picker: Giúp người dùng kéo chuột chọn vùng toạ độ (x, y, w, h)
và lưu trực tiếp vào coordinates.json hoặc cắt lưu ảnh template vào images/.
"""
import argparse
from pathlib import Path
import sys
from typing import Optional, Tuple

import cv2
import numpy as np

# Thêm thư mục gốc vào sys.path để import config & coordinates
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import IMAGES_DIR
from coordinates import coords


class RegionPicker:
    def __init__(self, image_path: Optional[str] = None):
        self.image_path = image_path
        self.original_img: Optional[np.ndarray] = None
        self.display_img: Optional[np.ndarray] = None
        
        # Trạng thái chuột
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.cur_x, self.cur_y = -1, -1
        self.selected_rect: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h

        self.window_name = "Region Picker - [Keo chuot chon: S de luu toa do, C de cat anh, R de reset, Q de thoat]"

    def load_image(self, path_or_img):
        if isinstance(path_or_img, (str, Path)):
            self.original_img = cv2.imread(str(path_or_img))
            if self.original_img is None:
                raise ValueError(f"Không thể đọc ảnh: {path_or_img}")
        elif isinstance(path_or_img, np.ndarray):
            self.original_img = path_or_img.copy()
        else:
            raise TypeError("Ảnh không hợp lệ")
        self.display_img = self.original_img.copy()

    def capture_from_adb(self, serial: Optional[str] = None):
        """Chụp trực tiếp từ thiết bị ADB."""
        import adbutils
        print("Đang chụp màn hình từ LDPlayer qua ADB...")
        if serial:
            device = adbutils.adb.device(serial)
        else:
            devices = adbutils.adb.device_list()
            if not devices:
                raise RuntimeError("Không tìm thấy thiết bị ADB nào đang kết nối!")
            device = devices[0]

        pil_img = device.screenshot()
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        self.load_image(img)
        print(f"Đã chụp ảnh thành công: kích thước {img.shape[1]}x{img.shape[0]}")

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
            self.cur_x, self.cur_y = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.cur_x, self.cur_y = x, y
                self.display_img = self.original_img.copy()
                cv2.rectangle(self.display_img, (self.ix, self.iy), (self.cur_x, self.cur_y), (0, 255, 0), 2)
                
                # Tính toạ độ
                rx = min(self.ix, self.cur_x)
                ry = min(self.iy, self.cur_y)
                rw = abs(self.cur_x - self.ix)
                rh = abs(self.cur_y - self.iy)
                text = f"x={rx}, y={ry}, w={rw}, h={rh}"
                cv2.putText(self.display_img, text, (rx, max(25, ry - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            rx = min(self.ix, x)
            ry = min(self.iy, y)
            rw = abs(x - self.ix)
            rh = abs(y - self.iy)
            if rw > 0 and rh > 0:
                self.selected_rect = (rx, ry, rw, rh)
                self.display_img = self.original_img.copy()
                cv2.rectangle(self.display_img, (rx, ry), (rx + rw, ry + rh), (0, 0, 255), 2)
                text = f"Rect(x={rx}, y={ry}, w={rw}, h={rh}) | Center: ({rx + rw // 2}, {ry + rh // 2})"
                cv2.putText(self.display_img, text, (rx, max(25, ry - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                print(f"\n[ĐÃ CHỌN VÙNG]: Rect(x={rx}, y={ry}, w={rw}, h={rh}) | Tâm: ({rx + rw // 2}, {ry + rh // 2})")

    def run(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window_name, self.mouse_callback)

        h, w = self.original_img.shape[:2]
        print("\n" + "="*65)
        print(f"REGION PICKER & TEMPLATE CROPPER (Kích thước ảnh: {w}x{h})")
        print("="*65)
        print("HƯỚNG DẪN:")
        print(" - Kéo chuột trái: Chọn vùng toạ độ / đối tượng / nút / dòng")
        print(" - Phím [S]: Lưu toạ độ vùng đã chọn vào file coordinates.json")
        print(" - Phím [C]: Cắt vùng đã chọn và lưu thành ảnh template vào images/")
        print(" - Phím [R]: Reset vùng chọn")
        print(" - Phím [Q] hoặc [ESC]: Thoát")
        print("="*65 + "\n")

        while True:
            cv2.imshow(self.window_name, self.display_img)
            key = cv2.waitKey(20) & 0xFF

            if key in (27, ord('q'), ord('Q')):
                break
            elif key in (ord('r'), ord('R')):
                self.selected_rect = None
                self.display_img = self.original_img.copy()
                print("Đã reset vùng chọn.")
            elif key in (ord('s'), ord('S')):
                if self.selected_rect is None:
                    print("⚠️ Chưa chọn vùng nào! Hãy kéo chuột chọn vùng trước khi bấm S.")
                    continue
                rx, ry, rw, rh = self.selected_rect
                elem_key = input("\nNhập mã định danh toạ độ (VD: tab_vip7, btn_even, row_1_vip7...): ").strip()
                desc = input("Nhập mô tả ngắn cho nút này: ").strip()
                if elem_key:
                    coords.update_element(elem_key, desc or elem_key, (rx, ry, rw, rh), w, h)
                    print(f"✅ Đã lưu toạ độ '{elem_key}' vào coordinates.json thành công!")
            elif key in (ord('c'), ord('C')):
                if self.selected_rect is None:
                    print("⚠️ Chưa chọn vùng nào! Hãy kéo chuột để chọn trước khi bấm C.")
                    continue
                rx, ry, rw, rh = self.selected_rect
                crop_img = self.original_img[ry:ry+rh, rx:rx+rw]
                
                print("\nDanh sách tên template gợi ý:")
                print(" 1. kim_cuong_icon.png")
                print(" 2. vip7_tab.png")
                print(" 3. vip9_tab.png")
                print(" 4. even_button.png")
                print(" 5. odd_button.png")
                print(" 6. claim_button.png")
                print(" 7. reset_button.png")
                filename = input("Nhập tên file để lưu (VD: kim_cuong_icon.png hoặc số 1-7): ").strip()
                
                mapping = {
                    "1": "kim_cuong_icon.png",
                    "2": "vip7_tab.png",
                    "3": "vip9_tab.png",
                    "4": "even_button.png",
                    "5": "odd_button.png",
                    "6": "claim_button.png",
                    "7": "reset_button.png",
                }
                if filename in mapping:
                    filename = mapping[filename]
                elif not filename.endswith(".png"):
                    filename += ".png"

                save_path = IMAGES_DIR / filename
                cv2.imwrite(str(save_path), crop_img)
                print(f"✅ Đã lưu ảnh template thành công tại: {save_path}")

        cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool chọn vùng toạ độ và crop template ảnh")
    parser.add_argument("--image", "-i", type=str, help="Đường dẫn file ảnh có sẵn (nếu có)")
    parser.add_argument("--serial", "-s", type=str, help="ADB Serial của LDPlayer (nếu muốn chụp trực tiếp)")
    args = parser.parse_args()

    picker = RegionPicker()
    if args.image:
        picker.load_image(args.image)
    else:
        # Nếu có file trong sample_images, ưu tiên load
        default_sample = ROOT_DIR / "sample_images" / "first_step.png"
        if default_sample.exists():
            print(f"Đang mở ảnh mẫu có sẵn: {default_sample}")
            picker.load_image(default_sample)
        else:
            try:
                picker.capture_from_adb(serial=args.serial)
            except Exception as e:
                print(f"Lỗi: {e}")
                print("Nếu chưa kết nối ADB, bạn có thể truyền ảnh qua: python tools/region_picker.py --image sample_images/first_step.png")
                sys.exit(1)

    picker.run()
