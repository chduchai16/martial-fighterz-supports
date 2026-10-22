import sys
import time
from pathlib import Path
import cv2
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.core.capture import FastCapture
from src.core.config import config

def main():
    cap = FastCapture(device_serial=config.device_serial)
    cap.start()
    time.sleep(0.5)

    frame = cap.get_latest_frame(timeout=3.5)
    if frame is None:
        print("ERROR: Could not get frame!")
        return

    out_p = ROOT_DIR / "debug_crops" / "live_current_vip7.png"
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_p), frame)
    print(f"Captured live screen: {frame.shape[1]}x{frame.shape[0]} -> {out_p}")
    cap.stop()

if __name__ == "__main__":
    main()
