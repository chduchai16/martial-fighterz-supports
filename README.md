# Bot Tự Động Hoá Game Mobile trên MuMu / LDPlayer (ADB + OpenCV)

Tool tự động hoá quy trình lặp lại (VIP7 ➔ Kim Cương ➔ Even/Odd ➔ VIP9 ➔ Kim Cương ➔ Even/Odd ➔ Reset) chạy trên giả lập Android (MuMu Player / LDPlayer) với kiến trúc nhận diện **Template Matching Auto-Scale đa độ phân giải** độ trễ thấp (<30ms).

---

## 📁 Cấu Trúc Dự Án Chuẩn Hóa

```
martial-fighterz-supports/
│
├── src/                        # Source code chính của dự án
│   ├── core/                   # Engine & Logic nghiệp vụ Bot
│   │   ├── __init__.py         # Core package exports
│   │   ├── bot.py              # State Machine điều khiển luồng tự động
│   │   ├── capture.py          # FastCapture (ADB Screencap + Tap/Swipe)
│   │   ├── vision.py           # VisionEngine (Template matching, quét dòng)
│   │   ├── config.py           # Cấu hình toạ độ, thresholds, timeout
│   │   └── coordinates.py      # Quản lý toạ độ co giãn theo tỷ lệ
│   │
│   └── ui/                     # Giao diện người dùng
│       ├── __init__.py         # UI package exports
│       └── gui_app.py          # Dashboard CustomTkinter (Light/Dark Mode)
│
├── assets/                     # Tài nguyên ảnh & dữ liệu toạ độ
│   ├── templates/              # Ảnh template icon/nút nhận diện (.png)
│   ├── samples/                # Ảnh chụp mẫu các bước trong game
│   ├── line_4/                 # Ảnh mẫu kiểm tra dòng 4 VIP9
│   └── coordinates.json        # Dữ liệu toạ độ các phần tử UI game
│
├── tools/                      # Bộ công cụ hỗ trợ phát triển & đo toạ độ
│   ├── region_picker.py        # Giao diện đo toạ độ & crop template trực quan
│   ├── screenshot_tool.py      # Chụp nhanh màn hình từ giả lập
│   └── crop_vip9_line4.py      # Tool kiểm tra chụp 4 dòng VIP9
│
├── gui_app.py                  # Entrypoint khởi chạy giao diện Desktop
├── main.py                     # Entrypoint CLI chạy dòng lệnh & test
├── requirements.txt            # Thư viện phụ thuộc (OpenCV, CustomTkinter...)
└── .gitignore                  # Bỏ qua cache, logs và debug dumps
```

---

## 🚀 Hướng Dẫn Cài Đặt & Thiết Lập

### 1. Cài đặt Python & Thư viện

Yêu cầu **Python 3.9+**. Cài đặt các gói phụ thuộc:

```bash
pip install -r requirements.txt
```

> **Lưu ý về Scrcpy:** Đảm bảo `scrcpy` hoặc `adb` có sẵn trong biến môi trường `PATH`. Thư viện `scrcpy-client` sẽ tự động kích hoạt H.264 video stream để đạt tốc độ capture <50ms.

---

### 2. Cài đặt Giả Lập LDPlayer

1. **Cố định độ phân giải:**
   - Mở LDPlayer ➔ **Cài đặt (Settings)** ➔ **Nâng cao (Advanced)**.
   - Chọn chế độ **Điện thoại (Mobile/Portrait)** với độ phân giải cố định: `1080 x 1920` (hoặc `720 x 1280`).
   - Tắt tính năng tự động co giãn cửa sổ để đảm bảo toạ độ logic pixel luôn đồng nhất.
2. **Bật ADB Debugging:**
   - Trong LDPlayer ➔ Cài đặt khác ➔ Bật **ADB Debugging** (Mở kết nối cục bộ).
3. **Kiểm tra kết nối:**
   ```bash
   adb devices
   adb shell wm size
   # Kết quả: Physical size: 1080x1920
   ```

