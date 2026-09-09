# utils/startup.py
"""Utility module to handle Windows startup registry settings."""

import os
import sys

def set_startup(enabled):
    """Enable or disable Ticky starting automatically on Windows login."""
    if sys.platform != 'win32':
        return
        
    import winreg
    
    if getattr(sys, 'frozen', False):
        # Compiled executable mode (PyInstaller EXE)
        cmd = f'"{sys.executable}"'
    else:
        # Python script mode (.py) - must include python interpreter
        script_path = os.path.abspath(sys.argv[0])
        cmd = f'"{sys.executable}" "{script_path}"'
        
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        # Open HKEY_CURRENT_USER Run key with write access
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enabled:
            winreg.SetValueEx(key, "Ticky", 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, "Ticky")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Error modifying Windows startup registry: {e}", file=sys.stderr)
        sys.stderr.flush()
