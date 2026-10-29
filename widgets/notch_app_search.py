# widgets/notch_app_search.py
"""
System-wide app, file, and web search widget for the Ticky Notch.

Results are composed as matching applications first, then a Google search
action, then matching files and folders. File matching runs on a background
worker, so typing never blocks on filesystem scans.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal, QTimer, QByteArray
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QSizePolicy
)
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QFontMetrics
from PySide6.QtSvg import QSvgRenderer

from styles import theme
from utils import config
from utils.app_indexer import AppIndexer
from utils.app_usage import AppUsageStore
from utils.file_indexer import FileIndexer, open_path
from utils.web_search import open_google_search
from widgets.app_icon_service import AppIconService

VISIBLE_ROWS = 4
ROW_HEIGHT = 44
FILE_RESULT_LIMIT = 2

SEARCH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M10 2a8 8 0 0 1 6.32 12.906l5.387 5.387a1 1 0 0 1-1.414 1.414l-5.387-5.387A8 8 0 1 1 10 2m0 2a6 6 0 1 0 0 12 6 6 0 0 0 0-12"/>
</svg>"""

GOOGLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/>
<path fill="#FF3D00" d="m6.306 14.691 6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"/>
<path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/>
<path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/>
</svg>"""


def render_svg(svg: str, size: int) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


@dataclass(slots=True)
class SearchResult:
    kind: str  # "app", "google", "file"
    title: str
    subtitle: str
    icon_key: str | None = None
    payload: object = None
    hint: str = "Open ↵"

    @property
    def key(self) -> str:
        if self.kind == "app":
            return f"app:{self.payload.usage_key}"
        if self.kind == "file":
            return f"file:{self.payload.path.casefold()}"
        return "google"


def app_result(app) -> SearchResult:
    return SearchResult(
        kind="app",
        title=app.name,
        subtitle=app.category,
        icon_key=app.icon_key,
        payload=app,
        hint="Launch ↵",
    )


def google_result(query: str) -> SearchResult:
    query = query.strip()
    return SearchResult(
        kind="google",
        title=f'Search Google for "{query}"',
        subtitle="Open in your default browser",
        payload=query,
        hint="Search ↵",
    )


def file_result(item) -> SearchResult:
    return SearchResult(
        kind="file",
        title=item.name,
        subtitle=f"{item.type_label()} · {item.parent_label()}",
        icon_key=item.icon_key,
        payload=item,
        hint="Open ↵",
    )


def compose_results(app_matches, query: str, file_matches=()) -> list[SearchResult]:
    """Order results as applications, then Google, then files and folders."""
    results = [app_result(app) for app in app_matches]
    if query.strip():
        results.append(google_result(query))
    results.extend(file_result(item) for item in file_matches)
    return results


class SearchInputBox(QLineEdit):
    """Clean borderless line edit supporting Up/Down arrow navigation and Escape."""
    escape_pressed = Signal()
    navigate_down = Signal()
    navigate_up = Signal()
    enter_pressed = Signal()

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            return
        elif key == Qt.Key.Key_Down:
            self.navigate_down.emit()
            return
        elif key == Qt.Key.Key_Up:
            self.navigate_up.emit()
            return
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.enter_pressed.emit()
            return
        super().keyPressEvent(event)


class SearchResultRow(QWidget):
    """Interactive row for an application, web search, file, or folder."""
    clicked = Signal(object)

    def __init__(
        self,
        result: SearchResult,
        icon: QPixmap | None = None,
        parent=None,
        font_family: str | None = None,
    ):
        super().__init__(parent)
        self.result = result
        self._hovered = False
        self._selected = False

        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        self.icon_lbl = QLabel(self)
        self.icon_lbl.setFixedSize(26, 26)
        self.icon_lbl.setStyleSheet("background: transparent; border: none;")
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if icon is not None and not icon.isNull():
            self.icon_lbl.setPixmap(icon)

        layout.addWidget(self.icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        font_family = font_family or config.load_font_family("DM Sans")
        self._title_font_family = font_family

        self._title = result.title
        self._subtitle = result.subtitle

        self.title_lbl = QLabel(self)
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title_lbl.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 12px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(self.title_lbl)

        self.sub_lbl = QLabel(self)
        self.sub_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.sub_lbl.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.42);
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 9.5px;
                font-weight: 400;
                background: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(self.sub_lbl)

        layout.addLayout(text_layout, 1)

        self.hint_lbl = QLabel(result.hint, self)
        self.hint_lbl.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.55);
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 4px;
                padding: 2px 7px;
            }}
        """)
        self.hint_lbl.hide()
        layout.addWidget(self.hint_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        if result.kind == "file":
            self.setToolTip(result.payload.path)
        elif result.kind == "google":
            self.setToolTip(result.payload)

        self._apply_elide()

    def _apply_elide(self):
        available = self.width() - 118
        if available <= 24:
            return
        title_metrics = QFontMetrics(self.title_lbl.font())
        sub_metrics = QFontMetrics(self.sub_lbl.font())
        self.title_lbl.setText(
            title_metrics.elidedText(self._title, Qt.TextElideMode.ElideRight, available)
        )
        self.sub_lbl.setText(
            sub_metrics.elidedText(self._subtitle, Qt.TextElideMode.ElideRight, available)
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_elide()

    def set_icon(self, pixmap: QPixmap):
        if pixmap is not None and not pixmap.isNull():
            self.icon_lbl.setPixmap(pixmap)

    def set_selected(self, selected: bool):
        self._selected = selected
        if self._selected or self._hovered:
            self.hint_lbl.show()
        else:
            self.hint_lbl.hide()
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.hint_lbl.show()
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        if not self._selected:
            self.hint_lbl.hide()
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.result)
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 1, -2, -1)

        if self._selected:
            painter.setBrush(QColor(255, 255, 255, 26))
            painter.setPen(QPen(QColor(255, 255, 255, 50), 1.0))
            painter.drawRoundedRect(rect, 8, 8)
        elif self._hovered:
            painter.setBrush(QColor(255, 255, 255, 22))
            painter.setPen(QPen(QColor(255, 255, 255, 36), 0.8))
            painter.drawRoundedRect(rect, 8, 8)


