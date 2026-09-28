"""
Launcher khởi chạy giao diện Desktop Windows điều khiển GameBot.
Entrypoint trỏ tới src/ui/gui_app.py
"""
import sys
from pathlib import Path

# Thêm root vào sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ui.gui_app import main

if __name__ == "__main__":
    main()
