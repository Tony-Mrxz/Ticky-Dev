# widgets/app_icon_service.py
"""Asynchronous Windows shell icon loader.

Shell icon extraction can block for seconds (offline shortcuts, shell
extensions), so it must never run on the GUI thread. Icons are extracted with
SHGetFileInfo on daemon worker threads, converted to QImage there, and turned
into QPixmap only when they arrive back on the GUI thread.
"""

from __future__ import annotations

import ctypes
import os
import queue
import sys
import threading

from PySide6.QtCore import QByteArray, QObject, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICON_SIZE = 26
WORKER_COUNT = 3

DEFAULT_APP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M4 4h6.5v6.5H4zm9.5 0H20v6.5h-6.5zM4 13.5h6.5V20H4zm9.5 0H20V20h-6.5z"/>
</svg>"""

if sys.platform == "win32":
    from ctypes import wintypes

    class _SHFILEINFOW(ctypes.Structure):
        _fields_ = [
            ("hIcon", wintypes.HICON),
            ("iIcon", ctypes.c_int),
            ("dwAttributes", wintypes.DWORD),
            ("szDisplayName", wintypes.WCHAR * 260),
            ("szTypeName", wintypes.WCHAR * 80),
        ]

    class _ICONINFO(ctypes.Structure):
        _fields_ = [
            ("fIcon", wintypes.BOOL),
            ("xHotspot", wintypes.DWORD),
            ("yHotspot", wintypes.DWORD),
            ("hbmMask", wintypes.HBITMAP),
            ("hbmColor", wintypes.HBITMAP),
        ]

    class _BITMAP(ctypes.Structure):
        _fields_ = [
            ("bmType", wintypes.LONG),
            ("bmWidth", wintypes.LONG),
            ("bmHeight", wintypes.LONG),
            ("bmWidthBytes", wintypes.LONG),
            ("bmPlanes", wintypes.WORD),
            ("bmBitsPixel", wintypes.WORD),
            ("bmBits", ctypes.c_void_p),
        ]

    class _BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD),
            ("biWidth", wintypes.LONG),
            ("biHeight", wintypes.LONG),
            ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD),
            ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD),
            ("biXPelsPerMeter", wintypes.LONG),
            ("biYPelsPerMeter", wintypes.LONG),
            ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    _shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

    _SHGFI_ICON = 0x00000100
    _SHGFI_LARGEICON = 0x00000000
    _DIB_RGB_COLORS = 0
    _BI_RGB = 0

    _shell32.SHGetFileInfoW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(_SHFILEINFOW),
        wintypes.UINT,
        wintypes.UINT,
    ]
    _shell32.SHGetFileInfoW.restype = ctypes.c_size_t
    _shell32.ExtractIconExW.argtypes = [
        wintypes.LPCWSTR,
        ctypes.c_int,
        ctypes.POINTER(wintypes.HICON),
        ctypes.POINTER(wintypes.HICON),
        wintypes.UINT,
    ]
    _shell32.ExtractIconExW.restype = wintypes.UINT
    _user32.GetIconInfo.argtypes = [wintypes.HICON, ctypes.POINTER(_ICONINFO)]
    _user32.GetIconInfo.restype = wintypes.BOOL
    _user32.GetDC.argtypes = [wintypes.HWND]
    _user32.GetDC.restype = wintypes.HDC
    _user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    _user32.ReleaseDC.restype = ctypes.c_int
    _user32.DestroyIcon.argtypes = [wintypes.HICON]
    _user32.DestroyIcon.restype = wintypes.BOOL
    _gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    _gdi32.GetObjectW.restype = ctypes.c_int
    _gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        ctypes.c_void_p,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(_BITMAPINFOHEADER),
        wintypes.UINT,
    ]
    _gdi32.GetDIBits.restype = ctypes.c_int
    _gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
    _gdi32.DeleteObject.restype = wintypes.BOOL


def _read_bitmap(bitmap_handle, bit_count: int = 32):
    if sys.platform != "win32" or not bitmap_handle:
        return None

    bitmap = _BITMAP()
    if not _gdi32.GetObjectW(bitmap_handle, ctypes.sizeof(bitmap), ctypes.byref(bitmap)):
        return None
    width = int(bitmap.bmWidth)
    height = abs(int(bitmap.bmHeight))
    if width <= 0 or height <= 0:
        return None

    header = _BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height
    header.biPlanes = 1
    header.biBitCount = bit_count
    header.biCompression = _BI_RGB

    stride = width * (bit_count // 8)
    buffer = ctypes.create_string_buffer(stride * height)
    device_context = _user32.GetDC(None)
    try:
        copied = _gdi32.GetDIBits(
            device_context,
            bitmap_handle,
            0,
            height,
            buffer,
            ctypes.byref(header),
            _DIB_RGB_COLORS,
        )
    finally:
        _user32.ReleaseDC(None, device_context)

    if not copied:
        return None
    return width, height, stride, buffer.raw


def _apply_monochrome_mask(pixels: bytearray, width: int, height: int, mask_handle) -> bool:
    mask = _read_bitmap(mask_handle, 32)
    if mask is None:
        return False
    _, mask_height, mask_stride, mask_bytes = mask
    if mask_height < height:
        return False
    for y in range(height):
        color_row = y * width * 4
        mask_row = y * mask_stride
        for x in range(width):
            transparent = mask_bytes[mask_row + x * 4] > 127
            pixels[color_row + x * 4 + 3] = 0 if transparent else 255
    return True


def _hicon_to_image(icon_handle):
    if sys.platform != "win32" or not icon_handle:
        return None

    icon_info = _ICONINFO()
    try:
        if not _user32.GetIconInfo(icon_handle, ctypes.byref(icon_info)):
            return None

        color_bitmap = None
        if icon_info.hbmColor:
            color_bitmap = _read_bitmap(icon_info.hbmColor, 32)
        if color_bitmap is not None:
            width, height, stride, raw = color_bitmap
            pixels = bytearray(raw)
            has_alpha = any(pixels[index] for index in range(3, len(pixels), 4))
            if not has_alpha:
                if icon_info.hbmMask:
                    _apply_monochrome_mask(pixels, width, height, icon_info.hbmMask)
                else:
                    for index in range(3, len(pixels), 4):
                        pixels[index] = 255
            image = QImage(bytes(pixels), width, height, stride, QImage.Format.Format_ARGB32).copy()
            return image if not image.isNull() else None

        if icon_info.hbmMask:
            mask = _read_bitmap(icon_info.hbmMask, 32)
            if mask is None:
                return None
            width, height, stride, raw = mask
            pixels = bytearray(stride * height)
            for y in range(height):
                row = y * stride
                for x in range(width):
                    index = row + x * 4
                    opaque = raw[index] < 128
                    if opaque:
                        pixels[index] = pixels[index + 1] = pixels[index + 2] = 0
                        pixels[index + 3] = 255
            image = QImage(bytes(pixels), width, height, stride, QImage.Format.Format_ARGB32).copy()
            return image if not image.isNull() else None
        return None
    finally:
        if icon_info.hbmColor:
            _gdi32.DeleteObject(icon_info.hbmColor)
        if icon_info.hbmMask:
            _gdi32.DeleteObject(icon_info.hbmMask)


def _extract_icon_image(path: str, icon_index: int = 0, exact: bool = False):
    """Extract an icon from a file, optionally using an exact icon index."""
    if sys.platform != "win32" or not path:
        return None

    if exact:
        large = wintypes.HICON()
        small = wintypes.HICON()
        try:
            extracted = _shell32.ExtractIconExW(
                path,
                int(icon_index),
                ctypes.byref(large),
                ctypes.byref(small),
                1,
            )
        except Exception:
            extracted = 0
        if small.value:
            _user32.DestroyIcon(small)
        if extracted and large.value:
            try:
                image = _hicon_to_image(large)
            finally:
                _user32.DestroyIcon(large)
            if image is not None:
                return image

    file_info = _SHFILEINFOW()
    result = _shell32.SHGetFileInfoW(
        path,
        0,
        ctypes.byref(file_info),
        ctypes.sizeof(file_info),
        _SHGFI_ICON | _SHGFI_LARGEICON,
    )
    if not result or not file_info.hIcon:
        return None

    try:
        return _hicon_to_image(file_info.hIcon)
    finally:
        _user32.DestroyIcon(file_info.hIcon)


_shortcut_cache: dict[str, tuple[str, int] | None] = {}
_shortcut_cache_lock = threading.Lock()


def _create_shortcut_shell():
    """Create a per-thread WScript.Shell used to resolve .lnk targets."""
    if sys.platform != "win32":
        return None
    try:
        import pythoncom
        from win32com.client import Dispatch

        pythoncom.CoInitialize()
        return Dispatch("WScript.Shell")
    except Exception:
        return None


def _resolve_shortcut(path: str, shell):
    """Return (icon_path, icon_index) for a shortcut, without its overlay arrow."""
    if shell is None or not path.casefold().endswith(".lnk"):
        return None

    with _shortcut_cache_lock:
        if path in _shortcut_cache:
            return _shortcut_cache[path]

    target = ""
    icon_location = ""
    try:
        shortcut = shell.CreateShortcut(path)
        target = (shortcut.TargetPath or "").strip()
        icon_location = (shortcut.IconLocation or "").strip()
    except Exception:
        pass

    resolved = None
    if icon_location:
        location_path, _, index_text = icon_location.rpartition(",")
        location_path = os.path.expandvars(location_path.strip().strip('"'))
        if location_path and os.path.exists(location_path):
            try:
                icon_index = int(index_text)
            except ValueError:
                icon_index = 0
            resolved = (location_path, max(icon_index, 0))

    if resolved is None and target:
        target = os.path.expandvars(target)
        if os.path.exists(target):
            resolved = (target, 0)

    with _shortcut_cache_lock:
        _shortcut_cache[path] = resolved
    return resolved


class _IconWorkerSignals(QObject):
    ready = Signal(str, object)
    failed = Signal(str)


class AppIconService(QObject):
    icon_ready = Signal(str)

    _instance = None

    @classmethod
    def get_instance(cls) -> "AppIconService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        super().__init__()
        self._cache: dict[str, QPixmap] = {}
        self._pending: set[str] = set()
        self._failed: set[str] = set()
        self._queue: queue.Queue = queue.Queue()
        self._signals = _IconWorkerSignals()
        self._signals.ready.connect(self._on_ready, Qt.ConnectionType.QueuedConnection)
        self._signals.failed.connect(self._on_failed, Qt.ConnectionType.QueuedConnection)

        if sys.platform == "win32":
            for index in range(WORKER_COUNT):
                threading.Thread(
                    target=self._worker_loop,
                    name=f"TickyIconWorker{index}",
                    daemon=True,
                ).start()

    def placeholder(self, size: int = ICON_SIZE) -> QPixmap:
        key = f"__placeholder__:{size}"
        pixmap = self._cache.get(key)
        if pixmap is not None:
            return pixmap

        renderer = QSvgRenderer(
            QByteArray(DEFAULT_APP_SVG.replace("COLOR_PLACEHOLDER", "#4CC2FF").encode("utf-8"))
        )
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        self._cache[key] = pixmap
        return pixmap

    def cached(self, key: str) -> QPixmap | None:
        return self._cache.get(key)

    def request(self, app):
        key = getattr(app, "icon_key", None)
        path = getattr(app, "path", None)
        if not key:
            return
        if key in self._cache or key in self._failed or key in self._pending:
            return
        if not path or not os.path.exists(path):
            self._failed.add(key)
            return

        self._pending.add(key)
        self._queue.put((key, path))

    def _worker_loop(self):
        shell = _create_shortcut_shell()
        while True:
            key, path = self._queue.get()
            try:
                resolved = _resolve_shortcut(path, shell)
                if resolved is not None:
                    image = _extract_icon_image(resolved[0], resolved[1], exact=True)
                    if image is None:
                        image = _extract_icon_image(path)
                else:
                    image = _extract_icon_image(path)
            except Exception:
                image = None
            try:
                if image is None or image.isNull():
                    self._signals.failed.emit(key)
                else:
                    self._signals.ready.emit(key, image)
            except RuntimeError:
                return

    def _on_ready(self, key: str, image):
        self._pending.discard(key)
        if not isinstance(image, QImage) or image.isNull():
            self._failed.add(key)
            return
        scaled = image.scaled(
            ICON_SIZE,
            ICON_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        pixmap = QPixmap.fromImage(scaled)
        if pixmap.isNull():
            self._failed.add(key)
            return
        self._cache[key] = pixmap
        self.icon_ready.emit(key)

    def _on_failed(self, key: str):
        self._pending.discard(key)
        self._failed.add(key)