class NotchAppSearchWidget(QWidget):
    """
    Embedded widget that hosts the search input box and results scroll area.
    Communicates with NotchWidget to dynamically resize vertically when characters are entered.
    """
    request_geometry_update = Signal(int)  # target height
    app_launched = Signal(object)
    closed = Signal()
    index_updated = Signal()

    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self.selected_index = -1
        self.rows = []
        self.current_app_matches = []
        self.current_file_matches = []
        self._file_results_query = ""
        self._results_query = ""
        self._active_query = ""
        self._google_icon: QPixmap | None = None

        self._indexer = AppIndexer.get_instance()
        self._files = FileIndexer.get_instance()
        self._usage = AppUsageStore.get_instance()
        self._icons = AppIconService.get_instance()

        # Coalesce keystrokes; the indexes are in memory, so 60 ms is enough to
        # avoid rebuilding rows for every intermediate character.
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(60)
        self._search_timer.timeout.connect(self._run_search)

        self._indexer.add_listener(self.index_updated.emit)
        self.index_updated.connect(self._rerun_search)
        self._files.index_ready.connect(self._rerun_search)
        self._files.results_ready.connect(self._on_file_results)
        self._icons.icon_ready.connect(self._on_icon_ready)

        self.init_ui()

    def init_ui(self):
        font_family = config.load_font_family("DM Sans")
        self._font_family = font_family
        accent = theme.ACCENT_COLOR

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 5, 12, 8)
        main_layout.setSpacing(5)

        # 1. Top Search Bar Row
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(8)

        self.search_icon_lbl = QLabel(self)
        self.search_icon_lbl.setFixedSize(18, 18)
        self.search_icon_lbl.setStyleSheet("background: transparent; border: none;")
        self._render_search_icon()
        top_bar.addWidget(self.search_icon_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self.search_input = SearchInputBox(self)
        self.search_input.setPlaceholderText("Search apps, files, or the web...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: #FFFFFF;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                padding: 3px 4px;
                selection-background-color: {accent};
                selection-color: #FFFFFF;
            }}
            QLineEdit::placeholder {{
                color: rgba(255, 255, 255, 0.40);
                font-weight: 400;
            }}
        """)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.escape_pressed.connect(self.close_search)
        self.search_input.navigate_down.connect(self._navigate_down)
        self.search_input.navigate_up.connect(self._navigate_up)
        self.search_input.enter_pressed.connect(self._launch_selected)
        top_bar.addWidget(self.search_input, 1)

        self.esc_badge = QLabel("Esc", self)
        self.esc_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.esc_badge.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.55);
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 600;
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 4px;
                padding: 2px 7px;
            }}
            QLabel:hover {{
                color: #FFFFFF;
                background: rgba(255, 255, 255, 0.16);
                border-color: rgba(255, 255, 255, 0.30);
            }}
        """)
        self.esc_badge.mousePressEvent = lambda e: self.close_search()
        top_bar.addWidget(self.esc_badge, 0, Qt.AlignmentFlag.AlignVCenter)

        main_layout.addLayout(top_bar)

        # 2. Glowing separator line
        self.separator = QFrame(self)
        self.separator.setFixedHeight(1)
        self.separator.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 255, 255, 0),
                    stop:0.5 rgba(255, 255, 255, 0.14),
                    stop:1 rgba(255, 255, 255, 0));
                border: none;
            }
        """)
        self.separator.hide()
        main_layout.addWidget(self.separator)

        # 3. Results scroll area (4 rows visible, the rest scrollable)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
                margin: 0px 1px 0px 1px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.22);
                border-radius: 2px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.45);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.scroll.hide()

        self.results_container = QWidget()
        self.results_container.setStyleSheet("background: transparent;")
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 2, 0)
        self.results_layout.setSpacing(2)
        self.results_layout.addStretch(1)

        self.scroll.setWidget(self.results_container)
        main_layout.addWidget(self.scroll, 1)

    def _render_search_icon(self):
        svg_str = SEARCH_SVG.replace("COLOR_PLACEHOLDER", theme.ACCENT_COLOR)
        self.search_icon_lbl.setPixmap(render_svg(svg_str, 18))

    def _google_pixmap(self) -> QPixmap:
        if self._google_icon is None:
            self._google_icon = render_svg(GOOGLE_SVG, 22)
        return self._google_icon

    def reset_state(self):
        """Prepare widget for a fresh search session."""
        self._search_timer.stop()
        self._active_query = ""
        self._render_search_icon()
        self.search_input.clear()
        self._clear_results()
        self.separator.hide()
        self.scroll.hide()

    def focus_input(self):
        """Ensure input box receives immediate keyboard focus."""
        self.search_input.setFocus()
        self.search_input.selectAll()

    def _clear_row_widgets(self):
        while self.results_layout.count() > 1:
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.rows = []
        self.selected_index = -1

    def _clear_results(self):
        self._clear_row_widgets()
        self.current_app_matches = []
        self.current_file_matches = []
        self._file_results_query = ""
        self._results_query = ""

    def _selected_key(self) -> str | None:
        if 0 <= self.selected_index < len(self.rows):
            return self.rows[self.selected_index].result.key
        return None

    def _on_search_text_changed(self, text: str):
        query = text.strip()
        self._active_query = query
        self._search_timer.stop()

        if not query:
            self._clear_results()
            self.separator.hide()
            self.scroll.hide()
            self.request_geometry_update.emit(48)
            return

        self._search_timer.start()

    def _flush_pending_search(self):
        """Run a debounced search immediately, e.g. when Enter/arrows are pressed."""
        if self._search_timer.isActive():
            self._search_timer.stop()
            self._run_search()

    def _rerun_search(self):
        """An index changed in the background; refresh the current results."""
        if not self._active_query:
            return
        self._search_timer.stop()
        self._run_search()

    def _on_file_results(self, query: str, results):
        if query != self._active_query:
            return
        self.current_file_matches = list(results or [])
        self._file_results_query = query
        self._rebuild_results()

    def _on_icon_ready(self, key: str):
        pixmap = self._icons.cached(key)
        if pixmap is None:
            return
        for row in self.rows:
            if row.result.icon_key == key:
                row.set_icon(pixmap)

    def _run_search(self):
        query = self._active_query
        if not query:
            return

        matches = (
            self._indexer.search(query, limit=40, usage=self._usage)
            if self._indexer.is_ready
            else []
        )

        if self._file_results_query != query:
            self.current_file_matches = []
            self._file_results_query = query
        self._files.search_async(query, limit=FILE_RESULT_LIMIT)

        self._rebuild_results(matches, preserve_selection=(query == self._results_query))

    def _rebuild_results(self, app_matches=None, preserve_selection: bool = True):
        query = self._active_query
        if not query:
            return

        if app_matches is not None:
            self.current_app_matches = list(app_matches)

        selected_key = self._selected_key() if preserve_selection else None
        scroll_value = self.scroll.verticalScrollBar().value() if preserve_selection else 0

        self._clear_row_widgets()
        self._results_query = query

        results = compose_results(
            self.current_app_matches,
            query,
            self.current_file_matches if self._file_results_query == query else (),
        )

        if not results:
            self.separator.hide()
            self.scroll.hide()
            self.request_geometry_update.emit(94)
            return

        self.separator.show()
        self.scroll.show()

        placeholder = self._icons.placeholder()
        for result in results:
            if result.kind == "google":
                icon = self._google_pixmap()
            else:
                icon = self._icons.cached(result.icon_key) or placeholder
            row = SearchResultRow(result, icon, self.results_container, self._font_family)
            row.clicked.connect(self._activate_result)
            self.results_layout.insertWidget(self.results_layout.count() - 1, row)
            self.rows.append(row)
            if result.icon_key:
                self._icons.request(result.payload)

        self.selected_index = 0
        if selected_key:
            for index, row in enumerate(self.rows):
                if row.result.key == selected_key:
                    self.selected_index = index
                    break
        self.rows[self.selected_index].set_selected(True)

        visible_rows = min(len(results), VISIBLE_ROWS)
        scroll_height = visible_rows * ROW_HEIGHT
        self.scroll.setFixedHeight(scroll_height)
        self.scroll.verticalScrollBar().setValue(scroll_value)

        # Header bar (46px) + separator (6px) + scroll_height + bottom padding (10px)
        self.request_geometry_update.emit(46 + 6 + scroll_height + 10)

    def _navigate_down(self):
        self._flush_pending_search()
        if not self.rows:
            return
        if self.selected_index >= 0 and self.selected_index < len(self.rows):
            self.rows[self.selected_index].set_selected(False)
        self.selected_index = (self.selected_index + 1) % len(self.rows)
        selected_row = self.rows[self.selected_index]
        selected_row.set_selected(True)
        self.scroll.ensureWidgetVisible(selected_row)

    def _navigate_up(self):
        self._flush_pending_search()
        if not self.rows:
            return
        if self.selected_index >= 0 and self.selected_index < len(self.rows):
            self.rows[self.selected_index].set_selected(False)
        self.selected_index = (self.selected_index - 1 + len(self.rows)) % len(self.rows)
        selected_row = self.rows[self.selected_index]
        selected_row.set_selected(True)
        self.scroll.ensureWidgetVisible(selected_row)

    def _launch_selected(self):
        self._flush_pending_search()
        if 0 <= self.selected_index < len(self.rows):
            self._activate_result(self.rows[self.selected_index].result)
        elif self.rows:
            self._activate_result(self.rows[0].result)

    def _activate_result(self, result: SearchResult):
        if result.kind == "app":
            app = result.payload
            self._usage.record(self._active_query, app.usage_key)
            self._indexer.launch(app)
        elif result.kind == "google":
            open_google_search(result.payload)
        elif result.kind == "file":
            open_path(result.payload.path)
        else:
            return
        self.app_launched.emit(result)

    def close_search(self):
        self.closed.emit()