---

## 🛠️ Quy Trình Lấy Template & Căn Chỉnh Toạ Độ (Chỉ cần làm 1 lần)

### Bước 1: Mở tool `region_picker.py`

Chạy tool chụp trực tiếp từ màn hình LDPlayer:

```bash
python tools/region_picker.py
```

*(Hoặc chụp qua file ảnh: `python tools/region_picker.py --image path/to/screen.png`)*

### Bước 2: Cắt ảnh Template
- Dùng chuột trái kéo thả quanh icon **Kim Cương**.
- Nhấn phím **`C`**, chọn số `1` (hoặc gõ `kim_cuong_icon.png`) để lưu vào `images/`.
- Làm tương tự cho các nút khác nếu muốn dùng template matching cho toàn bộ nút: `vip7_tab.png`, `vip9_tab.png`, `even_button.png`, `odd_button.png`, `claim_button.png`, `reset_button.png`.

### Bước 3: Đo vùng ROI các dòng trong VIP7 & VIP9
- Dùng chuột kéo chọn bao quanh từng dòng (Dòng 1, Dòng 2, Dòng 3 của VIP7).
- Console sẽ in ra dạng: `Rect(x=100, y=600, w=880, h=180)`.
- Sao chép các toạ độ này cập nhật vào danh sách `vip7_rows` và `vip9_rows` trong file [config.py](file:///d:/python/martial-fighterz-supports/config.py).

---

## 🎮 Hướng Dẫn Sử Dụng Bot

### 1. Test tốc độ Capture (FPS & Latency)

Kiểm tra xem scrcpy stream đã hoạt động ở mức <50ms chưa:

```bash
python main.py --mode test-capture
```

### 2. Test từng State riêng lẻ

Trước khi chạy vòng lặp vô hạn, bạn nên kiểm tra từng hành động:

```bash
# Test nhận diện & click Kim Cương trong VIP7:
python main.py --mode test-state --state diamond_vip7

# Test chọn Even/Odd:
python main.py --mode test-state --state even_odd

# Test bấm nhận quà (Claim):
python main.py --mode test-state --state claim

# Test bấm Reset:
python main.py --mode test-state --state reset
```

### 3. Test chạy thử 1 chu kỳ hoàn chỉnh

```bash
python main.py --mode test-cycle --debug
```

### 4. Chạy vòng lặp vô hạn (`run_forever`)

```bash
# Chạy mặc định (Even/Odd random 50/50):
python main.py --mode run

# Chạy với chiến lược luôn chọn Chẵn (Even):
python main.py --mode run --strategy even

# Chạy với thiết bị ADB chỉ định và bật log debug:
python main.py --mode run --serial 127.0.0.1:5555 --debug
```

Để dừng bot: Nhấn `Ctrl + C` trên terminal. Bot sẽ in bảng thống kê số vòng thành công/thất bại và tự đóng kết nối an toàn.

---

## 🛡️ Cơ Chế An Toàn & Xử Lý Lỗi

1. **So khớp đa vùng (Best Match Across Rows):** Thay vì chỉ lấy kết quả đầu tiên vượt ngưỡng, thuật toán quét đồng thời cả 3 dòng (VIP7) hoặc 4 dòng (VIP9), tính toán điểm confidence của từng dòng và chỉ chọn dòng có điểm cao nhất vượt ngưỡng `diamond_threshold` (mặc định `0.78`).
2. **Debug Dump tự động:** Khi có bước bị fail hoặc confidence thấp, bot tự động chụp màn hình, vẽ khung ROI các dòng và lưu vào thư mục `debug_dumps/` kèm timestamp để bạn dễ dàng kiểm tra lại.
3. **Random Tap Jitter:** Thao tác tap có độ lệch ngẫu nhiên `±5px` và thời gian giữ phím tự nhiên để tương tác mượt mà với UI game.
