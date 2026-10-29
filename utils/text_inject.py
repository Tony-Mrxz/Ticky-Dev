"""
Windows system-wide text injection helpers for Ticky voice dictation.

Uses SendInput with KEYEVENTF_UNICODE so text is inserted at the active
caret of the foreground application without replacing the entire field.
"""

from __future__ import annotations

import sys
import time
from typing import Optional

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_UNICODE = 0x0004
    KEYEVENTF_SCANCODE = 0x0008
    VK_BACK = 0x08
    VK_CONTROL = 0x11
    VK_V = 0x56

    ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class _INPUT(ctypes.Union):
        _fields_ = [
            ("mi", MOUSEINPUT),
            ("ki", KEYBDINPUT),
            ("hi", HARDWAREINPUT),
        ]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("_input",)
        _fields_ = [
            ("type", wintypes.DWORD),
            ("_input", _INPUT),
        ]

    SendInput = user32.SendInput
    SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
    SendInput.restype = wintypes.UINT

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.SetForegroundWindow.argtypes = (wintypes.HWND,)
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = (wintypes.HWND,)
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.SetFocus.argtypes = (wintypes.HWND,)
    user32.SetFocus.restype = wintypes.HWND
    user32.AttachThreadInput.argtypes = (wintypes.DWORD, wintypes.DWORD, wintypes.BOOL)
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.DWORD))
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
else:
    user32 = None
    kernel32 = None
    INPUT = None  # type: ignore


def _is_windows() -> bool:
    return sys.platform == "win32" and user32 is not None


def get_foreground_hwnd() -> Optional[int]:
    if not _is_windows():
        return None
    hwnd = user32.GetForegroundWindow()
    return int(hwnd) if hwnd else None


def focus_hwnd(hwnd: Optional[int]) -> bool:
    """Robustly restore foreground focus to the target window."""
    if not _is_windows() or not hwnd:
        return False
    try:
        if not user32.IsWindow(hwnd):
            return False

        fg_hwnd = user32.GetForegroundWindow()
        if fg_hwnd == hwnd:
            return True

        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None)
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)
        current_thread = kernel32.GetCurrentThreadId()

        attached_fg = False
        attached_target = False

        if fg_thread and fg_thread != current_thread:
            user32.AttachThreadInput(current_thread, fg_thread, True)
            attached_fg = True

        if target_thread and target_thread != current_thread:
            user32.AttachThreadInput(current_thread, target_thread, True)
            attached_target = True

        user32.SetForegroundWindow(hwnd)
        user32.BringWindowToTop(hwnd)
        user32.SetFocus(hwnd)

        if attached_fg:
            user32.AttachThreadInput(current_thread, fg_thread, False)
        if attached_target:
            user32.AttachThreadInput(current_thread, target_thread, False)

        time.sleep(0.015)
        return True
    except Exception:
        pass
    return False


def _send_inputs(inputs) -> bool:
    if not inputs:
        return True
    arr = (INPUT * len(inputs))(*inputs)
    sent = SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    return sent == len(inputs)


def _unicode_key_events(ch: str):
    code = ord(ch)
    # SendInput Unicode uses UTF-16 code units
    if code > 0xFFFF:
        # Surrogate pair
        code -= 0x10000
        high = 0xD800 + ((code >> 10) & 0x3FF)
        low = 0xDC00 + (code & 0x3FF)
        units = (high, low)
    else:
        units = (code,)

    events = []
    for unit in units:
        down = INPUT()
        down.type = INPUT_KEYBOARD
        down.ki = KEYBDINPUT(0, unit, KEYEVENTF_UNICODE, 0, 0)
        up = INPUT()
        up.type = INPUT_KEYBOARD
        up.ki = KEYBDINPUT(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, 0)
        events.extend((down, up))
    return events


def _vk_key_events(vk: int, key_up: bool = False):
    flags = KEYEVENTF_KEYUP if key_up else 0
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(vk, 0, flags, 0, 0)
    return inp


def inject_text(text: str, target_hwnd: Optional[int] = None) -> bool:
    """
    Insert `text` at the caret of the focused (or restored) window.
    Returns True if SendInput reported success.
    """
    if not text:
        return True
    if not _is_windows():
        return False

    if target_hwnd:
        focus_hwnd(target_hwnd)

    batch = []
    for ch in text:
        if ch == "\r":
            continue
        if ch == "\n":
            # Enter key for newline
            batch.append(_vk_key_events(0x0D, False))
            batch.append(_vk_key_events(0x0D, True))
        else:
            batch.extend(_unicode_key_events(ch))

        # Flush periodically to avoid oversized SendInput buffers
        if len(batch) >= 200:
            if not _send_inputs(batch):
                return False
            batch = []

    return _send_inputs(batch)


def inject_backspaces(count: int, target_hwnd: Optional[int] = None) -> bool:
    """Delete `count` characters before the caret via Backspace."""
    if count <= 0:
        return True
    if not _is_windows():
        return False

    if target_hwnd:
        focus_hwnd(target_hwnd)

    batch = []
    for _ in range(count):
        batch.append(_vk_key_events(VK_BACK, False))
        batch.append(_vk_key_events(VK_BACK, True))
        if len(batch) >= 200:
            if not _send_inputs(batch):
                return False
            batch = []
    return _send_inputs(batch)


def inject_text_via_clipboard(text: str, target_hwnd: Optional[int] = None) -> bool:
    """
    Fallback: paste via clipboard + Ctrl+V, restoring prior clipboard content.
    Prefer inject_text(); use only when Unicode SendInput fails for a target app.
    """
    if not text or not _is_windows():
        return False

    try:
        from PySide6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is None:
            return False
        previous = clipboard.text()
        clipboard.setText(text)

        if target_hwnd:
            focus_hwnd(target_hwnd)
            time.sleep(0.02)

        # Ctrl down, V down, V up, Ctrl up
        ok = _send_inputs([
            _vk_key_events(VK_CONTROL, False),
            _vk_key_events(VK_V, False),
            _vk_key_events(VK_V, True),
            _vk_key_events(VK_CONTROL, True),
        ])
        time.sleep(0.05)
        clipboard.setText(previous or "")
        return ok
    except Exception:
        return False
