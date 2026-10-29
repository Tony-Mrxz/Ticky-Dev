# utils/app_indexer.py
"""Thread-safe system-wide application indexer and launcher for Windows.

The Start Menu scan happens on a background thread and is started when the
singleton is first requested, so the UI never blocks on indexing. UWP apps are
added later without blocking. Search uses the Flow Launcher-style matcher in
utils.app_search.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading

from utils.app_search import match_application, normalize_query

JUNK_KEYWORDS = (
    "uninstall",
    "uninst",
    "help",
    "readme",
    "documentation",
    "manual",
    "website",
    "license",
    "release notes",
)

SYSTEM_TOOLS = (
    ("Calculator", ("System32", "calc.exe")),
    ("Notepad", ("System32", "notepad.exe")),
    ("Command Prompt", ("System32", "cmd.exe")),
    ("Windows PowerShell", ("System32", "WindowsPowerShell", "v1.0", "powershell.exe")),
    ("Paint", ("System32", "mspaint.exe")),
    ("Task Manager", ("System32", "taskmgr.exe")),
    ("Control Panel", ("System32", "control.exe")),
    ("File Explorer", ("explorer.exe",)),
    ("Registry Editor", ("regedit.exe",)),
    ("Snipping Tool", ("System32", "SnippingTool.exe")),
    ("Device Manager", ("System32", "devmgmt.msc")),
    ("Disk Cleanup", ("System32", "cleanmgr.exe")),
)

_EXECUTABLE_SUFFIXES = {".exe", ".msc", ".bat", ".cmd", ".com"}


class AppItem:
    """Represents an indexable system application."""

    def __init__(self, name: str, path: str = None, app_id: str = None, category: str = "Application"):
        self.name = name.strip()
        self.path = path
        self.app_id = app_id
        self.category = category
        self.name_fold = self.name.casefold()
        self.exe_stem = self._extract_exe_stem(path)
        self.exe_stem_fold = self.exe_stem.casefold() if self.exe_stem else ""
        if app_id:
            self.usage_key = f"uwp:{app_id.casefold()}"
        elif path:
            self.usage_key = f"path:{path.casefold()}"
        else:
            self.usage_key = f"name:{self.name_fold}"
        self.icon_key = self.usage_key

    def _extract_exe_stem(self, path: str | None) -> str | None:
        if not path:
            return None
        stem, suffix = os.path.splitext(os.path.basename(path))
        if suffix.casefold() not in _EXECUTABLE_SUFFIXES:
            return None
        if stem.casefold() == self.name_fold:
            return None
        return stem


class AppIndexer:
    """Singleton indexer that locates and searches system applications."""

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            instance = cls._instance
        instance.start()
        return instance

    def __init__(self):
        self._apps: list[AppItem] = []
        self._lock = threading.RLock()
        self._listeners = []
        self._started = False
        self._ready = False
        self._uwp_scanning = False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def start(self):
        with self._lock:
            if self._started:
                return
            self._started = True
        threading.Thread(
            target=self._initial_index,
            name="TickyAppIndexer",
            daemon=True,
        ).start()

    def add_listener(self, callback):
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def refresh(self):
        """Rebuild the local Start Menu/system-tool index synchronously."""
        apps_dict: dict[str, AppItem] = {}

        start_menu_dirs = [
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"), r"Microsoft\Windows\Start Menu\Programs"),
        ]

        for directory in start_menu_dirs:
            if not os.path.exists(directory):
                continue
            for root, _, files in os.walk(directory):
                for filename in files:
                    if not filename.lower().endswith(".lnk"):
                        continue
                    name = os.path.splitext(filename)[0].strip()
                    lowered = name.casefold()
                    if not name or any(keyword in lowered for keyword in JUNK_KEYWORDS):
                        continue
                    if lowered in apps_dict:
                        continue
                    apps_dict[lowered] = AppItem(
                        name=name,
                        path=os.path.join(root, filename),
                        category="Application",
                    )

        windir = os.environ.get("WINDIR", r"C:\Windows")
        for name, relative_parts in SYSTEM_TOOLS:
            tool_path = os.path.join(windir, *relative_parts)
            if os.path.exists(tool_path):
                apps_dict[name.casefold()] = AppItem(
                    name=name,
                    path=tool_path,
                    category="System Software",
                )

        with self._lock:
            existing_uwp = [
                app
                for app in self._apps
                if app.app_id and app.name_fold not in apps_dict
            ]
            self._apps = sorted(
                [*apps_dict.values(), *existing_uwp],
                key=lambda app: app.name_fold,
            )

    def _initial_index(self):
        try:
            self.refresh()
        except Exception as error:
            print(f"[AppIndexer] Initial index failed: {error}")
        finally:
            with self._lock:
                self._ready = True
            self._notify_listeners()
            self._start_uwp_scan()

    def _start_uwp_scan(self):
        if sys.platform != "win32":
            return
        with self._lock:
            if self._uwp_scanning:
                return
            self._uwp_scanning = True
        threading.Thread(
            target=self._scan_uwp_apps,
            name="TickyUwpScan",
            daemon=True,
        ).start()

    def _scan_uwp_apps(self):
        try:
            command = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Compress",
            ]
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=12,
                creationflags=creationflags,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return

            raw_data = json.loads(result.stdout)
            if isinstance(raw_data, dict):
                raw_data = [raw_data]

            new_apps: list[AppItem] = []
            with self._lock:
                known_names = {app.name_fold for app in self._apps}
                known_ids = {app.app_id for app in self._apps if app.app_id}

            for item in raw_data:
                name = str(item.get("Name", "")).strip()
                app_id = str(item.get("AppID", "")).strip()
                if not name or not app_id:
                    continue
                lowered = name.casefold()
                if lowered in known_names or app_id in known_ids:
                    continue
                if any(keyword in lowered for keyword in JUNK_KEYWORDS):
                    continue
                category = "Windows App" if "!" in app_id else "Application"
                new_apps.append(AppItem(name=name, app_id=app_id, category=category))
                known_names.add(lowered)
                known_ids.add(app_id)

            if new_apps:
                with self._lock:
                    self._apps = sorted(
                        [*self._apps, *new_apps],
                        key=lambda app: app.name_fold,
                    )
                self._notify_listeners()
        except Exception:
            pass
        finally:
            with self._lock:
                self._uwp_scanning = False

    def _notify_listeners(self):
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener()
            except RuntimeError:
                pass
            except Exception as error:
                print(f"[AppIndexer] Index listener failed: {error}")

    def search(self, query: str, limit: int = 40, usage=None) -> list[AppItem]:
        """Return matches ranked by match score plus learned usage boost."""
        normalized = normalize_query(query)
        if not normalized:
            return []

        with self._lock:
            apps = tuple(self._apps)

        scored = []
        for app in apps:
            match = match_application(normalized, app.name, app.exe_stem)
            if match is None:
                continue
            score = match.score
            if usage is not None:
                score += usage.boost(normalized, app.usage_key)
            scored.append((score, match.tier, app.name_fold, app))

        scored.sort(key=lambda entry: (-entry[0], -entry[1], entry[2]))
        return [entry[3] for entry in scored[:limit]]

    def launch(self, app: AppItem) -> bool:
        """Launch the application."""
        if not app:
            return False

        try:
            if app.path and os.path.exists(app.path):
                os.startfile(app.path)
                return True
            if app.app_id:
                try:
                    os.startfile(f"shell:AppsFolder\\{app.app_id}")
                    return True
                except Exception:
                    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app.app_id}"])
                    return True
            if app.path:
                os.startfile(app.path)
                return True
        except Exception as error:
            print(f"[AppIndexer] Error launching {app.name}: {error}")
            try:
                if app.path:
                    subprocess.Popen(["cmd.exe", "/c", "start", "", app.path], shell=True)
                    return True
            except Exception:
                pass
        return False
