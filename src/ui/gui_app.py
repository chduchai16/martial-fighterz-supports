"""
Giao diện Desktop Windows điều khiển GameBot tự động hoá viết bằng CustomTkinter.
Hỗ trợ chuyển đổi Theme Sáng / Tối (Light / Dark Mode), mặc định là giao diện Sáng (Light Mode).
- Cột trái: Bảng điều khiển tính năng, thiết lập tham số, các nút hành động bo góc.
- Cột phải: Live Console Terminal với phông chữ sắc nét, tô màu log, bộ lọc và tự cuộn.
"""
import logging
import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox
from typing import Optional

import customtkinter as ctk

from pathlib import Path
import sys

# Thêm thư mục gốc vào sys.path để import dễ dàng
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.core.bot import GameBot
    from src.core.config import config
except ImportError:
    from bot import GameBot
    from config import config

# Mặc định giao diện SÁNG (Light Mode) theo yêu cầu
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class QueueLogHandler(logging.Handler):
    """Định tuyến log từ logging chuẩn vào queue luồng UI."""
    def __init__(self, log_queue: queue.Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put((record.levelname, msg))
        except Exception:
            self.handleError(record)


class ModernBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Martial Fighterz • Auto Control Panel")
        self.geometry("1180x730")
        self.minsize(980, 620)

        # Quản lý luồng worker
        self.bot_instance: Optional[GameBot] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

        # Queue log cho UI
        self.log_queue = queue.Queue()
        self.all_logs = []

        self._build_ui()
        self._setup_logging()

        # Áp dụng màu cho Text Terminal theo theme Light ban đầu
        self._apply_terminal_theme("Light")

        # Bắt đầu đọc stream log
        self.after(60, self._process_log_queue)

    def _build_ui(self):
        # 1. Top Header Bar
        header = ctk.CTkFrame(self, height=60, fg_color=("#ffffff", "#111827"), corner_radius=0)
        header.pack(fill="x", side="top")

        # Tiêu đề và subtitle bên trái
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=8)

        title_lbl = ctk.CTkLabel(
            title_frame,
            text="MARTIAL FIGHTERZ",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
            text_color=("#0284c7", "#38bdf8")
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_frame,
            text="Autonomous GameBot Controller • v2.0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8")
        )
        sub_lbl.pack(anchor="w")

        # Cụm điều khiển bên phải header: Status Badge + Nút Action + Nút Toggle Theme Sáng/Tối
        right_header_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_header_frame.pack(side="right", padx=20, pady=8)

        # Nút chuyển giao diện Sáng / Tối (ngoài cùng bên phải)
        self.theme_switch = ctk.CTkSwitch(
            right_header_frame,
            text="Chế độ Tối",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("#334155", "#cbd5e1"),
            command=self._on_theme_toggle,
            progress_color="#0284c7"
        )
        # Mặc định là SÁNG nên switch ở trạng thái uncheck (deselected)
        self.theme_switch.deselect()
        self.theme_switch.pack(side="right", padx=(14, 0))

        # Nút Dừng (Stop)
        self.btn_stop = ctk.CTkButton(
            right_header_frame,
            text="⏹ DỪNG LẠI",
            command=self.stop_task,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=("#cbd5e1", "#334155"),
            hover_color="#dc2626",
            text_color=("#64748b", "#94a3b8"),
            width=96,
            height=34,
            corner_radius=8,
            state="disabled"
        )
        self.btn_stop.pack(side="right", padx=(8, 0))

        # Nút Bắt đầu Chạy (Run) - Nằm ngay cạnh tag Sẵn sàng
        self.btn_run = ctk.CTkButton(
            right_header_frame,
            text="▶ BẮT ĐẦU CHẠY",
            command=self.start_task,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            text_color="#ffffff",
            width=140,
            height=34,
            corner_radius=8
        )
        self.btn_run.pack(side="right", padx=(12, 0))

        # Status Badge (Tag Sẵn sàng)
        self.status_badge = ctk.CTkLabel(
            right_header_frame,
            text="● SẴN SÀNG (IDLE)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=("#059669", "#34d399"),
            fg_color=("#d1fae5", "#064e3b"),
            corner_radius=12,
            padx=14,
            pady=6
        )
        self.status_badge.pack(side="right")

        # Main Body Layout
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        # ========================================================
        # CỘT TRÁI: CONTROL PANEL (350px)
        # ========================================================
        left_card = ctk.CTkFrame(
            body,
            width=350,
            fg_color=("#ffffff", "#131b2e"),
            corner_radius=12,
            border_width=1,
            border_color=("#e2e8f0", "#1e293b")
        )
        left_card.pack(side="left", fill="y", padx=(0, 14))
        left_card.pack_propagate(False)

        # Section: Chọn tính năng
        ctk.CTkLabel(
            left_card,
            text="DANH SÁCH TÍNH NĂNG",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=("#0369a1", "#93c5fd")
        ).pack(anchor="w", padx=16, pady=(16, 10))

        self.mode_var = ctk.StringVar(value="chan_le")
        features = [
            ("Chạy Chẵn Lẻ (Even / Odd)", "chan_le"),
            ("Quay Tướng Nhà Rùa", "quay_tuong_nha_rua"),
            ("Chạy Cướp Heo", "cuop_heo"),
            ("Chạy Võ Công", "vo_cong"),
            ("Chạy Ải (Auto Campaign)", "chay_ai"),
        ]

        for text, val in features:
            rb = ctk.CTkRadioButton(
                left_card,
                text=text,
                value=val,
                variable=self.mode_var,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                text_color=("#1e293b", "#e2e8f0"),
                fg_color="#0284c7",
                hover_color="#0369a1",
                border_color=("#94a3b8", "#475569"),
                border_width_unchecked=2,
                radiobutton_width=18,
                radiobutton_height=18
            )
            rb.pack(anchor="w", padx=20, pady=7)

        # Divider
        ctk.CTkFrame(left_card, height=1, fg_color=("#e2e8f0", "#1e293b")).pack(fill="x", padx=16, pady=14)

        # Section: Cấu hình tham số
        ctk.CTkLabel(
            left_card,
            text="THIẾT LẬP THAM SỐ",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=("#0369a1", "#93c5fd")
        ).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(
            left_card,
            text="ADB Device Serial:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#64748b", "#94a3b8")
        ).pack(anchor="w", padx=16, pady=(2, 2))

        self.serial_entry = ctk.CTkEntry(
            left_card,
            placeholder_text="Tự động quét nếu trống",
            fg_color=("#f8fafc", "#0a0e17"),
            border_color=("#cbd5e1", "#334155"),
            text_color=("#0f172a", "#f8fafc"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            height=36
        )
        self.serial_entry.pack(fill="x", padx=16, pady=(0, 8))
        if config.device_serial:
            self.serial_entry.insert(0, config.device_serial)

        ctk.CTkLabel(
            left_card,
            text="Chiến lược xúc xắc:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#64748b", "#94a3b8")
        ).pack(anchor="w", padx=16, pady=(2, 2))

        self.strategy_cb = ctk.CTkComboBox(
            left_card,
            values=["even (Ưu tiên Chẵn)", "odd (Ưu tiên Lẻ)", "random (Ngẫu nhiên 50/50)"],
            fg_color=("#f8fafc", "#0a0e17"),
            border_color=("#cbd5e1", "#334155"),
            dropdown_fg_color=("#ffffff", "#1e293b"),
            text_color=("#0f172a", "#f8fafc"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12),
            height=36,
            state="readonly"
        )
        self.strategy_cb.set("even (Ưu tiên Chẵn)")
        self.strategy_cb.pack(fill="x", padx=16, pady=(0, 8))

        # Switch: Ăn thêm Phục Tùng (C & D)
        self.phuc_tung_switch = ctk.CTkSwitch(
            left_card,
            text="Ăn thêm Phục Tùng (C & D)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#334155", "#cbd5e1"),
            progress_color="#0284c7"
        )
        self.phuc_tung_switch.pack(anchor="w", padx=16, pady=(2, 6))

        # Nhãn & Lựa chọn Ngôn ngữ Game (ở bên dưới mục Phục Tùng)
        ctk.CTkLabel(
            left_card,
            text="Ngôn ngữ Game:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#64748b", "#94a3b8")
        ).pack(anchor="w", padx=16, pady=(2, 2))

        self.lang_cb = ctk.CTkComboBox(
            left_card,
            values=["auto (Tự động nhận diện)", "vi (Tiếng Việt)", "en (English)"],
            fg_color=("#f8fafc", "#0a0e17"),
            border_color=("#cbd5e1", "#334155"),
            dropdown_fg_color=("#ffffff", "#1e293b"),
            text_color=("#0f172a", "#f8fafc"),
            font=ctk.CTkFont(family="Segoe UI", size=12),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=12),
            height=34,
            state="readonly"
        )
        self.lang_cb.set("auto (Tự động nhận diện)")
        self.lang_cb.pack(fill="x", padx=16, pady=(0, 6))

        self.debug_switch = ctk.CTkSwitch(
            left_card,
            text="Bật Debug Logs chi tiết",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#334155", "#cbd5e1"),
            progress_color="#0284c7"
        )
        self.debug_switch.pack(anchor="w", padx=16, pady=4)

        # Divider
        ctk.CTkFrame(left_card, height=1, fg_color=("#e2e8f0", "#1e293b")).pack(fill="x", padx=16, pady=16)

        # Bottom Stats Bar
        stats_frame = ctk.CTkFrame(left_card, fg_color="transparent")
        stats_frame.pack(side="bottom", fill="x", padx=16, pady=12)
        self.lbl_stats = ctk.CTkLabel(
            stats_frame,
            text="Đã chạy: 0 vòng  •  Thành công: 0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8")
        )
        self.lbl_stats.pack(anchor="w")

        # ========================================================
        # CỘT PHẢI: LIVE CONSOLE TERMINAL
        # ========================================================
        right_panel = ctk.CTkFrame(
            body,
            fg_color=("#ffffff", "#0e131f"),
            corner_radius=12,
            border_width=1,
            border_color=("#e2e8f0", "#1e293b")
        )
        right_panel.pack(side="right", fill="both", expand=True)

        # Toolbar Terminal
        toolbar = ctk.CTkFrame(right_panel, fg_color=("#f1f5f9", "#141c2e"), height=46, corner_radius=10)
        toolbar.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            toolbar,
            text="LIVE LOG STREAM",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color=("#0284c7", "#38bdf8")
        ).pack(side="left", padx=14)

        btn_clear = ctk.CTkButton(
            toolbar,
            text="Xoá log",
            command=self.clear_logs,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#e2e8f0", "#1e293b"),
            hover_color=("#cbd5e1", "#334155"),
            text_color=("#1e293b", "#e2e8f0"),
            width=76,
            height=28,
            corner_radius=6
        )
        btn_clear.pack(side="right", padx=(6, 12), pady=6)

        self.autoscroll_switch = ctk.CTkSwitch(
            toolbar,
            text="Tự cuộn (Auto-scroll)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
            progress_color="#0284c7"
        )
        self.autoscroll_switch.select()
        self.autoscroll_switch.pack(side="right", padx=10)

        ctk.CTkLabel(
            toolbar,
            text="Lọc:",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8")
        ).pack(side="right", padx=(8, 4))

        self.log_filter_cb = ctk.CTkComboBox(
            toolbar,
            values=["TẤT CẢ", "INFO", "WARN", "ERROR", "DEBUG"],
            fg_color=("#ffffff", "#0a0e17"),
            border_color=("#cbd5e1", "#334155"),
            dropdown_fg_color=("#ffffff", "#1e293b"),
            text_color=("#0f172a", "#f8fafc"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            dropdown_font=ctk.CTkFont(family="Segoe UI", size=11),
            width=96,
            height=28,
            state="readonly",
            command=lambda v: self._refresh_filtered_logs()
        )
        self.log_filter_cb.set("TẤT CẢ")
        self.log_filter_cb.pack(side="right", padx=(0, 6))

        # Khung Text Terminal
        self.log_box_frame = ctk.CTkFrame(
            right_panel,
            fg_color=("#f8fafc", "#070a10"),
            corner_radius=8,
            border_width=1,
            border_color=("#e2e8f0", "#162033")
        )
        self.log_box_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        scroll_y = tk.Scrollbar(self.log_box_frame)
        scroll_y.pack(side="right", fill="y", padx=(0, 4), pady=4)

        self.txt_log = tk.Text(
            self.log_box_frame,
            font=("Consolas", 11),
            wrap="word",
            yscrollcommand=scroll_y.set,
            relief="flat",
            padx=14,
            pady=12,
            insertbackground="#0284c7"
        )
        self.txt_log.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scroll_y.config(command=self.txt_log.yview)

        # Footer Status Counter
        footer = ctk.CTkFrame(right_panel, fg_color="transparent", height=26)
        footer.pack(fill="x", padx=14, pady=(0, 8))
        self.lbl_log_count = ctk.CTkLabel(
            footer,
            text="Tổng: 0 dòng log  •  Bộ đệm hoạt động",
            font=ctk.CTkFont(family="Consolas", size=11),
            text_color=("#64748b", "#94a3b8")
        )
        self.lbl_log_count.pack(side="left")

    def _on_theme_toggle(self):
        """Bật tắt chuyển đổi giữa Light Mode và Dark Mode."""
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self._apply_terminal_theme("Dark")
        else:
            ctk.set_appearance_mode("Light")
            self._apply_terminal_theme("Light")

    def _apply_terminal_theme(self, mode: str):
        """Đổi màu sắc của ô Text Terminal thuần Tkinter tương ứng với mode."""
        if mode == "Dark":
            bg_color = "#070a10"
            fg_color = "#f8fafc"
            select_bg = "#1e293b"
            info_color = "#10b981"
            warn_color = "#f59e0b"
            error_color = "#ef4444"
            debug_color = "#38bdf8"
        else:
            # Light theme
            bg_color = "#ffffff"
            fg_color = "#1e293b"
            select_bg = "#e2e8f0"
            info_color = "#059669"
            warn_color = "#d97706"
            error_color = "#dc2626"
            debug_color = "#0284c7"

        self.txt_log.configure(
            bg=bg_color,
            fg=fg_color,
            selectbackground=select_bg,
            selectforeground=fg_color
        )
        self.txt_log.tag_config("INFO", foreground=info_color)
        self.txt_log.tag_config("WARN", foreground=warn_color)
        self.txt_log.tag_config("WARNING", foreground=warn_color)
        self.txt_log.tag_config("ERROR", foreground=error_color)
        self.txt_log.tag_config("CRITICAL", foreground=error_color)
        self.txt_log.tag_config("DEBUG", foreground=debug_color)

    def _setup_logging(self):
        queue_handler = QueueLogHandler(self.log_queue)
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s", "%H:%M:%S")
        queue_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(queue_handler)

        logging.getLogger("GameBot.Core").addHandler(queue_handler)
        logging.getLogger("GameBot.Capture").addHandler(queue_handler)
        logging.getLogger("GameBot.Vision").addHandler(queue_handler)

    def _append_log_line(self, level: str, msg: str):
        self.all_logs.append((level, msg))
        flt = self.log_filter_cb.get()
        if flt != "TẤT CẢ" and level != flt:
            return

        self.txt_log.insert(tk.END, msg + "\n", level)
        if self.autoscroll_switch.get():
            self.txt_log.see(tk.END)

        self.lbl_log_count.configure(text=f"Tổng: {len(self.all_logs)} dòng log  •  Bộ đệm hoạt động")

    def _refresh_filtered_logs(self):
        self.txt_log.delete("1.0", tk.END)
        flt = self.log_filter_cb.get()
        for level, msg in self.all_logs:
            if flt == "TẤT CẢ" or level == flt:
                self.txt_log.insert(tk.END, msg + "\n", level)
        if self.autoscroll_switch.get():
            self.txt_log.see(tk.END)

    def _process_log_queue(self):
        while not self.log_queue.empty():
            try:
                level, msg = self.log_queue.get_nowait()
                self._append_log_line(level, msg)
            except queue.Empty:
                break

        if self.bot_instance:
            self.lbl_stats.configure(
                text=f"Đã chạy: {self.bot_instance.cycle_count} vòng  •  Thành công: {self.bot_instance.success_count}"
            )

        self.after(60, self._process_log_queue)

    def clear_logs(self):
        self.all_logs.clear()
        self.txt_log.delete("1.0", tk.END)
        self.lbl_log_count.configure(text="Tổng: 0 dòng log  •  Bộ đệm hoạt động")

    def start_task(self):
        if self.is_running:
            return

        mode = self.mode_var.get()
        feature_labels = {
            "chan_le": "Chạy Chẵn Lẻ (Even / Odd)",
            "quay_tuong_nha_rua": "Quay Tướng Nhà Rùa",
            "cuop_heo": "Chạy Cướp Heo",
            "vo_cong": "Chạy Võ Công",
            "chay_ai": "Chạy Ải (Auto Campaign)",
        }

        # Nếu chọn tính năng khác Chẵn Lẻ thì hiện thông báo popup
        if mode != "chan_le":
            feature_name = feature_labels.get(mode, mode)
            messagebox.showinfo(
                "Thông Báo Tính Năng",
                f"Tính năng [{feature_name}] hiện đang trong quá trình phát triển!\n\nVui lòng sử dụng tính năng 'Chạy Chẵn Lẻ' hoặc quay lại ở bản cập nhật tiếp theo."
            )
            return

        # Cấu hình
        serial = self.serial_entry.get().strip()
        config.device_serial = serial if serial else None

        strategy_raw = self.strategy_cb.get()
        if "even" in strategy_raw:
            config.even_odd_strategy = "even"
        elif "odd" in strategy_raw:
            config.even_odd_strategy = "odd"
        else:
            config.even_odd_strategy = "random"

        # Phục Tùng C & D và Ngôn ngữ
        config.enable_phuc_tung = (self.phuc_tung_switch.get() == 1)
        lang_raw = self.lang_cb.get()
        if "vi" in lang_raw:
            config.game_language = "vi"
        elif "en" in lang_raw:
            config.game_language = "en"
        else:
            config.game_language = "auto"

        log_level = logging.DEBUG if self.debug_switch.get() else logging.INFO
        logging.getLogger().setLevel(log_level)

        self.stop_event.clear()
        self.is_running = True

        self.status_badge.configure(
            text="● ĐANG CHẠY (RUNNING)",
            text_color="#059669" if self.theme_switch.get() == 0 else "#34d399",
            fg_color="#d1fae5" if self.theme_switch.get() == 0 else "#065f46"
        )
        self.btn_run.configure(state="disabled", fg_color=("#e2e8f0", "#1e293b"), text_color=("#94a3b8", "#64748b"))
        self.btn_stop.configure(state="normal", fg_color="#dc2626", text_color="#ffffff")

        self.worker_thread = threading.Thread(target=self._run_worker, daemon=True)
        self.worker_thread.start()

    def _run_worker(self):
        logging.info("🚀 Bắt đầu tính năng: [Chạy Chẵn Lẻ (Even / Odd)]")
        self.bot_instance = GameBot(cfg=config)

        try:
            self.bot_instance.start()
            logging.info("[Chẵn Lẻ] Vòng lặp tự động bắt đầu...")
            while not self.stop_event.is_set():
                self.bot_instance.run_one_cycle()
        except Exception as e:
            logging.error(f"Lỗi trong quá trình chạy: {e}", exc_info=True)
        finally:
            if self.bot_instance:
                self.bot_instance.stop()
            self._on_worker_finished()

    def _on_worker_finished(self):
        def _update():
            self.is_running = False
            self.status_badge.configure(
                text="● ĐÃ DỪNG (STOPPED)",
                text_color="#dc2626" if self.theme_switch.get() == 0 else "#f87171",
                fg_color="#fee2e2" if self.theme_switch.get() == 0 else "#450a0a"
            )
            self.btn_run.configure(state="normal", fg_color="#059669", text_color="#ffffff")
            self.btn_stop.configure(state="disabled", fg_color=("#cbd5e1", "#334155"), text_color=("#64748b", "#94a3b8"))
            logging.info("Tác vụ đã dừng lại.")
        self.after(0, _update)

    def stop_task(self):
        if not self.is_running:
            return
        logging.info("🛑 Đang gửi tín hiệu dừng tới bot...")
        self.stop_event.set()
        if self.bot_instance:
            self.bot_instance.stop()


def main():
    app = ModernBotApp()
    app.mainloop()


if __name__ == "__main__":
    main()
