"""
Package core: Chứa toàn bộ core engine của GameBot (Bot State Machine, Capture, Vision, Config, Coordinates).
"""
from .config import BotConfig, Rect, config
from .capture import FastCapture
from .vision import VisionEngine, MatchResult
from .bot import GameBot
from .coordinates import CoordinateManager, coords

__all__ = [
    "BotConfig",
    "Rect",
    "config",
    "FastCapture",
    "VisionEngine",
    "MatchResult",
    "GameBot",
    "CoordinateManager",
    "coords",
]
