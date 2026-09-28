# ĐẶC TẢ GAMEPLAY & CƠ CHẾ TỰ ĐỘNG HOÁ: MINI-GAME CHẴN LẺ (VIP7 & VIP9)

Tài liệu mô tả chi tiết toàn bộ logic nghiệp vụ, quy trình vận hành (workflow), cơ chế xử lý ngoại lệ và kiến trúc kỹ thuật của hệ thống Bot tự động chơi mini-game Chẵn Lẻ (Martial Fighterz).

---

## 1. TỔNG QUAN GAMEPLAY

### 1.1 Mục tiêu
Tự động hoá việc đổi thưởng và chơi xúc xắc Chẵn Lẻ tại 2 khu vực đặc quyền: **VIP 7** và **VIP 9**.
- Tìm và chỉ chơi các dòng phần thưởng chứa **Kim Cương (Diamond)**.
- Bỏ qua các dòng vật phẩm thông thường (đá, vàng, rác...).
- Tối ưu hoá số lượt nhận quà cho mỗi dòng Kim Cương trước khi chuyển dòng hoặc làm mới (Reset) chu kỳ.

### 1.2 Quy tắc từng khu vực
| Khu vực | Số dòng hiển thị ban đầu | Thao tác cuộn | Số dòng tối đa | Số lượt chơi tối đa / dòng |
| :--- | :---: | :---: | :---: | :---: |
| **VIP 7** (Tab 3) | 3 dòng (Dòng 1, 2, 3) | Không | 3 | **2 lượt** |
| **VIP 9** (Tab 4) | 3 dòng (Dòng 1, 2, 3) | Có (Cuộn lên để xem Dòng 4) | 4 | **3 lượt** |

---

## 2. QUY TRÌNH VẬN HÀNH CHI TIẾT (WORKFLOW)

### 2.1 Chu kỳ đảo chiều thông minh (Alternating Loop)
Để tối ưu tốc độ và giảm thiểu thao tác bấm đổi Tab không cần thiết, bot áp dụng quy luật đảo chiều:
- **Chu kỳ N (bắt đầu từ VIP 7):**
  $$\text{Vào VIP 7} \longrightarrow \text{Chơi Kim Cương VIP 7} \longrightarrow \text{Sang VIP 9} \longrightarrow \text{Chơi Kim Cương VIP 9} \longrightarrow \text{Bấm Reset (ở lại VIP 9)}$$
- **Chu kỳ N + 1 (bắt đầu từ VIP 9):**
  $$\text{Chơi ngay VIP 9} \longrightarrow \text{Sang VIP 7} \longrightarrow \text{Chơi Kim Cương VIP 7} \longrightarrow \text{Bấm Reset (ở lại VIP 7)}$$

---

### 2.2 Quy trình quét dòng Kim Cương (Tuần tự từ trên xuống)
Tại mỗi Tab VIP, bot quét lần lượt theo thứ tự từ trên xuống dưới:

```
[Bắt đầu Tab VIP]
       │
       ▼
 [Kiểm tra Dòng 1] ──(Có Kim Cương >= 0.80)──► [Chơi đủ lượt Dòng 1]
       │ (Không có)                                    │
       ▼                                              ▼
 [Kiểm tra Dòng 2] ──(Có Kim Cương >= 0.80)──► [Chơi đủ lượt Dòng 2]
       │ (Không có)                                    │
       ▼                                              ▼
 [Kiểm tra Dòng 3] ──(Có Kim Cương >= 0.80)──► [Chơi đủ lượt Dòng 3]
       │ (Không có)                                    │
       ▼                                              ▼
 [VIP 9: Cuộn lên kiểm tra Dòng 4] ────────────────────┘
       │
       ▼
 [Chuyển Tab tiếp theo hoặc Reset]
```

1. **Quét Dòng 1:**
   - So khớp hình ảnh với `kim_cuong_inner.png` và `kim_cuong_icon.png`.
   - Nếu độ khớp $\ge 0.80$: Tap vào giữa dòng để mở bàn cờ xúc xắc $\rightarrow$ Chơi.
   - Nếu $< 0.80$: Bỏ qua, xét tiếp Dòng 2.
