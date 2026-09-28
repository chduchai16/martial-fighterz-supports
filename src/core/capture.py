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
        self._shell_proc: Optional[subprocess.Popen] = None

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

    def _init_persistent_shell(self):
        """Khởi tạo một tiến trình ADB Shell duy nhất và duy trì xuyên suốt vòng đời bot."""
        if self._shell_proc is not None and self._shell_proc.poll() is None:
            return

        cmd = [self.adb_bin]
        if self.device_serial:
            cmd.extend(["-s", self.device_serial])
        cmd.extend(["shell"])

        try:
            self._shell_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                bufsize=0  # Không đệm, gửi dữ liệu đi ngay lập tức
            )
            logger.info("⚡ Đã kích hoạt kết nối Persistent ADB Shell xuyên suốt (Độ trễ tap < 5ms)!")
        except Exception as e:
            logger.warning(f"Không thể mở Persistent Shell ({e}), sẽ fallback về subprocess thường.")
            self._shell_proc = None

    def _send_shell_cmd(self, command: str):
        """Gửi lệnh trực tiếp vào pipe của Persistent Shell."""
        if self._shell_proc is None or self._shell_proc.poll() is not None:
            self._init_persistent_shell()

        if self._shell_proc and self._shell_proc.stdin:
            try:
                line = (command.strip() + "\n").encode("utf-8")
                self._shell_proc.stdin.write(line)
                self._shell_proc.stdin.flush()
                return
            except Exception as e:
                logger.debug(f"Lỗi gửi qua Persistent Shell: {e}, đang khởi tạo lại...")
                self._init_persistent_shell()

        # Fallback an toàn nếu persistent shell bị lỗi
        args = ["shell"] + command.split()
        self._run_adb(args, timeout=2.0)

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
        # Mở sẵn ống kết nối Persistent Shell ngay từ lúc start
        self._init_persistent_shell()

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
        """Tap tại điểm (x, y) qua Persistent Shell siêu tốc kèm jitter nhẹ."""
        if jitter_px > 0:
            x += random.randint(-jitter_px, jitter_px)
            y += random.randint(-jitter_px, jitter_px)

        x = max(0, x)
        y = max(0, y)

        self._send_shell_cmd(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3):
        """Vuốt cuộn màn hình qua Persistent Shell."""
        duration_ms = int(duration * 1000)
        self._send_shell_cmd(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    def stop(self):
        """Dừng kết nối và đóng Persistent Shell."""
        self._running = False
        if self._shell_proc:
            try:
                if self._shell_proc.stdin:
                    self._shell_proc.stdin.write(b"exit\n")
                    self._shell_proc.stdin.flush()
                self._shell_proc.terminate()
                self._shell_proc.wait(timeout=1.0)
            except Exception:
                try:
                    self._shell_proc.kill()
                except Exception:
                    pass
            self._shell_proc = None
        logger.info("FastCapture đã dừng và đóng Persistent Shell an toàn.")
