# utils/memreduct.py
"""
Mem Reduct auto-detection and trigger integration for Ticky hardware monitor.
Mem Reduct (by henrypp): https://github.com/henrypp/memreduct
CLI arguments:
    memreduct.exe /clean (or -clean)
"""

import os
import shutil
import subprocess
import threading
import winreg
import psutil

_MEMREDUCT_PATH_CACHE = None
_CACHE_LOCK = threading.Lock()

COMMON_MEMREDUCT_PATHS = [
    os.path.expandvars(r"%ProgramFiles%\Mem Reduct\memreduct.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Mem Reduct\memreduct.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Mem Reduct\memreduct.exe"),
    r"C:\Program Files\Mem Reduct\memreduct.exe",
    r"C:\Program Files (x86)\Mem Reduct\memreduct.exe",
]


def _find_in_registry() -> str | None:
    """Check Windows Uninstall registry keys for Mem Reduct installation."""
    reg_roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    for hkey, subkey in reg_roots:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                for i in range(num_subkeys):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as app_key:
                            try:
                                name, _ = winreg.QueryValueEx(app_key, "DisplayName")
                                if "mem reduct" in str(name).lower():
                                    # Try DisplayIcon or InstallLocation
                                    for val_name in ("DisplayIcon", "InstallLocation"):
                                        try:
                                            val, _ = winreg.QueryValueEx(app_key, val_name)
                                            val_clean = str(val).strip('"').strip()
                                            if val_clean.lower().endswith(".exe") and os.path.isfile(val_clean):
                                                return val_clean
                                            candidate = os.path.join(val_clean, "memreduct.exe")
                                            if os.path.isfile(candidate):
                                                return candidate
                                        except OSError:
                                            pass
                            except OSError:
                                pass
                    except OSError:
                        continue
        except OSError:
            continue
    return None


def find_memreduct_executable(force_refresh: bool = False) -> str | None:
    """Finds the memreduct.exe path on the system. Returns None if not found."""
    global _MEMREDUCT_PATH_CACHE
    with _CACHE_LOCK:
        if _MEMREDUCT_PATH_CACHE and not force_refresh:
            if os.path.isfile(_MEMREDUCT_PATH_CACHE):
                return _MEMREDUCT_PATH_CACHE
            _MEMREDUCT_PATH_CACHE = None

        # 1. Check running processes (detects running portable, custom, or tray instances)
        try:
            for p in psutil.process_iter(attrs=["name", "exe"]):
                name = p.info.get("name") or ""
                if name.lower() == "memreduct.exe":
                    exe_path = p.info.get("exe")
                    if exe_path and os.path.isfile(exe_path):
                        _MEMREDUCT_PATH_CACHE = exe_path
                        return exe_path
        except Exception:
            pass

        # 2. Check standard installation paths
        for path in COMMON_MEMREDUCT_PATHS:
            if os.path.isfile(path):
                _MEMREDUCT_PATH_CACHE = path
                return path

        # 3. Check Windows Registry
        reg_path = _find_in_registry()
        if reg_path and os.path.isfile(reg_path):
            _MEMREDUCT_PATH_CACHE = reg_path
            return reg_path

        # 4. Check system PATH
        which_path = shutil.which("memreduct.exe") or shutil.which("memreduct")
        if which_path and os.path.isfile(which_path):
            _MEMREDUCT_PATH_CACHE = which_path
            return which_path

        return None


def is_memreduct_available() -> bool:
    """Returns True if Mem Reduct is installed or currently running."""
    return find_memreduct_executable() is not None


def trigger_memreduct_clean(callback=None):
    """Executes 'memreduct.exe /clean' in a background thread."""
    def _run():
        exe = find_memreduct_executable()
        success = False
        if exe:
            try:
                flags = 0
                if os.name == "nt":
                    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
                # memreduct supports /clean or -clean
                subprocess.Popen([exe, "/clean"], creationflags=flags)
                success = True
            except Exception as e:
                print(f"[MemReduct] Error triggering clean: {e}")
        if callback:
            callback(success)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

