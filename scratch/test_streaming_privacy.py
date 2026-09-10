# scratch/test_streaming_privacy.py
"""Automated verification script for Ticky's 'Hide while streaming' feature."""

import os
import sys
import ctypes

# Add project root to sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PySide6.QtWidgets import QApplication, QWidget
from utils import config
from utils.window_capture import set_window_capture_exclusion, WDA_EXCLUDEFROMCAPTURE, WDA_NONE

def test_config_persistence():
    print("--- Testing Config Persistence ---")
    orig_state = config.load_hide_while_streaming()
    print(f"Original hide_while_streaming state: {orig_state}")
    
    # Save True
    config.save_hide_while_streaming(True)
    assert config.load_hide_while_streaming() is True, "Failed to save True state!"
    print("Successfully saved & verified True state.")
    
    # Save False
    config.save_hide_while_streaming(False)
    assert config.load_hide_while_streaming() is False, "Failed to save False state!"
    print("Successfully saved & verified False state.")
    
    # Restore original state
    config.save_hide_while_streaming(orig_state)
    print("Restored original state successfully.")

def test_window_affinity():
    print("\n--- Testing Native Window Affinity ---")
    app = QApplication.instance() or QApplication(sys.argv)
    
    dummy_win = QWidget()
    dummy_win.setWindowTitle("Ticky Privacy Test Window")
    dummy_win.show()
    
    hwnd = int(dummy_win.winId())
    print(f"Test QWidget HWND: {hwnd}")
    
    # Test setting exclusion ON
    res_on = set_window_capture_exclusion(hwnd, True)
    print(f"set_window_capture_exclusion(hwnd, True) result: {res_on}")
    assert res_on is True, "Native API SetWindowDisplayAffinity failed when setting ON!"
    
    # Query current affinity using GetWindowDisplayAffinity
    if sys.platform == 'win32':
        dw_affinity = ctypes.c_ulong(0)
        res_get = ctypes.windll.user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(dw_affinity))
        print(f"GetWindowDisplayAffinity result: {res_get}, dwAffinity: 0x{dw_affinity.value:08X}")
        assert dw_affinity.value in (WDA_EXCLUDEFROMCAPTURE, 0x01), f"Unexpected affinity 0x{dw_affinity.value:08X}!"
    
    # Test setting exclusion OFF
    res_off = set_window_capture_exclusion(hwnd, False)
    print(f"set_window_capture_exclusion(hwnd, False) result: {res_off}")
    assert res_off is True, "Native API SetWindowDisplayAffinity failed when setting OFF!"
    
    if sys.platform == 'win32':
        dw_affinity = ctypes.c_ulong(0)
        ctypes.windll.user32.GetWindowDisplayAffinity(hwnd, ctypes.byref(dw_affinity))
        print(f"GetWindowDisplayAffinity after OFF: 0x{dw_affinity.value:08X}")
        assert dw_affinity.value == WDA_NONE, f"Expected 0x0, got 0x{dw_affinity.value:08X}!"
        
    dummy_win.close()
    print("Native Window Affinity Test PASSED!")

if __name__ == "__main__":
    test_config_persistence()
    test_window_affinity()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")
