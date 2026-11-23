# utils/bucket_service.py
"""Bucket: anything dragged onto the notch is copied into ~/.ticky_bucket and listed in config."""

import base64
import hashlib
import os
import re
import shutil
import time
import urllib.request
import uuid

from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtCore import QUrl, QByteArray, QMimeData

from utils import config
from utils.web_search import open_url

BUCKET_DIR = os.path.expanduser("~/.ticky_bucket")

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_ITEMS = 300
MAX_TEXT_CHARS = 20000

IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".gif", ".bmp", ".dib",
    ".webp", ".ico", ".tif", ".tiff", ".svg", ".svgz", ".heic", ".heif",
    ".avif", ".raw", ".cr2", ".nef", ".arw", ".dng"
}

KIND_LABELS = {"image": "Image", "file": "File", "link": "Link", "text": "Text"}


def load_items():
    """Stored bucket entries, newest first, tolerating anything odd in the config."""
    raw = config.load_config().get("bucket_items", [])
    items = []
    if isinstance(raw, list):
        for entry in raw:
            if not isinstance(entry, dict) or not entry.get("id"):
                continue
            if entry.get("kind") not in KIND_LABELS:
                continue
            if entry["kind"] in ("image", "file") and not os.path.isfile(entry.get("path", "")):
                continue
            items.append(entry)
    items.sort(key=lambda e: str(e.get("created", "")), reverse=True)
    return items[:MAX_ITEMS]


def save_items(items):
    items = list(items or [])
    for stale in items[MAX_ITEMS:]:
        _delete_file(stale)
    config.save_config({"bucket_items": items[:MAX_ITEMS]})


def _ensure_dir():
    try:
        os.makedirs(BUCKET_DIR, exist_ok=True)
    except OSError:
        pass


def _delete_file(item):
    path = item.get("path", "")
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _hash_of(data):
    return hashlib.sha1(data).hexdigest()[:16]


def _file_hash(path):
    digest = hashlib.sha1()
    try:
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()[:16]


def _unique_dest(ext):
    return os.path.join(BUCKET_DIR, f"{uuid.uuid4().hex}{ext}")


def _existing_hashes(items):
    return {entry.get("hash", "") for entry in items if entry.get("hash")}


def _title_for_file(name):
    base = os.path.splitext(os.path.basename(name))[0].strip()
    return (base[:60] or "Untitled")


def _extract_image_from_mime(mime):
    """Safely extract a QImage from a drag/drop QMimeData instance across different platforms."""
    if mime is None:
        return None
    # 1. Native Qt image
    if mime.hasImage():
        img = mime.imageData()
        if isinstance(img, QPixmap) and not img.isNull():
            return img.toImage()
        if isinstance(img, QImage) and not img.isNull():
            return img
    # 2. Check standard image mime formats (Windows/Chromium often pass image/png directly)
    for fmt in ("image/png", "image/jpeg", "image/jpg", "image/webp", "image/bmp", "image/gif", "image/tiff"):
        if mime.hasFormat(fmt):
            data = mime.data(fmt)
            if not data.isEmpty():
                img = QImage.fromData(data)
                if not img.isNull():
                    return img
    # 3. Check any mime format that starts with image/
    for fmt in mime.formats():
        if fmt.startswith("image/"):
            data = mime.data(fmt)
            if not data.isEmpty():
                img = QImage.fromData(data)
                if not img.isNull():
                    return img
    return None


