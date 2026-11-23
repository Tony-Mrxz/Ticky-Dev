# utils/screen_time.py
"""Per-app foreground time, bucketed by day and persisted locally.

Samples the window manager rather than hooking input, so a sample is credited to
whatever app actually owns the screen; idle stretches are dropped so walking away
does not inflate the busiest app of the day.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import date, timedelta

from PySide6.QtCore import QObject, QTimer

SCREEN_TIME_FILE = os.path.join(os.path.expanduser("~"), ".ticky_screen_time.json")

POLL_INTERVAL_MS = 5000
IDLE_AFTER_SECONDS = 60
DAYS_KEPT = 8
FLUSH_AFTER_SECONDS = 60

# Sessions the user is not really "in front of" a screen.
_IGNORED_PROCESSES = {
    "lockapp.exe",
    "logonui.exe",
    "searchui.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
}

_PRETTY_NAMES = {
    "chrome": "Chrome",
    "msedge": "Edge",
    "firefox": "Firefox",
    "brave": "Brave",
    "opera": "Opera",
    "code": "VS Code",
    "telegram": "Telegram",
    "discord": "Discord",
    "spotify": "Spotify",
    "obs64": "OBS",
    "taskmgr": "Task Manager",
    "explorer": "Explorer",
    "windowterminal": "Terminal",
    "wt": "Terminal",
    "powerpnt": "PowerPoint",
    "winword": "Word",
    "excel": "Excel",
    "outlook": "Outlook",
    "teams": "Teams",
    "zoom": "Zoom",
    "vlc": "VLC",
    "devenv": "Visual Studio",
}

_WORD_FIXES = {"mgr": "Manager", "app": "App", "exe": ""}

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    _user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    _kernel32.OpenProcess.restype = wintypes.HANDLE
    _kernel32.GetTickCount.restype = wintypes.DWORD
    _kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
    ]

    class _LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    _PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _foreground_process_name() -> str:
    """Basename of the executable owning the foreground window, or "" when unknown."""
    if not _IS_WINDOWS:
        return ""
    try:
        hwnd = _user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        handle = _kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            size = wintypes.DWORD(1024)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not _kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return ""
            return os.path.basename(buffer.value)
        finally:
            _kernel32.CloseHandle(handle)
    except Exception:
        return ""


def _idle_seconds() -> float:
    """Seconds since the last keyboard or mouse event."""
    if not _IS_WINDOWS:
        return 0.0
    try:
        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not _user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        # GetTickCount wraps every ~49 days, so compare through a 32-bit window.
        return ((_kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0
    except Exception:
        return 0.0


def display_name(process_name: str) -> str:
    """'chrome.exe' -> 'Chrome', 'Taskmgr.exe' -> 'Task Manager'."""
    stem = os.path.splitext(process_name or "")[0]
    if not stem:
        return ""
    if stem.lower() in _PRETTY_NAMES:
        return _PRETTY_NAMES[stem.lower()]
    words = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+", stem)
    if not words:
        return stem.capitalize()
    return " ".join(_WORD_FIXES.get(word.lower(), word.capitalize()) for word in words)


def _today_key() -> str:
    return date.today().isoformat()


class ScreenTimeService(QObject):
    """Singleton foreground-time collector; callers read the day buckets directly."""

    _instance: "ScreenTimeService | None" = None

    @classmethod
    def get_instance(cls) -> "ScreenTimeService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, path: str = SCREEN_TIME_FILE, parent=None):
        super().__init__(parent)
        self._path = path
        self._days: dict[str, dict[str, float]] = {}
        self._current: str | None = None
        self._sampled_at = 0.0
        self._dirty = False
        self._saved_at = 0.0
        self._own_name = os.path.basename(sys.argv[0] or "") if sys.argv else ""
        self._timer = QTimer(self)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._sample)
        self._load()

    # -- lifecycle ----------------------------------------------------------
    def start(self):
        if not self._timer.isActive():
            self._sampled_at = time.monotonic()
            self._timer.start()

    def stop(self):
        self._timer.stop()
        self._credit_current(flush_only=True)
        self._flush(force=True)

    # -- sampling -----------------------------------------------------------
    def _sample(self):
        now = time.monotonic()
        elapsed = now - self._sampled_at
        self._sampled_at = now
        if elapsed <= 0 or elapsed > POLL_INTERVAL_MS / 1000.0 * 4:
            # A suspended or stalled process must not hand out a huge block of time.
            self._current = None
            return

        if _idle_seconds() > IDLE_AFTER_SECONDS:
            self._current = None
            return

        name = _foreground_process_name().lower()
        if not name or name in _IGNORED_PROCESSES or name == self._own_name.lower():
            self._current = None
            return

        self._credit_current(elapsed)
        self._current = name

    def _credit_current(self, seconds: float = 0.0, flush_only: bool = False):
        if seconds > 0 and self._current:
            day = self._days.setdefault(_today_key(), {})
            day[self._current] = day.get(self._current, 0.0) + seconds
            self._dirty = True
        if flush_only or (self._dirty and time.monotonic() - self._saved_at >= FLUSH_AFTER_SECONDS):
            self._flush()

    # -- persistence --------------------------------------------------------
    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return
        days = data.get("days", {}) if isinstance(data, dict) else {}
        if not isinstance(days, dict):
            return
        for key, apps in days.items():
            if isinstance(apps, dict):
                self._days[str(key)] = {
                    str(app): float(seconds)
                    for app, seconds in apps.items()
                    if isinstance(seconds, (int, float))
                }
        self._prune()

    def _flush(self, force: bool = False):
        if not self._dirty and not force:
            return
        self._prune()
        temporary = self._path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump({"days": self._days}, handle, indent=2)
            os.replace(temporary, self._path)
            self._dirty = False
            self._saved_at = time.monotonic()
        except OSError:
            try:
                os.remove(temporary)
            except OSError:
                pass

    def _prune(self):
        cutoff = (date.today() - timedelta(days=DAYS_KEPT - 1)).isoformat()
        for key in [k for k in self._days if str(k) < cutoff]:
            del self._days[key]

    # -- queries ------------------------------------------------------------
    def seconds_on(self, day_key: str) -> float:
        return sum(self._days.get(day_key, {}).values())

    def today_seconds(self) -> float:
        return self.seconds_on(_today_key())

    def seconds_for_today(self, process_name: str) -> float:
        return self._days.get(_today_key(), {}).get(process_name.lower(), 0.0)

    def top_today(self, limit: int = 3) -> list[tuple[str, float]]:
        day = self._days.get(_today_key(), {})
        return sorted(day.items(), key=lambda item: item[1], reverse=True)[:limit]


def format_duration(seconds: float) -> str:
    """Compact '4h 12m' / '12m' / '48s' for glanceable blocks."""
    seconds = max(0, int(seconds or 0))
    hours, remainder = divmod(seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m"
    return f"{seconds}s"
