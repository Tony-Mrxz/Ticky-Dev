# widgets/notch_bucket.py
"""
Bucket stage: modernized drop zone UI/UX and rich capture cards.
- Drop Target: magnetic glowing drop zone with animated icon and format tags.
- Bucket Browser: rich micro-cards with thumbnail previews, filenames, sizes, 1-click delete,
  folder reveal, clear-all, and quick clipboard copy.
"""

import os
import sys
from PySide6.QtCore import Qt, Signal, QByteArray, QPointF, QRectF, QSize, QTimer, QRect, QPoint
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QToolButton, QFrame,
    QStackedLayout, QMenu, QApplication
)
from PySide6.QtGui import (
    QColor, QIcon, QImageReader, QPainter, QPen, QPixmap, QBrush,
    QFontMetrics, QAction, QDrag
)
from PySide6.QtSvg import QSvgRenderer

from styles import theme
from utils import config
from utils.bucket_service import (
    describe, load_items, remove_item, clear_bucket, open_item,
    copy_to_clipboard, total_bytes, format_bytes, open_bucket_folder,
    create_drag_mime, get_drag_file_path
)

NOTCH_PADDING_X = 18
NOTCH_PADDING_Y = 12
HEADER_H = 22
CARD_W = 74
CARD_H = 70
CARD_GAP = 8
MAX_CARDS = 6
THUMB_PX = 128
PANEL_W = MAX_CARDS * CARD_W + (MAX_CARDS - 1) * CARD_GAP  # 484
PANEL_H = HEADER_H + 6 + CARD_H  # 98
NOTCH_WIDTH = PANEL_W + (NOTCH_PADDING_X * 2)  # 520
NOTCH_HEIGHT = PANEL_H + (NOTCH_PADDING_Y * 2)  # 122

BUCKET_NOTCH_WIDTH = NOTCH_WIDTH
BUCKET_NOTCH_HEIGHT = NOTCH_HEIGHT
BUCKET_PANEL_W = PANEL_W
BUCKET_PADDING_X = NOTCH_PADDING_X
BUCKET_PADDING_Y = NOTCH_PADDING_Y

BUCKET_UNHOVER_TIMEOUT_MS = 1200

DROP_TRAY_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24">'
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>'
    '<polyline points="7 10 12 15 17 10"></polyline>'
    '<line x1="12" y1="15" x2="12" y2="3"></line>'
    '</svg>'
)

FOLDER_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24">'
    '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>'
    '</svg>'
)

TRASH_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24">'
    '<polyline points="3 6 5 6 21 6"></polyline>'
    '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>'
    '</svg>'
)

CLOSE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" '
    'stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24">'
    '<line x1="18" y1="6" x2="6" y2="18"></line>'
    '<line x1="6" y1="6" x2="18" y2="18"></line>'
    '</svg>'
)

FILE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24"><path d="M14 3v5h5"></path>'
    '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>'
    '<path d="M8 13h8M8 17h5"></path></svg>'
)

LINK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.07 0l2.44-2.44a5 5 0 0 0-7.07-7.07L11 4.9"></path>'
    '<path d="M14 11a5 5 0 0 0-7.07 0L4.49 13.44a5 5 0 0 0 7.07 7.07L13 19.1"></path></svg>'
)

TEXT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
    'viewBox="0 0 24 24"><path d="M5 6h14M5 10h14M5 14h10M5 18h6"></path></svg>'
)

IMAGE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" '
    'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24">'
    '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>'
    '<circle cx="8.5" cy="8.5" r="1.5"></circle>'
    '<polyline points="21 15 16 10 5 21"></polyline>'
    '</svg>'
)

KIND_SVGS = {"file": FILE_SVG, "link": LINK_SVG, "text": TEXT_SVG, "image": IMAGE_SVG}

