# utils/file_indexer.py
"""Background index of common user folders for quick file and folder search.

Only well-known user folders are scanned. Heavy build/package directories and
directory reparse points are skipped, and the index is capped, so indexing a
large home folder stays bounded. Searches run on a worker thread; a newer query
supersedes one still in flight.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, Signal

from utils.app_search import SEARCH_PRECISION, match_text, normalize_query

MAX_DEPTH = 6
MAX_ENTRIES = 60_000
DEFAULT_LIMIT = 2

_FILE_ATTRIBUTE_REPARSE_POINT = 0x0400

EXCLUDED_DIR_NAMES = frozenset(
    {
        "$recycle.bin",
        ".cache",
        ".cargo",
        ".conda",
        ".eggs",
        ".git",
        ".gradle",
        ".hg",
        ".m2",
        ".mypy_cache",
        ".next",
        ".npm",
        ".nuxt",
        ".pytest_cache",
        ".ruff_cache",
        ".rustup",
        ".svn",
        ".tox",
        ".venv",
        "appdata",
        "application data",
        "bin",
        "bower_components",
        "browser_profile",
        "build",
        "coverage",
        "crashpad",
        "dist",
        "env",
        "logs",
        "node_modules",
        "obj",
        "recovery",
        "site-packages",
        "system volume information",
        "target",
        "temp",
        "tmp",
        "venv",
        "__pycache__",
    }
)

EXCLUDED_FILE_NAMES = frozenset({"desktop.ini", "thumbs.db", ".ds_store", "ntuser.dat"})

KNOWN_FOLDER_IDS = (
    ("Desktop", 0x0010),
    ("Documents", 0x0005),
    ("Pictures", 0x0027),
    ("Music", 0x000D),
    ("Videos", 0x000E),
)

_TYPE_LABELS = {
    ".7z": "Archive",
    ".avi": "Video",
    ".bat": "Batch file",
    ".csv": "CSV file",
    ".css": "CSS file",
    ".doc": "Word document",
    ".docx": "Word document",
    ".exe": "Application",
    ".flac": "Audio",
    ".gif": "Image",
    ".html": "HTML file",
    ".jpeg": "Image",
    ".jpg": "Image",
    ".js": "JavaScript file",
    ".json": "JSON file",
    ".m4a": "Audio",
    ".md": "Markdown document",
    ".mkv": "Video",
    ".mov": "Video",
    ".mp3": "Audio",
    ".mp4": "Video",
    ".msi": "Installer",
    ".pdf": "PDF document",
    ".png": "Image",
    ".ppt": "PowerPoint presentation",
    ".pptx": "PowerPoint presentation",
    ".ps1": "PowerShell script",
    ".py": "Python file",
    ".rar": "Archive",
    ".svg": "Image",
    ".ts": "TypeScript file",
    ".txt": "Text document",
    ".wav": "Audio",
    ".webp": "Image",
    ".xls": "Excel spreadsheet",
    ".xlsx": "Excel spreadsheet",
    ".zip": "Archive",
}

_WORD_BOUNDARIES = " -_."


class FileItem:
    """An indexed file or folder."""

    __slots__ = ("name", "path", "is_dir", "suffix", "name_fold", "icon_key")

    def __init__(self, path: str, is_dir: bool):
        self.path = path
        self.name = os.path.basename(path.rstrip("\\/")) or path
        self.is_dir = is_dir
        self.suffix = "" if is_dir else os.path.splitext(self.name)[1].casefold()
        self.name_fold = self.name.casefold()
        self.icon_key = f"file:{path.casefold()}"

    def type_label(self) -> str:
        if self.is_dir:
            return "Folder"
        label = _TYPE_LABELS.get(self.suffix)
        if label:
            return label
        if self.suffix:
            return f"{self.suffix.lstrip('.').upper()} file"
        return "File"

    def parent_label(self) -> str:
        parent = os.path.dirname(self.path)
        home = os.path.expanduser("~")
        if parent.casefold() == home.casefold():
            return "Home"
        try:
            relative = os.path.relpath(parent, home)
        except ValueError:
            relative = parent
        if relative and not relative.startswith(".."):
            return relative
        drive, tail = os.path.splitdrive(parent)
        parts = [part for part in tail.split(os.sep) if part]
        return os.sep.join(parts[-2:]) if parts else parent or drive


def open_path(path: str) -> bool:
    """Open a file or folder with the platform default handler."""
    try:
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except Exception as error:
        print(f"[FileIndexer] Could not open {path}: {error}")
        return False


def _known_folder(csidl: int) -> str | None:
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        buffer = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        result = ctypes.windll.shell32.SHGetFolderPathW(None, csidl, None, 0, buffer)
        if result != 0:
            return None
        return buffer.value or None
    except Exception:
        return None


def candidate_roots() -> list[str]:
    roots: list[str] = []
    seen: set[str] = set()

    def add(path: str | None):
        if not path:
            return
        path = os.path.abspath(path)
        key = path.casefold()
        if key in seen or not os.path.isdir(path):
            return
        seen.add(key)
        roots.append(path)

    if sys.platform != "win32":
        home = os.path.expanduser("~")
        for name in ("Desktop", "Documents", "Downloads", "Pictures", "Music", "Movies", "Videos"):
            add(os.path.join(home, name))
        return roots

    for _, csidl in KNOWN_FOLDER_IDS:
        add(_known_folder(csidl))
    add(os.path.join(os.path.expanduser("~"), "Downloads"))
    return roots


def _is_reparse_point(entry: os.DirEntry) -> bool:
    try:
        attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    except OSError:
        return True
    return bool(attributes & _FILE_ATTRIBUTE_REPARSE_POINT)


def build_index(
    roots: list[str],
    max_entries: int = MAX_ENTRIES,
    max_depth: int = MAX_DEPTH,
) -> list[FileItem]:
    """Walk the given roots and return files and folders in depth-first order."""
    items: list[FileItem] = []
    seen_paths: set[str] = set()

    def add_item(path: str, is_dir: bool) -> bool:
        key = path.casefold()
        if key in seen_paths or len(items) >= max_entries:
            return False
        seen_paths.add(key)
        items.append(FileItem(path, is_dir))
        return True

    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        add_item(root, True)
        stack: list[tuple[str, int]] = [(root, 0)]
        while stack and len(items) < max_entries:
            directory, depth = stack.pop()
            try:
                with os.scandir(directory) as scanner:
                    entries = list(scanner)
            except OSError:
                continue
            for entry in entries:
                if len(items) >= max_entries:
                    break
                name = entry.name
                if not name:
                    continue
                name_fold = name.casefold()
                try:
                    is_dir = entry.is_dir(follow_symlinks=False)
                except OSError:
                    continue
                if is_dir:
                    if name_fold in EXCLUDED_DIR_NAMES or "cache" in name_fold:
                        continue
                    # Reparse folders are shown as results but not traversed,
                    # so junctions cannot create scan loops.
                    if add_item(entry.path, True) and depth < max_depth:
                        if not _is_reparse_point(entry):
                            stack.append((entry.path, depth + 1))
                else:
                    if name_fold in EXCLUDED_FILE_NAMES:
                        continue
                    add_item(entry.path, False)
    return items


def _substring_score(name_fold: str, terms: list[str], is_dir: bool) -> float | None:
    cursor = 0
    first = -1
    for term in terms:
        found = name_fold.find(term, cursor)
        if found < 0:
            return None
        if first < 0:
            first = found
        cursor = found + len(term)

    joined = " ".join(terms)
    if name_fold == joined:
        score = 1200.0
    elif name_fold.startswith(joined):
        score = 1000.0
    elif first == 0:
        score = 900.0
    elif name_fold[first - 1] in _WORD_BOUNDARIES:
        score = 800.0
    else:
        score = 500.0

    score -= first * 2.0
    score += max(0.0, 60.0 - len(name_fold))
    if is_dir:
        score += 10.0
    return score


def _select_balanced(scored, limit: int) -> list[FileItem]:
    """Keep the top results, but surface the other kind when both match."""
    ordered = [entry[4] for entry in scored]
    if limit <= 1 or len(ordered) <= limit:
        return ordered[:limit]

    top = ordered[:limit]
    if len({item.is_dir for item in top}) > 1:
        return top

    wanted_is_dir = not top[0].is_dir
    for item in ordered[limit:]:
        if item.is_dir == wanted_is_dir:
            return [*top[:-1], item]
    return top


def search_items(items, query: str, limit: int = DEFAULT_LIMIT) -> list[FileItem]:
    """Rank name matches, falling back to fuzzy matching when substrings are sparse."""
    normalized = normalize_query(query)
    if not normalized or limit <= 0:
        return []

    terms = normalized.split(" ")
    scored: list[tuple[float, int, str, str, FileItem]] = []
    for item in items:
        score = _substring_score(item.name_fold, terms, item.is_dir)
        if score is None:
            continue
        scored.append((score, len(item.name_fold), item.name_fold, item.path, item))

    scored.sort(key=lambda entry: (-entry[0], entry[1], entry[2], entry[3]))
    if len(scored) >= limit:
        return _select_balanced(scored, limit)

    matched = {entry[4].path for entry in scored}
    first_char = normalized[0]
    fuzzy: list[tuple[float, int, str, str, FileItem]] = []
    for item in items:
        if item.path in matched or first_char not in item.name_fold:
            continue
        match = match_text(normalized, item.name, precision=SEARCH_PRECISION)
        if match is None:
            continue
        fuzzy.append((match.score * 0.9, len(item.name_fold), item.name_fold, item.path, item))

    combined = sorted(scored + fuzzy, key=lambda entry: (-entry[0], entry[1], entry[2], entry[3]))
    return _select_balanced(combined, limit)


class FileIndexer(QObject):
    """Singleton index of user files and folders with asynchronous queries."""

    results_ready = Signal(str, object)
    index_ready = Signal()

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "FileIndexer":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            instance = cls._instance
        instance.start()
        return instance

    def __init__(self):
        super().__init__()
        self._items: list[FileItem] = []
        self._lock = threading.Lock()
        self._started = False
        self._ready = False
        self._pending: tuple[str, int] | None = None
        self._search_event = threading.Event()

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
            name="TickyFileIndexer",
            daemon=True,
        ).start()
        threading.Thread(
            target=self._search_loop,
            name="TickyFileSearch",
            daemon=True,
        ).start()

    def _initial_index(self):
        try:
            items = build_index(candidate_roots())
        except Exception as error:
            print(f"[FileIndexer] Initial index failed: {error}")
            items = []
        with self._lock:
            self._items = items
            self._ready = True
        self.index_ready.emit()

    def search_async(self, query: str, limit: int = DEFAULT_LIMIT):
        if not query.strip() or not self._ready:
            return
        with self._lock:
            self._pending = (query, limit)
        self._search_event.set()

    def search(self, query: str, limit: int = DEFAULT_LIMIT) -> list[FileItem]:
        with self._lock:
            items = tuple(self._items)
        return search_items(items, query, limit=limit)

    def _search_loop(self):
        while True:
            self._search_event.wait()
            self._search_event.clear()
            with self._lock:
                pending = self._pending
                self._pending = None
            if pending is None:
                continue
            query, limit = pending
            try:
                results = self.search(query, limit=limit)
            except Exception as error:
                print(f"[FileIndexer] Search failed: {error}")
                results = []
            with self._lock:
                if self._pending is not None:
                    continue
            self.results_ready.emit(query, results)