def _download_web_image(url_str: str, items: list, seen: set):
    """Extract or download an image if the URL points directly to an image or data URI."""
    if not url_str:
        return None
    # Data URI
    if url_str.startswith("data:image/"):
        try:
            _, b64 = url_str.split(",", 1)
            raw = base64.b64decode(b64)
            img = QImage.fromData(raw)
            if not img.isNull():
                return _capture_bitmap(img, items, seen, title="Web image")
        except Exception:
            return None

    # HTTP/HTTPS direct image link
    path_lower = url_str.lower().split("?")[0].split("#")[0]
    ext = os.path.splitext(path_lower)[1]
    if ext in IMAGE_EXTS:
        try:
            req = urllib.request.Request(
                url_str,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = resp.read(MAX_FILE_BYTES + 1)
                if 0 < len(data) <= MAX_FILE_BYTES:
                    img = QImage.fromData(data)
                    if not img.isNull():
                        dest_ext = ext if ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp") else ".png"
                        dest = _unique_dest(dest_ext)
                        with open(dest, "wb") as f:
                            f.write(data)
                        digest = _file_hash(dest)
                        if digest in seen:
                            _delete_file({"path": dest})
                            for entry in items:
                                if entry.get("hash") == digest:
                                    entry["created"] = _now()
                                    return entry
                            return None
                        size = len(data)
                        title = os.path.splitext(os.path.basename(path_lower))[0] or "Web image"
                        item = {
                            "id": uuid.uuid4().hex, "kind": "image", "title": title[:60],
                            "path": dest, "mime": dest_ext.lstrip("."), "ext": dest_ext, "size": size,
                            "hash": digest, "created": _now(), "origin": url_str
                        }
                        seen.add(digest)
                        return item
        except Exception:
            pass
    return None


def capture_mime(mime):
    """Save everything useful in a drag/drop payload. Returns the new items, newest first."""
    if mime is None:
        return []
    _ensure_dir()
    items = load_items()
    seen = _existing_hashes(items)
    captured = []

    # 1. First priority: Direct bitmap or image data in MIME payload!
    # Dragging an image from browser, paint, snipping tool, or clipboard provides the actual image.
    img = _extract_image_from_mime(mime)
    if img is not None and not img.isNull():
        title = "Dropped image"
        if mime.hasUrls():
            for u in mime.urls():
                if u.isLocalFile():
                    title = _title_for_file(u.toLocalFile())
                    break
        item = _capture_bitmap(img, items, seen, title=title)
        if item:
            captured.append(item)

    # 2. Local file URLs or web links
    if not captured and mime.hasUrls():
        for url in mime.urls():
            item = _capture_url(url, items, seen)
            if item:
                captured.append(item)

    # 3. HTML with embedded base64 image
    if not captured and mime.hasHtml():
        html = mime.html()
        if "data:image/" in html:
            m = re.search(r'data:image/[^"\'\s]+', html)
            if m:
                web_img = _download_web_image(m.group(0), items, seen)
                if web_img:
                    captured.append(web_img)

    # 4. Text fallback
    if not captured and mime.hasText():
        raw_text = mime.text().strip()
        if raw_text.startswith("data:image/"):
            web_img = _download_web_image(raw_text, items, seen)
            if web_img:
                captured.append(web_img)
        elif raw_text.startswith("http://") or raw_text.startswith("https://"):
            web_img = _download_web_image(raw_text, items, seen)
            if web_img:
                captured.append(web_img)
            else:
                item = _capture_link(raw_text, items, seen)
                if item:
                    captured.append(item)
        else:
            item = _capture_text(raw_text, items, seen)
            if item:
                captured.append(item)

    if captured:
        # Merge captured items with existing items without duplicates
        captured_ids = {c.get("id") for c in captured}
        remaining_items = [it for it in items if it.get("id") not in captured_ids]
        save_items(captured + remaining_items)
    return captured


def _capture_url(url, items, seen):
    if not url.isValid():
        return None
    scheme = url.scheme().lower()
    if scheme == "file":
        path = url.toLocalFile()
        if path and os.path.isfile(path):
            return _capture_file(path, items, seen)
    elif scheme in ("http", "https"):
        link = url.toString()
        web_img = _download_web_image(link, items, seen)
        if web_img:
            return web_img
        return _capture_link(link, items, seen)
    elif scheme == "data":
        link = url.toString()
        web_img = _download_web_image(link, items, seen)
        if web_img:
            return web_img
    return None


def _capture_file(src, items, seen):
    try:
        size = os.path.getsize(src)
    except OSError:
        return None
    if size > MAX_FILE_BYTES:
        return None
    digest = _file_hash(src)
    if not digest:
        return None
    if digest in seen:
        # File is already in the bucket: bring to top and refresh timestamp
        for entry in items:
            if entry.get("hash") == digest:
                entry["created"] = _now()
                return entry
        return None
    ext = os.path.splitext(src)[1].lower()[:10]
    dest = _unique_dest(ext)
    try:
        shutil.copy2(src, dest)
    except OSError:
        return None
    kind = "image" if ext in IMAGE_EXTS else "file"
    item = {"id": uuid.uuid4().hex, "kind": kind, "title": _title_for_file(src),
            "path": dest, "mime": ext.lstrip("."), "ext": ext, "size": size,
            "hash": digest, "created": _now(), "origin": src}
    seen.add(digest)
    return item


def _capture_bitmap(image, items, seen, title="Dropped image"):
    if image is None or image.isNull():
        return None
    dest = _unique_dest(".png")
    if not image.save(dest, "PNG"):
        return None
    digest = _file_hash(dest)
    if not digest:
        _delete_file({"path": dest})
        return None
    if digest in seen:
        _delete_file({"path": dest})
        # Already in bucket: bring to top and refresh timestamp
        for entry in items:
            if entry.get("hash") == digest:
                entry["created"] = _now()
                return entry
        return None
    size = os.path.getsize(dest) if os.path.isfile(dest) else 0
    item = {"id": uuid.uuid4().hex, "kind": "image", "title": title,
            "path": dest, "mime": "png", "ext": ".png", "size": size,
            "hash": digest, "created": _now(), "origin": ""}
    seen.add(digest)
    return item


def _capture_link(link, items, seen):
    digest = _hash_of(link.encode("utf-8", "ignore"))
    if digest in seen:
        return None
    host = QUrl(link).host() or link[:60]
    item = {"id": uuid.uuid4().hex, "kind": "link", "title": host[:60], "url": link,
            "path": "", "mime": "url", "ext": "", "size": len(link),
            "hash": digest, "created": _now(), "origin": ""}
    seen.add(digest)
    return item


def _capture_text(text, items, seen):
    clean = (text or "").strip()
    if not clean:
        return None
    clean = clean[:MAX_TEXT_CHARS]
    digest = _hash_of(clean.encode("utf-8", "ignore"))
    if digest in seen:
        return None
    first_line = clean.splitlines()[0].strip()
    item = {"id": uuid.uuid4().hex, "kind": "text", "title": (first_line[:60] or "Note"),
            "text": clean, "path": "", "mime": "text", "ext": "", "size": len(clean),
            "hash": digest, "created": _now(), "origin": ""}
    seen.add(digest)
    return item


def remove_item(item_id):
    items = load_items()
    keep = [entry for entry in items if entry.get("id") != item_id]
    for dropped in items:
        if dropped.get("id") == item_id:
            _delete_file(dropped)
    save_items(keep)


def clear_bucket():
    for item in load_items():
        _delete_file(item)
    save_items([])
    # Anything left behind was orphaned by an earlier failed delete.
    try:
        for name in os.listdir(BUCKET_DIR):
            _delete_file({"path": os.path.join(BUCKET_DIR, name)})
    except OSError:
        pass


def open_item(item):
    """Images and files go to the system viewer, links to the browser, text to the clipboard."""
    kind = item.get("kind")
    if kind in ("image", "file"):
        path = item.get("path", "")
        if not path or not os.path.isfile(path):
            return False
        try:
            os.startfile(path)  # Windows
            return True
        except OSError:
            return open_url(QUrl.fromLocalFile(path).toString())
    if kind == "link":
        return open_url(item.get("url", ""))
    if kind == "text":
        clipboard = QGuiApplication.clipboard()
        if clipboard is None:
            return False
        clipboard.setText(item.get("text", ""))
        return True
    return False


def get_drag_file_path(item: dict) -> str:
    """Return the best file path for dragging out, ensuring a friendly original filename."""
    path = item.get("path", "")
    if not path or not os.path.isfile(path):
        return ""
    title = item.get("title", "").strip()
    ext = item.get("ext", "").strip()
    if not ext:
        ext = os.path.splitext(path)[1]
    if not title:
        return path

    # Sanitize title for valid Windows filename
    clean_title = re.sub(r'[\\/*?:"<>|]', "_", title).strip()
    if not clean_title:
        return path

    target_name = clean_title if clean_title.lower().endswith(ext.lower()) else f"{clean_title}{ext}"
    current_name = os.path.basename(path)
    if current_name.lower() == target_name.lower():
        return path

    # Stage into a subfolder with the clean user-friendly filename
    stage_dir = os.path.join(BUCKET_DIR, "_drag")
    try:
        os.makedirs(stage_dir, exist_ok=True)
        staged_path = os.path.join(stage_dir, target_name)
        if not os.path.isfile(staged_path) or os.path.getsize(staged_path) != os.path.getsize(path):
            shutil.copy2(path, staged_path)
        return staged_path
    except Exception:
        return path


def create_drag_mime(item: dict) -> QMimeData:
    """
    Prepare a rich QMimeData payload for dragging an item out of the bucket.
    Enables native dropping/pasting into File Explorer, Desktop, web browsers,
    Discord, Slack, text editors, Office apps, and more.
    """
    mime = QMimeData()
    kind = item.get("kind", "")

    if kind in ("file", "image"):
        path = get_drag_file_path(item) or item.get("path", "")
        if path and os.path.isfile(path):
            abs_path = os.path.abspath(path)
            url = QUrl.fromLocalFile(abs_path)
            mime.setUrls([url])
            mime.setText(abs_path)
            if kind == "image":
                img = QImage(abs_path)
                if not img.isNull():
                    mime.setImageData(img)
    elif kind == "link":
        url_str = item.get("url", "")
        if url_str:
            urls = [QUrl(url_str)]
            mime.setText(url_str)
            # Create a staged .url shortcut file for dragging onto Desktop / Explorer
            stage_dir = os.path.join(BUCKET_DIR, "_drag")
            try:
                os.makedirs(stage_dir, exist_ok=True)
                title = item.get("title", "Link").strip()
                clean_title = re.sub(r'[\\/*?:"<>|]', "_", title).strip() or "Link"
                shortcut_path = os.path.join(stage_dir, f"{clean_title}.url")
                with open(shortcut_path, "w", encoding="utf-8") as f:
                    f.write(f"[InternetShortcut]\nURL={url_str}\n")
                urls.append(QUrl.fromLocalFile(os.path.abspath(shortcut_path)))
            except Exception:
                pass
            mime.setUrls(urls)
    elif kind == "text":
        txt = item.get("text", "")
        if txt:
            mime.setText(txt)
            # Create a staged .txt note file for dragging onto Desktop / Explorer
            stage_dir = os.path.join(BUCKET_DIR, "_drag")
            try:
                os.makedirs(stage_dir, exist_ok=True)
                title = item.get("title", "Note").strip()
                clean_title = re.sub(r'[\\/*?:"<>|]', "_", title).strip() or "Note"
                note_path = os.path.join(stage_dir, f"{clean_title}.txt")
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(txt)
                mime.setUrls([QUrl.fromLocalFile(os.path.abspath(note_path))])
            except Exception:
                pass
    return mime


def copy_to_clipboard(item):
    clipboard = QGuiApplication.clipboard()
    if clipboard is None:
        return False
    kind = item.get("kind")
    if kind == "text":
        clipboard.setText(item.get("text", ""))
    elif kind == "link":
        clipboard.setText(item.get("url", ""))
    elif kind in ("image", "file"):
        path = get_drag_file_path(item) or item.get("path", "")
        if path and os.path.isfile(path):
            abs_p = os.path.abspath(path)
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(abs_p)])
            mime.setText(abs_p)
            if kind == "image":
                img = QImage(abs_p)
                if not img.isNull():
                    mime.setImageData(img)
            clipboard.setMimeData(mime)
        else:
            return False
    return True


def describe(item):
    kind = KIND_LABELS.get(item.get("kind", ""), "Item")
    if item.get("kind") == "link":
        return f"{kind}\n{item.get('url', '')}"
    if item.get("kind") == "text":
        preview = (item.get("text", "") or "").replace("\n", " ")[:80]
        return f"{kind}\n{preview}"
    return f"{kind}\n{item.get('origin') or item.get('path', '')}"


def total_bytes(items=None):
    used = 0
    for item in (items if items is not None else load_items()):
        try:
            used += int(item.get("size", 0) or 0)
        except (TypeError, ValueError):
            continue
    return used


def format_bytes(size):
    try:
        size = float(size or 0)
    except (TypeError, ValueError):
        return "0 B"
    if size < 1024:
        return f"{int(size)} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def open_bucket_folder():
    """Reveal ~/.ticky_bucket in Windows File Explorer."""
    _ensure_dir()
    if os.name == "nt":
        try:
            os.startfile(BUCKET_DIR)
            return True
        except Exception:
            pass
    return open_url(QUrl.fromLocalFile(BUCKET_DIR).toString())

