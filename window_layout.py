"""Fit CustomTkinter's logical client size inside the primary work area."""
from dataclasses import dataclass
import math
import os


@dataclass(frozen=True)
class WindowLayout:
    width: int
    height: int
    x: int
    y: int
    compact: bool


def fit_window(work_area, scale=1.0, frame=(20, 44)):
    left, top, right, bottom = work_area
    available_width = max(1, right - left - 24 - frame[0])
    available_height = max(1, bottom - top - 24 - frame[1])
    width = min(1180, max(1, math.floor(available_width / scale)))
    height = min(820, max(1, math.floor(available_height / scale)))
    x = left + max(0, (right - left - round(width * scale) - frame[0]) // 2)
    y = top + max(0, (bottom - top - round(height * scale) - frame[1]) // 2)
    return WindowLayout(width, height, x, y, width < 1050 or height < 740)


def screen_work_area(window):
    """Windows primary desktop excludes taskbar, including top/left taskbars."""
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        area = wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):
            return area.left, area.top, area.right, area.bottom
    return 0, 0, window.winfo_screenwidth(), window.winfo_screenheight()
