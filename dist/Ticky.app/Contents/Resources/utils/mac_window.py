# utils/mac_window.py
"""macOS Cocoa window configuration helpers via ctypes/Objective-C runtime."""

import sys

def configure_mac_window(win_id, always_on_top=True):
    """
    Configure Cocoa NSWindow on macOS so it:
    1. Does not hide on deactivate (setHidesOnDeactivate: NO), remaining visible when switching apps.
    2. Joins all virtual desktops / Spaces (NSWindowCollectionBehaviorCanJoinAllSpaces).
    3. Remains stationary across desktop changes (NSWindowCollectionBehaviorStationary).
    4. Can float above full-screen windows (NSWindowCollectionBehaviorFullScreenAuxiliary).
    5. Sets appropriate Cocoa window level if always_on_top is enabled.
    """
    if sys.platform != 'darwin':
        return

    try:
        import ctypes
        from ctypes import c_void_p, c_char_p, c_ulonglong, c_bool, c_longlong

        objc = ctypes.cdll.LoadLibrary('/System/Library/Frameworks/Foundation.framework/Foundation')
        
        objc.objc_getClass.restype = c_void_p
        objc.objc_getClass.argtypes = [c_char_p]

        objc.sel_registerName.restype = c_void_p
        objc.sel_registerName.argtypes = [c_char_p]

        objc_msgSend = objc.objc_msgSend

        def get_sel(name):
            return objc.sel_registerName(name.encode('utf-8'))

        ns_view = c_void_p(int(win_id))
        if not ns_view:
            return

        # Get NSWindow pointer: [nsView window]
        objc_msgSend.argtypes = [c_void_p, c_void_p]
        objc_msgSend.restype = c_void_p
        ns_window = objc_msgSend(ns_view, get_sel("window"))

        if not ns_window:
            return

        # 1. Disable hidesOnDeactivate (Crucial fix for macOS!)
        # By default, NSPanel utility windows hide when switching to another app (Finder, Chrome, VS Code, etc.).
        # Setting setHidesOnDeactivate:NO keeps Ticky visible when switching app focus.
        objc_msgSend.argtypes = [c_void_p, c_void_p, c_bool]
        objc_msgSend.restype = None
        objc_msgSend(ns_window, get_sel("setHidesOnDeactivate:"), False)

        # 2. Set collectionBehavior:
        # CanJoinAllSpaces (1 << 0 = 1)
        # Stationary (1 << 4 = 16)
        # FullScreenAuxiliary (1 << 8 = 256)
        # Total = 1 | 16 | 256 = 273 (0x111)
        behavior = c_ulonglong(1 | 16 | 256)
        objc_msgSend.argtypes = [c_void_p, c_void_p, c_ulonglong]
        objc_msgSend.restype = None
        objc_msgSend(ns_window, get_sel("setCollectionBehavior:"), behavior)

        # 3. Set window level if always_on_top is True
        # NSFloatingWindowLevel = 3, NSSubmenuWindowLevel = 3, NSStatusWindowLevel = 25
        if always_on_top:
            objc_msgSend.argtypes = [c_void_p, c_void_p, c_longlong]
            objc_msgSend.restype = None
            objc_msgSend(ns_window, get_sel("setLevel:"), c_longlong(3))

    except Exception as e:
        print(f"[macOS Window] Warning during Cocoa window setup: {e}")
