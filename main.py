"""
Entrypoint chính điều khiển GameBot tự động hoá.
Hỗ trợ chạy test từng state riêng lẻ hoặc chạy vòng lặp vô hạn.
"""
import argparse
from datetime import datetime
import logging
import sys
import time

# Đảm bảo hiển thị Tiếng Việt trên Windows console không bị lỗi cp1252 charmap
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from src.core.bot import GameBot
    from src.core.config import LOGS_DIR, config
except ImportError:
    from bot import GameBot
    from config import LOGS_DIR, config


def setup_logging(debug: bool = False):
    """Cấu hình ghi log ra console và file log."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
    date_format = "%H:%M:%S"

    log_filename = LOGS_DIR / f"bot_{datetime.now().strftime('%Y%m%d')}.log"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_filename), encoding="utf-8"),
    ]

    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers,
    )


def test_capture_speed(bot: GameBot, frames_to_test: int = 50):
    """Kiểm tra tốc độ chụp khung hình và FPS."""
    print(f"\n--- Đang test tốc độ chụp {frames_to_test} frames qua Scrcpy Stream ---")
    bot.start()
    latencies = []
    try:
        for i in range(frames_to_test):
            t0 = time.perf_counter()
            frame = bot.capture.get_latest_frame(timeout=2.0)
            t1 = time.perf_counter()
            if frame is not None:
                latencies.append((t1 - t0) * 1000)
            time.sleep(0.01)

        avg_ms = sum(latencies) / len(latencies) if latencies else 0
        min_ms = min(latencies) if latencies else 0
        max_ms = max(latencies) if latencies else 0
        print(f"✅ Kết quả Capture: Trung bình: {avg_ms:.2f}ms | Nhanh nhất: {min_ms:.2f}ms | Chậm nhất: {max_ms:.2f}ms")
        if avg_ms < 50:
            print("🚀 Tốc độ đạt yêu cầu chuẩn <50ms!")
        else:
            print("⚠️ Tốc độ chậm hơn kỳ vọng (có thể do đang chạy chế độ ADB fallback).")
    finally:
        bot.stop()


def test_single_state(bot: GameBot, state_name: str):
    """Chạy thử nghiệm một state cụ thể để kiểm tra tính chính xác."""
    print(f"\n--- Đang chạy thử nghiệm state: {state_name.upper()} ---")
    bot.start()
    time.sleep(1.0)  # Chờ luồng ổn định
    try:
        state_map = {
            "vip7": lambda: bot.enter_vip_section("vip7"),
            "vip9": lambda: bot.enter_vip_section("vip9"),
            "diamond_vip7": lambda: bot.process_vip_section("vip7"),
            "diamond_vip9": lambda: bot.process_vip_section("vip9"),
            "even_odd": bot.choose_even_odd,
            "popup": bot.wait_and_handle_reward_popup,
            "reset": bot.reset_cycle,
        }

        if state_name not in state_map:
            print(f"❌ State không hợp lệ! Danh sách hợp lệ: {list(state_map.keys())}")
            return

        func = state_map[state_name]
        t0 = time.perf_counter()
        result = func()
        duration_ms = (time.perf_counter() - t0) * 1000
        print(f"👉 Kết quả: {'THÀNH CÔNG' if result else 'THẤT BẠI'} (Thời gian thực thi: {duration_ms:.1f}ms)")
    finally:
        bot.stop()


def main():
    parser = argparse.ArgumentParser(description="Bot tự động hoá game Android trên LDPlayer")
    parser.add_argument(
        "--mode", "-m",
        choices=["run", "test-cycle", "test-state", "test-capture"],
        default="run",
        help="Chế độ chạy: run (vô hạn), test-cycle (1 vòng), test-state (1 bước), test-capture (đo FPS)"
    )
    parser.add_argument(
        "--state", "-s",
        type=str,
        help="Tên state khi dùng mode test-state (vip7, diamond_vip7, even_odd, claim, vip9, diamond_vip9, reset)"
    )
    parser.add_argument("--serial", type=str, help="ADB Serial của thiết bị (VD: 127.0.0.1:5555)")
    parser.add_argument("--strategy", choices=["random", "even", "odd"], default="even", help="Chiến lược Even/Odd (mặc định: even)")
    parser.add_argument("--debug", action="store_true", help="Bật log debug chi tiết")

    args = parser.parse_args()
    setup_logging(debug=args.debug)

    # Cập nhật config từ tham số dòng lệnh
    if args.serial:
        config.device_serial = args.serial
    if args.strategy:
        config.even_odd_strategy = args.strategy

    bot = GameBot(cfg=config)

    if args.mode == "test-capture":
        test_capture_speed(bot)
    elif args.mode == "test-state":
        if not args.state:
            print("❌ Vui lòng chỉ định state cần test qua cờ: --state <tên_state>")
            sys.exit(1)
        test_single_state(bot, args.state)
    elif args.mode == "test-cycle":
        bot.start()
        try:
            bot.run_one_cycle()
        finally:
            bot.stop()
    elif args.mode == "run":
        bot.start()
        bot.run_forever()


if __name__ == "__main__":
    main()