2. **Quét Dòng 2:** Thực hiện tương tự.
3. **Quét Dòng 3:** Thực hiện tương tự.
4. **Riêng VIP 9 (Dòng 4):**
   - Sau khi duyệt xong 3 dòng đầu, bot thực hiện lệnh vuốt (swipe) cuộn khay item lên:
     $$\text{Từ toạ độ } (50\%, 90\%) \longrightarrow (50\%, 62\%)$$
   - Chụp frame và kiểm tra duy nhất **Dòng 4** (lưu 1 ảnh debug `line_4/vip9_dong_4.png`).
   - Nếu có Kim Cương $\ge 0.80$: Click chơi Dòng 4.
   - Sau khi xử lý xong Dòng 4, bot **luôn vuốt ngược trả lại vị trí ban đầu** (từ $62\% \rightarrow 90\%$) để chuẩn bị cho chu kỳ sau.

---

### 2.3 Quy trình 1 Lượt chơi xúc xắc (Event-Driven Loop)
Mỗi lượt chơi được kích hoạt bằng cách chọn **CHẴN (EVEN)** hoặc **LẺ (ODD)**:

```
                  [Tap chọn nút CHẴN (EVEN)]
                              │
                              ▼
            [Vòng lặp theo dõi màn hình thời gian thực]
            (Stream frame nhị phân trực tiếp từ RAM)
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
 [Nút 'Rút lui' xuất hiện]                [Popup 'OK' xuất hiện]
  (Ở vùng giữa màn hình)                 (Ở nửa dưới màn hình)
          │                                       │
          ▼                                       ▼
  [Bấm nút 'Rút lui']                      [Phân tích chữ trong Popup]
          │                                       │
          ▼                        ┌──────────────┴──────────────┐
[Xác nhận nút đã đóng hẳn]         ▼                             ▼
          │                [Warrior Gem]            [Hết lượt / Thiếu vật phẩm]
          ▼                        │                             │
 [Hoàn thành lượt chơi]            ▼                             ▼
                            [Bấm OK]                      [Bấm OK]
                                   │                             │
                                   ▼                             ▼
                       [Tiếp tục quay tiếp lượt này]    [DỪNG NGAY DÒNG HIỆN TẠI]
                                                        (Chuyển sang dòng kế tiếp)
```

1. **Chọn CHẴN (EVEN):** Bot kiểm tra nút EVEN xuất hiện trên màn hình và tap vào toạ độ tương ứng.
2. **Theo dõi kết quả xúc xắc:**
   - Bot liên tục đọc frame từ RAM (tốc độ $30 - 60\text{ms/frame}$).
   - **Trường hợp 1 - Thành công:** Nút `rut_lui_btn` xuất hiện trong vùng `rut_lui_roi` ($Y: 50\% - 75\%$).
     - Bot tap ngay vào nút Rút lui.
     - Hàm `_confirm_button_closed()` theo dõi tới khi nút biến mất hoàn toàn (nếu sau $0.25\text{s}$ chưa mất sẽ tap bồi).
     - Ghi nhận `SUCCESS`, tăng biến đếm lượt.
   - **Trường hợp 2 - Ra Warrior Gem:** Popup xuất hiện chứa chữ "Warrior Gem".
     - Bot tap OK.
     - Giữ nguyên số lượt và tiếp tục chơi lại cho đủ chỉ tiêu.
   - **Trường hợp 3 - Hết lượt / Thiếu nguyên liệu:** Popup thông báo "Không còn lượt đổi nào" hoặc "Không đủ vật phẩm".
     - Bot tap OK.
     - Thoát ngay khỏi dòng hiện tại (`OUT_OF_ITEMS`), không bấm mò thêm.

---

## 3. CƠ CHẾ BẢO ĐẢM TỐC ĐỘ VÀ ĐỘ ỔN ĐỊNH