TYPE_COLORS = {
    "PDF": "#EF4444",
    "DOC": "#3B82F6", "DOCX": "#3B82F6", "RTF": "#3B82F6",
    "XLS": "#10B981", "XLSX": "#10B981", "CSV": "#10B981",
    "PPT": "#F59E0B", "PPTX": "#F59E0B",
    "ZIP": "#8B5CF6", "RAR": "#8B5CF6", "7Z": "#8B5CF6",
    "TXT": "#64748B", "MD": "#06B6D4", "LOG": "#64748B",
    "PY": "#38BDF8", "JS": "#FACC15", "HTML": "#F97316", "CSS": "#38BDF8",
    "MP3": "#EC4899", "WAV": "#EC4899", "MP4": "#8B5CF6", "MKV": "#8B5CF6"
}
DEFAULT_TYPE_COLOR = "#64748B"


def _render_svg_pixmap(svg_str: str, color: str = "#FFFFFF", size: int = 16) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg_str.replace("currentColor", color).encode("utf-8")))
    canvas = QPixmap(size * 2, size * 2)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter)
    painter.end()
    return canvas


def _render_type_badge(ext: str) -> QPixmap:
    label = (ext or "").lstrip(".").upper()[:4]
    band = QColor(TYPE_COLORS.get(label, DEFAULT_TYPE_COLOR))
    canvas = QPixmap(64, 64)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Document body
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#1E293B"))
    painter.drawRoundedRect(QRectF(10, 4, 44, 56), 6, 6)

    # Folded corner
    painter.setBrush(QColor("#334155"))
    painter.drawPolygon([QPointF(40, 4), QPointF(54, 18), QPointF(40, 18)])

    # Color band badge
    painter.setBrush(band)
    painter.drawRoundedRect(QRectF(10, 38, 44, 22), 4, 4)

    # Text inside badge
    painter.setPen(QColor("#FFFFFF"))
    font = painter.font()
    font.setPixelSize(11 if len(label) <= 3 else 9)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(QRectF(10, 38, 44, 22), int(Qt.AlignmentFlag.AlignCenter), label)
    painter.end()
    return canvas


