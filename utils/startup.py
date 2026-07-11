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
        app_path = sys.executable
    else:
        app_path = os.path.abspath(sys.argv[0])
        
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        # Open HKEY_CURRENT_USER run key
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            # Wrap path in quotes to support spaces in file paths correctly
            winreg.SetValueEx(key, "Ticky", 0, winreg.REG_SZ, f'"{app_path}"')
        else:
            try:
                winreg.DeleteValue(key, "Ticky")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Error modifying Windows startup registry: {e}", file=sys.stderr)
        sys.stderr.flush()