### 3.1 Persistent ADB Shell Pipe
- Thay vì mở và đóng tiến trình `adb.exe` cho từng cú chạm (tốn $200 - 300\text{ms}$ mỗi lần), bot duy trì một tiến trình `adb shell` chạy nền xuyên suốt.
- Các lệnh `input tap x y` và `input swipe ...` được ghi trực tiếp vào `stdin` của shell, giảm độ trễ mỗi cú chạm xuống **$< 5\text{ms}$**.

### 3.2 Pure In-Memory Capture (Không rác ổ cứng)
- Sử dụng lệnh:
  ```bash
  adb exec-out screencap -p
  ```
- Dữ liệu ảnh dạng byte stream được nạp trực tiếp vào RAM qua `cv2.imdecode(np.frombuffer(...))`.
- Hoàn toàn **không ghi file ảnh tạm ra ổ đĩa**, không hao mòn SSD, không chiếm dung lượng khi chạy 24/7.
- Bộ nhớ được Python Garbage Collector dọn tự động sau mỗi vòng lặp.

### 3.3 Multi-scale Matching (Độ chính xác cao)
- Dù màn hình giả lập có tỉ lệ hiển thị thế nào, module `vision.py` luôn kiểm tra đa tỉ lệ $[1.0, 0.95, 1.05]$ kết hợp 2 mẫu template:
  - `kim_cuong_inner.png`: Lõi kim cương (nhận diện nhanh, không phụ thuộc viền).
  - `kim_cuong_icon.png`: Toàn bộ icon kim cương.
- Đảm bảo độ nhận diện chính xác $\ge 0.80$, loại bỏ hoàn toàn khả năng nhận diện nhầm các vật phẩm rác khác.

---

## 4. TỔNG KẾT BẢNG TOẠ ĐỘ & ROI (REFERENCE: 1080 x 1920)

| Thành phần | Toạ độ tỉ lệ $(X, Y, W, H)$ | Toạ độ pixel mẫu $(1080 \times 1920)$ |
| :--- | :---: | :---: |
| **Tab VIP 7** | $(0.785, 0.228)$ | $(847, 437)$ |
| **Tab VIP 9** | $(0.913, 0.228)$ | $(986, 437)$ |
| **Nút Reset (Refresh)** | $(0.127, 0.232)$ | $(137, 445)$ |
| **Nút EVEN (CHẴN)** | $(0.871, 0.420)$ | $(940, 806)$ |
| **Nút ODD (LẺ)** | $(0.871, 0.327)$ | $(940, 627)$ |
| **Vùng ROI Nút Rút lui** | $(0.15, 0.50, 0.70, 0.25)$ | $X: 162 \rightarrow 918,\; Y: 960 \rightarrow 1440$ |
| **Vùng ROI Nút OK** | $(0.15, 0.65, 0.70, 0.30)$ | $X: 162 \rightarrow 918,\; Y: 1248 \rightarrow 1824$ |
| **VIP 7 - Dòng 1** | $(0.0088, 0.5848, 0.9824, 0.1262)$ | $X: 9 \rightarrow 1070,\; Y: 1122 \rightarrow 1365$ |
| **VIP 7 - Dòng 2** | $(0.0088, 0.7219, 0.9824, 0.1262)$ | $X: 9 \rightarrow 1070,\; Y: 1386 \rightarrow 1628$ |
| **VIP 7 - Dòng 3** | $(0.0088, 0.8599, 0.9824, 0.1000)$ | $X: 9 \rightarrow 1070,\; Y: 1651 \rightarrow 1843$ |
| **VIP 9 - Dòng 1, 2, 3** | Tương tự tỉ lệ VIP 7 ban đầu | $Y$ từ $58.48\% \rightarrow 94.12\%$ |
| **VIP 9 - Dòng 4 (Sau cuộn)** | $(0.0088, 0.8150, 0.9824, 0.1262)$ | $X: 9 \rightarrow 1070,\; Y: 1564 \rightarrow 1807$ |