class BucketItemCard(QFrame):
    """Rich interactive card representing a single captured item."""
    activated = Signal(dict)
    deleted = Signal(str)
    action_flashed = Signal(str)

    def __init__(self, item: dict, thumbs_cache: dict, accent: str, font_family: str, parent=None):
        super().__init__(parent)
        self.item = item
        self._thumbs = thumbs_cache
        self._accent = accent
        self._font = font_family
        self._is_hovered = False
        self._drag_start_pos = None
        self._is_drag_candidate = False

        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(self._make_tooltip())
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 5, 4, 5)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Thumbnail / Icon container
        self.lbl_icon = QLabel(self)
        self.lbl_icon.setFixedSize(36, 36)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet("background: transparent; border: none;")
        self._apply_icon()
        layout.addWidget(self.lbl_icon, 0, Qt.AlignmentFlag.AlignCenter)

        # 2. Elided title label
        self.lbl_title = QLabel(self)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(f"""
            color: #FFFFFF;
            font-family: '{self._font}', 'Segoe UI', sans-serif;
            font-size: 9.5px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        raw_title = item.get("title") or item.get("ext") or "Item"
        metrics = QFontMetrics(self.lbl_title.font())
        elided = metrics.elidedText(raw_title, Qt.TextElideMode.ElideMiddle, CARD_W - 8)
        self.lbl_title.setText(elided)
        layout.addWidget(self.lbl_title)

        # 3. Subtitle / size display box with border radius
        self.lbl_sub = QLabel(self)
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sub.setStyleSheet(f"""
            color: rgba(255, 255, 255, 180);
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 4px;
            padding: 1px 5px;
            font-family: '{self._font}', 'Segoe UI', sans-serif;
            font-size: 8px;
            font-weight: 600;
        """)
        sub_text = self._make_sub_text()
        self.lbl_sub.setText(sub_text)
        layout.addWidget(self.lbl_sub, 0, Qt.AlignmentFlag.AlignCenter)

        # 4. Floating Delete button (visible on hover)
        self.btn_del = QToolButton(self)
        self.btn_del.setFixedSize(16, 16)
        self.btn_del.setIcon(QIcon(_render_svg_pixmap(CLOSE_SVG, "#FFFFFF", 10)))
        self.btn_del.setIconSize(QSize(10, 10))
        self.btn_del.setToolTip("Delete this item")
        self.btn_del.setStyleSheet("""
            QToolButton {
                background: rgba(239, 68, 68, 0.85);
                border: none;
                border-radius: 8px;
            }
            QToolButton:hover {
                background: #EF4444;
            }
        """)
        self.btn_del.move(CARD_W - 19, 3)
        self.btn_del.clicked.connect(self._on_delete_clicked)
        self.btn_del.hide()

        self._apply_style()

    def _make_tooltip(self) -> str:
        kind = self.item.get("kind", "file")
        title = self.item.get("title") or self.item.get("ext") or "Item"
        if kind == "image":
            return f"{title}\n• Click to open\n• Drag to paste into folder, desktop, or chat"
        if kind == "file":
            return f"{title}\n• Click to open\n• Drag to paste into folder, desktop, or chat"
        if kind == "link":
            return f"{title}\n• Click to open in browser\n• Drag to paste link"
        if kind == "text":
            return f"{title}\n• Click to copy note\n• Drag to paste note into app or desktop"
        return f"{title}\n• Click to open • Drag to paste to target"

    def _make_sub_text(self) -> str:
        kind = self.item.get("kind", "")
        if kind == "link":
            return "Link"
        if kind == "text":
            return "Note"
        size = self.item.get("size")
        if size:
            return format_bytes(size)
        return (self.item.get("ext") or "").upper()[:4]

    def _apply_icon(self):
        kind = self.item.get("kind", "file")
        path = self.item.get("path", "")
        if kind == "image" and path:
            thumb = self._get_thumbnail(path)
            if thumb and not thumb.isNull():
                self.lbl_icon.setPixmap(thumb.scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                return
        if kind in ("image", "file"):
            ext = self.item.get("ext") or ""
            self.lbl_icon.setPixmap(_render_type_badge(ext).scaled(34, 34, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return
        glyph = KIND_SVGS.get(kind, FILE_SVG)
        color = self._accent if kind == "link" else "#FFFFFF"
        self.lbl_icon.setPixmap(_render_svg_pixmap(glyph, color, 20))

    def _get_thumbnail(self, path: str):
        if not path or not os.path.isfile(path):
            return None
        cached = self._thumbs.get(path)
        if cached is not None:
            return cached
        reader = QImageReader(path)
        reader.setAutoTransform(True)
        img = reader.read()
        if img.isNull():
            self._thumbs[path] = None
            return None
        pm = QPixmap.fromImage(img)
        self._thumbs[path] = pm
        return pm

    def _apply_style(self):
        border_col = self._accent if self._is_hovered else "rgba(255, 255, 255, 0.10)"
        bg_col = "rgba(255, 255, 255, 0.12)" if self._is_hovered else "rgba(255, 255, 255, 0.05)"
        self.setStyleSheet(f"""
            BucketItemCard {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
        """)

    def enterEvent(self, event):
        super().enterEvent(event)
        self._is_hovered = True
        self._apply_style()
        self.btn_del.show()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self._is_hovered = False
        self._apply_style()
        self.btn_del.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._is_drag_candidate = True
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if getattr(self, "_is_drag_candidate", False) and (event.buttons() & Qt.MouseButton.LeftButton):
            if self._drag_start_pos is not None:
                dist = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
                if dist >= QApplication.startDragDistance():
                    self._is_drag_candidate = False
                    self._start_drag()
                    event.accept()
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if getattr(self, "_is_drag_candidate", False):
                self._is_drag_candidate = False
                self.activated.emit(self.item)
                event.accept()
                return
        self._is_drag_candidate = False
        super().mouseReleaseEvent(event)

    def _find_bucket_widget(self):
        w = self.parent()
        while w is not None:
            if isinstance(w, NotchBucketWidget):
                return w
            w = w.parent()
        return None

    def _start_drag(self):
        parent_bucket = self._find_bucket_widget()
        notch = parent_bucket.notch if parent_bucket else None
        if notch:
            setattr(notch, "_is_dragging_out", True)
        if parent_bucket:
            setattr(parent_bucket, "_is_dragging_out", True)

        mime = create_drag_mime(self.item)
        drag = QDrag(self)
        drag.setMimeData(mime)

        pixmap = self._make_drag_pixmap()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))

        # Native drag loop
        action = drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)

        if notch:
            setattr(notch, "_is_dragging_out", False)
        if parent_bucket:
            setattr(parent_bucket, "_is_dragging_out", False)

        if action != Qt.DropAction.IgnoreAction:
            self.action_flashed.emit("✓ Dropped to target")
            if parent_bucket and hasattr(parent_bucket, "flash"):
                parent_bucket.flash("✓ Dropped to target")
            if notch and hasattr(notch, "bucket_collapse_timer"):
                notch.bucket_collapse_timer.start(1000)
        else:
            if notch and hasattr(notch, "bucket_collapse_timer"):
                notch.bucket_collapse_timer.start(1200)

    def _make_drag_pixmap(self) -> QPixmap:
        base = self.grab()
        if base.isNull():
            return QPixmap()
        canvas = QPixmap(base.size())
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(0.92)
        painter.drawPixmap(0, 0, base)
        painter.setPen(QPen(QColor(self._accent), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(1, 1, canvas.width() - 2, canvas.height() - 2), 12, 12)
        painter.end()
        return canvas

    def _on_delete_clicked(self):
        item_id = self.item.get("id")
        if item_id:
            self.deleted.emit(item_id)

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: #0F172A;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 8px;
                padding: 4px;
                font-family: '{self._font}', sans-serif;
                font-size: 11px;
            }}
            QMenu::item {{
                padding: 5px 16px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {self._accent};
                color: #000000;
            }}
        """)
        act_open = menu.addAction("Open")
        act_copy = menu.addAction("Copy to Clipboard")
        act_del = menu.addAction("Delete")

        action = menu.exec(self.mapToGlobal(pos))
        if action == act_open:
            self.activated.emit(self.item)
        elif action == act_copy:
            if copy_to_clipboard(self.item):
                self.action_flashed.emit("Copied to clipboard")
        elif action == act_del:
            self._on_delete_clicked()


class NotchBucketWidget(QWidget):
    """
    Modernized Drop Target & Bucket UI.
    - When dragging: displays glowing animated drop zone.
    - When browsing: displays rich card items, item count badge, folder button, clear button.
    """
    item_activated = Signal(str)
    dragging_changed = Signal(bool)

    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self._font = config.load_font_family("DM Sans")
        self._accent = config.load_accent_color(theme.ACCENT_COLOR)
        self._dragging = False
        self._thumbs = {}

        self.setAcceptDrops(True)

        self._hint_timer = QTimer(self)
        self._hint_timer.setSingleShot(True)
        self._hint_timer.timeout.connect(self._clear_hint)

        self._build_ui()

    def _build_ui(self):
        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)

        # -------------------------------------------------------------
        # VIEW 0: BROWSE VIEW (normal state)
        # -------------------------------------------------------------
        self.browse_widget = QWidget(self)
        browse_lay = QVBoxLayout(self.browse_widget)
        browse_lay.setContentsMargins(0, 0, 0, 0)
        browse_lay.setSpacing(6)

        # 1. Header Bar
        head_row = QHBoxLayout()
        head_row.setContentsMargins(0, 0, 0, 0)
        head_row.setSpacing(8)

        self.lbl_title = QLabel("BUCKET", self)
        self.lbl_title.setStyleSheet(f"""
            color: #FFFFFF;
            font-family: '{self._font}', 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1.2px;
            background: transparent;
            border: none;
        """)
        head_row.addWidget(self.lbl_title)

        self.lbl_badge = QLabel("0 ITEMS", self)
        self.lbl_badge.setStyleSheet(f"""
            color: {self._accent};
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 6px;
            padding: 1px 7px;
            font-family: '{self._font}', 'Segoe UI', sans-serif;
            font-size: 9px;
            font-weight: 700;
        """)
        head_row.addWidget(self.lbl_badge)

        self.lbl_hint = QLabel("", self)
        self.lbl_hint.setStyleSheet(f"""
            color: {self._accent};
            font-family: '{self._font}', 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: 600;
            background: transparent;
        """)
        head_row.addWidget(self.lbl_hint)
        head_row.addStretch(1)

        # Header Action Buttons
        self.btn_folder = QToolButton(self)
        self.btn_folder.setFixedSize(22, 22)
        self.btn_folder.setIcon(QIcon(_render_svg_pixmap(FOLDER_SVG, "#FFFFFF", 12)))
        self.btn_folder.setIconSize(QSize(12, 12))
        self.btn_folder.setToolTip("Open bucket folder in File Explorer")
        self.btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_tool_btn(self.btn_folder)
        self.btn_folder.clicked.connect(self._on_open_folder)
        head_row.addWidget(self.btn_folder)

        self.btn_clear = QToolButton(self)
        self.btn_clear.setFixedSize(22, 22)
        self.btn_clear.setIcon(QIcon(_render_svg_pixmap(TRASH_SVG, "#FFFFFF", 12)))
        self.btn_clear.setIconSize(QSize(12, 12))
        self.btn_clear.setToolTip("Clear all items from Bucket")
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_tool_btn(self.btn_clear)
        self.btn_clear.clicked.connect(self._on_clear_bucket)
        head_row.addWidget(self.btn_clear)

        self.btn_close = QToolButton(self)
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setIcon(QIcon(_render_svg_pixmap(CLOSE_SVG, "#FFFFFF", 11)))
        self.btn_close.setIconSize(QSize(11, 11))
        self.btn_close.setToolTip("Close bucket")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self._style_tool_btn(self.btn_close)
        self.btn_close.clicked.connect(self._on_close_clicked)
        head_row.addWidget(self.btn_close)

        browse_lay.addLayout(head_row)

        # 2. Items Cards Row
        self.cards_container = QWidget(self)
        self.cards_container.setAcceptDrops(True)
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(CARD_GAP)
        self.cards_layout.addStretch(1)
        browse_lay.addWidget(self.cards_container)

        # 3. Empty State Container
        self.empty_widget = QWidget(self)
        self.empty_widget.setAcceptDrops(True)
        empty_lay = QHBoxLayout(self.empty_widget)
        empty_lay.setContentsMargins(12, 14, 12, 14)
        empty_lay.setSpacing(12)
        self.empty_widget.setStyleSheet("""
            QWidget {
                background: rgba(255, 255, 255, 0.04);
                border: 1px dashed rgba(255, 255, 255, 0.14);
                border-radius: 12px;
            }
        """)

        lbl_empty_icon = QLabel(self.empty_widget)
        lbl_empty_icon.setPixmap(_render_svg_pixmap(DROP_TRAY_SVG, "rgba(255, 255, 255, 120)", 22))
        lbl_empty_icon.setStyleSheet("border: none; background: transparent;")
        lbl_empty_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        empty_lay.addWidget(lbl_empty_icon)

        empty_text_col = QVBoxLayout()
        empty_text_col.setSpacing(2)
        lbl_empty_title = QLabel("Bucket is empty", self.empty_widget)
        lbl_empty_title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lbl_empty_title.setStyleSheet(f"""
            color: #FFFFFF; font-family: '{self._font}', sans-serif;
            font-size: 11.5px; font-weight: 600; border: none; background: transparent;
        """)
        lbl_empty_sub = QLabel("Drag & drop files, links, images, or notes anywhere onto the notch", self.empty_widget)
        lbl_empty_sub.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        lbl_empty_sub.setStyleSheet(f"""
            color: rgba(255, 255, 255, 130); font-family: '{self._font}', sans-serif;
            font-size: 9.5px; border: none; background: transparent;
        """)
        empty_text_col.addWidget(lbl_empty_title)
        empty_text_col.addWidget(lbl_empty_sub)
        empty_lay.addLayout(empty_text_col, 1)

        browse_lay.addWidget(self.empty_widget)
        self.stack.addWidget(self.browse_widget)

        # -------------------------------------------------------------
        # VIEW 1: DROP ZONE VIEW (active while dragging over notch)
        # -------------------------------------------------------------
        self.drop_widget = QFrame(self)
        self.drop_widget.setObjectName("dropFrame")
        self.drop_widget.setAcceptDrops(True)
        drop_lay = QVBoxLayout(self.drop_widget)
        drop_lay.setContentsMargins(16, 10, 16, 10)
        drop_lay.setSpacing(4)
        drop_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Icon row
        lbl_drop_icon = QLabel(self.drop_widget)
        lbl_drop_icon.setPixmap(_render_svg_pixmap(DROP_TRAY_SVG, self._accent, 26))
        lbl_drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_drop_icon.setStyleSheet("border: none; background: transparent;")
        lbl_drop_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        drop_lay.addWidget(lbl_drop_icon, 0, Qt.AlignmentFlag.AlignCenter)

        # Headline
        self.lbl_drop_headline = QLabel("Release to Save in Bucket", self.drop_widget)
        self.lbl_drop_headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_drop_headline.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.lbl_drop_headline.setStyleSheet(f"""
            color: #FFFFFF;
            font-family: '{self._font}', 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 700;
            background: transparent;
            border: none;
        """)
        drop_lay.addWidget(self.lbl_drop_headline)

        # Formats pill row
        formats_row = QHBoxLayout()
        formats_row.setSpacing(6)
        formats_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for tag in ["📁 Files", "🖼️ Images", "🔗 Links", "📝 Text"]:
            lbl_tag = QLabel(tag, self.drop_widget)
            lbl_tag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            lbl_tag.setStyleSheet(f"""
                color: rgba(255, 255, 255, 170);
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 5px;
                padding: 1px 6px;
                font-family: '{self._font}', sans-serif;
                font-size: 8.5px;
                font-weight: 600;
            """)
            formats_row.addWidget(lbl_tag)
        drop_lay.addLayout(formats_row)

        self._apply_drop_frame_style()
        self.stack.addWidget(self.drop_widget)

    def _style_tool_btn(self, btn: QToolButton):
        btn.setStyleSheet(f"""
            QToolButton {{
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 2px;
            }}
            QToolButton:hover {{
                background: {self._accent};
                border-color: {self._accent};
            }}
        """)

    def _apply_drop_frame_style(self):
        self.drop_widget.setStyleSheet(f"""
            #dropFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(56, 189, 248, 0.18), stop:1 rgba(15, 23, 42, 0.70));
                border: 2px dashed {self._accent};
                border-radius: 14px;
            }}
        """)

    # -- state management -----------------------------------------------------
    def preferred_height(self):
        return PANEL_H

    def set_dragging(self, active: bool):
        active = bool(active)
        if active == self._dragging:
            return
        self._dragging = active
        self.stack.setCurrentIndex(1 if active else 0)
        self.dragging_changed.emit(active)

    def flash(self, message: str):
        """Show a temporary feedback toast on the header."""
        self._hint_timer.stop()
        self.lbl_hint.setText(message)
        self._hint_timer.start(2400)

    def _clear_hint(self):
        self.lbl_hint.setText("")

    def reload(self):
        """Refresh items, badge count, and cards layout."""
        self._font = config.load_font_family("DM Sans")
        self._accent = config.load_accent_color(theme.ACCENT_COLOR)
        self._apply_drop_frame_style()
        self._style_tool_btn(self.btn_folder)
        self._style_tool_btn(self.btn_clear)
        self._style_tool_btn(self.btn_close)

        items = load_items()
        count = len(items)
        bytes_total = total_bytes(items)

        # Update Badge
        if count == 0:
            self.lbl_badge.setText("EMPTY")
            self.lbl_badge.setStyleSheet(f"""
                color: rgba(255, 255, 255, 120);
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 1px 7px;
                font-family: '{self._font}', sans-serif;
                font-size: 8.5px;
                font-weight: 700;
            """)
        else:
            self.lbl_badge.setText(f"{count} ITEM{'S' if count != 1 else ''} • {format_bytes(bytes_total)}")
            self.lbl_badge.setStyleSheet(f"""
                color: {self._accent};
                background: rgba(56, 189, 248, 0.12);
                border: 1px solid rgba(56, 189, 248, 0.25);
                border-radius: 6px;
                padding: 1px 7px;
                font-family: '{self._font}', sans-serif;
                font-size: 8.5px;
                font-weight: 700;
            """)

        # Clear existing cards
        while self.cards_layout.count() > 1:
            w = self.cards_layout.takeAt(0).widget()
            if w:
                w.deleteLater()

        # Populate cards
        for item in items[:MAX_CARDS]:
            card = BucketItemCard(item, self._thumbs, self._accent, self._font, self.cards_container)
            card.activated.connect(self._on_card_activated)
            card.deleted.connect(self._on_card_deleted)
            card.action_flashed.connect(self.flash)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)

        has_items = count > 0
        self.cards_container.setVisible(has_items)
        self.empty_widget.setVisible(not has_items)
        self.btn_clear.setVisible(has_items)

    def _on_card_activated(self, item: dict):
        kind = item.get("kind", "")
        if kind == "text":
            if copy_to_clipboard(item):
                self.flash("✓ Copied note to clipboard")
        else:
            if open_item(item):
                self.flash("✓ Opened item")
        item_id = item.get("id")
        if item_id:
            self.item_activated.emit(item_id)

    def _on_card_deleted(self, item_id: str):
        remove_item(item_id)
        self.flash("Deleted item")
        self.reload()

    def _on_open_folder(self):
        open_bucket_folder()
        self.flash("Opened folder")

    def _on_clear_bucket(self):
        clear_bucket()
        self.flash("Cleared all items")
        self.reload()

    def _on_close_clicked(self):
        if self.notch and hasattr(self.notch, "collapse_bucket"):
            self.notch.collapse_bucket()

    # -- drag and drop event forwarding ---------------------------------------
    def dragEnterEvent(self, event):
        if getattr(self, "_is_dragging_out", False) or (self.notch and getattr(self.notch, "_is_dragging_out", False)):
            event.ignore()
            return
        if self.notch and hasattr(self.notch, "dragEnterEvent"):
            self.notch.dragEnterEvent(event)
        else:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if getattr(self, "_is_dragging_out", False) or (self.notch and getattr(self.notch, "_is_dragging_out", False)):
            event.ignore()
            return
        if self.notch and hasattr(self.notch, "dragMoveEvent"):
            self.notch.dragMoveEvent(event)
        else:
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        if getattr(self, "_is_dragging_out", False) or (self.notch and getattr(self.notch, "_is_dragging_out", False)):
            return
        from PySide6.QtGui import QCursor
        pos = self.mapFromGlobal(QCursor.pos())
        if self.rect().contains(pos):
            return
        if self.notch and hasattr(self.notch, "dragLeaveEvent"):
            self.notch.dragLeaveEvent(event)
        else:
            super().dragLeaveEvent(event)

    def dropEvent(self, event):
        if getattr(self, "_is_dragging_out", False) or (self.notch and getattr(self.notch, "_is_dragging_out", False)):
            event.ignore()
            return
        if self.notch and hasattr(self.notch, "dropEvent"):
            self.notch.dropEvent(event)
        else:
            event.acceptProposedAction()
