# utils/window_capture.py
"""Native OS-level window capture exclusion utility for Windows."""

import sys
import ctypes

# Windows Display Affinity Constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011  # Windows 10 Version 2004 (Build 19041)+

def set_window_capture_exclusion(hwnd, exclude: bool) -> bool:
    """
    Apply or remove OS-level screen capture exclusion for a native window HWND.
    
    When exclude is True:
    - WDA_EXCLUDEFROMCAPTURE (0x00000011) instructs Windows Graphics Capture and DWM
      to exclude the window from screen/window captures while keeping it fully visible
      and interactive on the local monitor.
    - If WDA_EXCLUDEFROMCAPTURE fails (e.g. on older Windows versions), falls back to WDA_MONITOR (0x00000001).

    When exclude is False:
    - WDA_NONE (0x00000000) restores normal capturability.
    
    Returns True if the native API call succeeded, False otherwise.
    """
    if sys.platform != 'win32' or not hwnd:
        return False

    try:
        user32 = ctypes.windll.user32
        affinity = WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE
        hwnd_val = int(hwnd)

        result = user32.SetWindowDisplayAffinity(hwnd_val, affinity)
        if result == 0 and exclude:
            # Fallback to WDA_MONITOR if WDA_EXCLUDEFROMCAPTURE fails on older Windows builds
            result = user32.SetWindowDisplayAffinity(hwnd_val, WDA_MONITOR)

        return bool(result)
    except Exception as e:
        print(f"Failed to set window display affinity for HWND {hwnd}: {e}", file=sys.stderr)
        return False
