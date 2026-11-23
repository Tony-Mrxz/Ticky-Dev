# utils/favicon_cache.py
"""Website icons for the notch dashboard shortcuts, fetched off the UI thread."""

import hashlib
import os
import urllib.request

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

FAVICON_DIR = os.path.join(os.path.expanduser("~"), ".ticky_favicons")
FAVICON_SIZE = 32
USER_AGENT = "TickyApp/1.0"
MAX_BYTES = 256 * 1024


def domain_for_url(url):
    """Bare hostname of a shortcut URL, with or without a typed scheme."""
    text = (url or "").strip()
    if not text:
        return ""
    if "//" not in text:
        text = "https://" + text
    host = ""
    try:
        # urlparse only reveals the port, so the authority is split by hand.
        authority = text.split("//", 1)[1].split("/", 1)[0]
        host = authority.rsplit("@", 1)[-1].split(":", 1)[0].lower()
    except IndexError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _is_image(data):
    if data[:4] == b"\x00\x00\x01\x00" or data[:8] == b"\x89PNG\r\n\x1a\n":
        return True
    if data[:3] == b"\xff\xd8\xff" or data[:6] in (b"GIF87a", b"GIF89a"):
        return True
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return b"<svg" in data[:512].lower()


def _candidate_urls(domain):
    yield f"https://{domain}/favicon.ico"
    yield f"https://icons.duckduckgo.com/ip3/{domain}.ico"


class _FaviconWorker(QThread):
    """Downloads one favicon; the bytes are decoded back on the GUI thread."""
    fetched = Signal(str, object)

    def __init__(self, domain, parent=None):
        super().__init__(parent)
        self.domain = domain

    def run(self):
        for url in _candidate_urls(self.domain):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=6) as resp:
                    data = resp.read(MAX_BYTES)
            except Exception:
                continue
            if data and _is_image(data):
                self.fetched.emit(self.domain, data)
                return
        self.fetched.emit(self.domain, None)


def _pixmap_from_bytes(data):
    pixmap = QPixmap()
    if b"<svg" not in data[:512].lower() and pixmap.loadFromData(data):
        return pixmap
    renderer = QSvgRenderer(data)
    if not renderer.isValid():
        return QPixmap()
    canvas = QPixmap(FAVICON_SIZE, FAVICON_SIZE)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    renderer.render(painter)
    painter.end()
    return canvas


class FaviconCache(QObject):
    """Memory + disk cache of website icons keyed by hostname."""

    loaded = Signal(str)

    _instance = None

    @classmethod
    def get_instance(cls) -> "FaviconCache":
        if cls._instance is None:
            cls._instance = FaviconCache()
        return cls._instance

    def __init__(self, directory=FAVICON_DIR, parent=None):
        super().__init__(parent)
        self._directory = directory
        self._icons = {}
        self._pending = set()
        self._missing = set()

    def icon_for(self, url):
        """Cached icon, or None while it is still being fetched."""
        domain = domain_for_url(url)
        if not domain or domain in self._missing:
            return None
        icon = self._icons.get(domain)
        if icon:
            return icon
        cached = self._read_file(domain)
        if cached:
            self._icons[domain] = QIcon(cached)
            return self._icons[domain]
        if domain not in self._pending:
            self._pending.add(domain)
            worker = _FaviconWorker(domain, self)
            worker.fetched.connect(self._on_fetched)
            worker.finished.connect(worker.deleteLater)
            worker.start()
        return None

    def _on_fetched(self, domain, data):
        self._pending.discard(domain)
        if not data:
            self._missing.add(domain)
            return
        pixmap = _pixmap_from_bytes(data)
        if pixmap.isNull():
            self._missing.add(domain)
            return
        if pixmap.width() > FAVICON_SIZE or pixmap.height() > FAVICON_SIZE:
            pixmap = pixmap.scaled(FAVICON_SIZE, FAVICON_SIZE,
                                   Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
        self._icons[domain] = QIcon(pixmap)
        self._write_file(domain, data)
        self.loaded.emit(domain)

    def _cache_path(self, domain):
        digest = hashlib.sha1(domain.encode("utf-8")).hexdigest()[:16]
        return os.path.join(self._directory, digest + ".img")

    def _read_file(self, domain):
        try:
            with open(self._cache_path(domain), "rb") as fh:
                data = fh.read(MAX_BYTES)
        except OSError:
            return None
        return _pixmap_from_bytes(data) if _is_image(data) else None

    def _write_file(self, domain, data):
        try:
            os.makedirs(self._directory, exist_ok=True)
            with open(self._cache_path(domain), "wb") as fh:
                fh.write(data)
        except OSError:
            pass
