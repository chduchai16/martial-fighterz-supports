import os
import shutil
from pathlib import Path

debug_dir = Path("debug_crops")
keep_files = {
    "live_current_vip7.png",
    "coin_300k_full_preview.png",
    "input_zero_preview.png"
}

for item in debug_dir.iterdir():
    if item.is_dir():
        shutil.rmtree(item)
    elif item.name not in keep_files:
        item.unlink()

print("CLEANUP_DONE")
