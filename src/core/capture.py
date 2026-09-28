"""
Module FastCapture: Quản lý chụp màn hình tốc độ cao và gửi input tap.
Tự động tìm kiếm file adb.exe từ adbutils hoặc từ thư mục cài đặt MuMu / LDPlayer nếu chưa có trong PATH.
"""
import logging
from pathlib import Path
import random
import shutil
import subprocess
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("GameBot.Capture")


def find_adb_executable() -> str:
    """Tự động tìm đường dẫn tới file adb.exe."""
    # 1. Kiểm tra PATH hệ thống
    adb_in_path = shutil.which("adb")
    if adb_in_path:
        return adb_in_path

    # 2. Kiểm tra từ thư viện adbutils (luôn có sẵn khi cài pip install adbutils)
    try:
        import adbutils
        p = adbutils.adb_path()
        if p and Path(p).exists():
            return str(p)
    except Exception:
        pass

    # 3. Quét các thư mục cài đặt phổ biến của MuMu Player và LDPlayer trên Windows
    candidate_paths = [
        r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
        r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\adb.exe",
        r"C:\Program Files (x86)\Netease\MuMuPlayer-12.0\shell\adb.exe",
        r"D:\Program Files\Netease\MuMuPlayer-12.0\shell\adb.exe",
        r"D:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\adb.exe",
        r"C:\Program Files\Netease\MuMu\emulator\nemu\vmonitor\bin\adb_server.exe",
        r"C:\LDPlayer\LDPlayer9\adb.exe",
        r"D:\LDPlayer\LDPlayer9\adb.exe",
        r"C:\Program Files\LDPlayer\LDPlayer9\adb.exe",
        r"D:\Program Files\LDPlayer\LDPlayer9\adb.exe",
    ]
    for p in candidate_paths:
        if Path(p).exists():
            return p

    return "adb"  # Mặc định gọi adb


class FastCapture:
    def __init__(self, device_serial: Optional[str] = None, max_fps: int = 30, bitrate: int = 8000000):
        self.device_serial = device_serial
        self.max_fps = max_fps
        self.bitrate = bitrate
        self.adb_bin = find_adb_executable()
        self._running = False

    def _run_adb(self, args: List[str], timeout: float = 3.0) -> subprocess.CompletedProcess:
        """Chạy lệnh adb an toàn với executable đã xác định."""
        cmd = [self.adb_bin]
        if self.device_serial and args and args[0] not in ("devices", "connect", "start-server", "kill-server"):
            cmd.extend(["-s", self.device_serial])
        cmd.extend(args)
        return subprocess.run(cmd, capture_output=True, timeout=timeout)

    def _get_connected_devices(self) -> List[str]:
        """Lấy danh sách thiết bị ADB đang ở trạng thái 'device'."""
        try:
            res = self._run_adb(["devices"], timeout=2.5)
            if res.returncode != 0:
                return []
            lines = [l.strip() for l in res.stdout.decode("utf-8", errors="ignore").split("\n")[1:] if l.strip()]
            devices = [l.split()[0] for l in lines if "\tdevice" in l]
            return devices
        except Exception:
            return []

    def start(self):
        """Khởi tạo kết nối tới MuMu Player / LDPlayer."""
        logger.info(f"Đang sử dụng ADB tại: '{self.adb_bin}'")
        logger.info(f"Đang tìm kiếm thiết bị Android ({self.device_serial or 'Tự động kết nối'})...")

        devices = self._get_connected_devices()

        if not devices:
            # Tự động kết nối các cổng của MuMu 12 (16384, 16416), MuMu 6 (7555), LDPlayer (5555)
            common_ports = [16384, 7555, 16416, 5555, 5554, 22471]
            for port in common_ports:
                addr = f"127.0.0.1:{port}"
                try:
                    logger.debug(f"Thử kết nối: {self.adb_bin} connect {addr}...")
                    self._run_adb(["connect", addr], timeout=1.5)
                except Exception:
                    pass
            
            devices = self._get_connected_devices()

        if self.device_serial and self.device_serial in devices:
            logger.info(f"✅ Đã kết nối thiết bị: {self.device_serial}")
        elif devices:
            self.device_serial = devices[0]
            logger.info(f"✅ Đã tự động chọn thiết bị: {self.device_serial}")
        else:
            logger.error("❌ Không tìm thấy thiết bị Android nào!")
            logger.error("👉 Hãy đảm bảo MuMu Player đang bật, và kiểm tra tính năng ADB trong Cài đặt MuMu.")

        self._running = True

    def get_latest_frame(self, timeout: float = 3.5) -> Optional[np.ndarray]:
        """Chụp màn hình qua adb exec-out screencap -p."""
        if not self._running:
            self.start()

        try:
            cmd = [self.adb_bin]
            if self.device_serial:
                cmd.extend(["-s", self.device_serial])
            cmd.extend(["exec-out", "screencap", "-p"])

            res = subprocess.run(cmd, capture_output=True, timeout=timeout)
            if res.returncode == 0 and res.stdout:
                img_array = np.frombuffer(res.stdout, dtype=np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                if frame is not None:
                    return frame
        except Exception as e:
            logger.debug(f"Frame capture retry: {e}")

        return None

    def tap(self, x: int, y: int, jitter_px: int = 4):
        """Tap tại điểm (x, y) kèm jitter nhẹ."""
        if jitter_px > 0:
            x += random.randint(-jitter_px, jitter_px)
            y += random.randint(-jitter_px, jitter_px)

        x = max(0, x)
        y = max(0, y)

        try:
            self._run_adb(["shell", "input", "tap", str(x), str(y)], timeout=2.0)
        except Exception as e:
            logger.error(f"Lỗi tap: {e}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3):
        """Vuốt cuộn màn hình."""
        duration_ms = int(duration * 1000)
        try:
            self._run_adb(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)], timeout=3.0)
        except Exception as e:
            logger.error(f"Lỗi swipe: {e}")

    def stop(self):
        """Dừng kết nối."""
        self._running = False
        logger.info("FastCapture đã dừng.")
