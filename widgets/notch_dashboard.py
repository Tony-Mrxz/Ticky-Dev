# widgets/notch_dashboard.py
"""Dashboard blocks shown under the State 2 header row: screen time, task totals, shortcuts."""

from PySide6.QtCore import Qt, Signal, QByteArray, QSize, QTimer
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QGridLayout, QVBoxLayout, QLabel,
                               QToolButton, QFrame)
from PySide6.QtGui import QColor, QFontMetrics, QIcon, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer

from styles import theme
from utils import config
from utils.favicon_cache import FaviconCache
from utils.screen_time import display_name, format_duration

NOTCH_PADDING_X = 22
NOTCH_BOTTOM_GAP = 20  # clear space under the blocks, where the page dots live
HEADER_ROW_H = 62

SCREEN_W = 206
TASKS_W = 112
SHORTCUTS_W = 190
BLOCK_GAP = 12
PANEL_W = SCREEN_W + BLOCK_GAP + TASKS_W + BLOCK_GAP + SHORTCUTS_W  # 532
BLOCK_MARGIN_Y = 9

REFRESH_INTERVAL_MS = 20000
SCREEN_APP_ROWS = 2
SHORTCUT_COLS = 3
SHORTCUT_ROWS = 2
TILE_W = 50
TILE_H = 46
TILE_GAP = 6
TILE_RADIUS = 14
PANEL_H = SHORTCUT_ROWS * TILE_H + (SHORTCUT_ROWS - 1) * TILE_GAP + BLOCK_MARGIN_Y * 2  # 116
NOTCH_WIDTH = PANEL_W + (NOTCH_PADDING_X * 2)  # 576
NOTCH_HEIGHT = HEADER_ROW_H + PANEL_H + NOTCH_BOTTOM_GAP  # 198

GLOBE_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'viewBox="0 0 24 24">'
    '<circle cx="12" cy="12" r="9"></circle>'
    '<path d="M3 12h18M12 3a14.5 14.5 0 0 1 0 18a14.5 14.5 0 0 1 0-18z"></path></svg>'
)


def _plus_icon(size=26, stroke=2.8):
    """The header add button's plus, used bare on an empty shortcut tile."""
    canvas = QPixmap(size * 2, size * 2)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#FFFFFF"), stroke)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    mid = float(size)
    arm = size * 0.52
    painter.drawLine(mid - arm, mid, mid + arm, mid)
    painter.drawLine(mid, mid - arm, mid, mid + arm)
    painter.end()
    return canvas


class _UsageBar(QWidget):
    """Thin rounded track showing one app's share of the day."""

    def __init__(self, accent, parent=None):
        super().__init__(parent)
        self._accent = accent
        self._ratio = 0.0
        self.setFixedHeight(4)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_ratio(self, ratio):
        self._ratio = max(0.0, min(1.0, float(ratio or 0.0)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 22))
        painter.drawRoundedRect(0.0, 0.0, w, h, h / 2.0, h / 2.0)
        if self._ratio > 0.005:
            painter.setBrush(QColor(self._accent))
            painter.drawRoundedRect(0.0, 0.0, max(h, w * self._ratio), h, h / 2.0, h / 2.0)


class NotchDashboardWidget(QWidget):
    """The glanceable blocks that fill the lower part of the hovered notch."""

    shortcut_activated = Signal(int)

    def __init__(self, notch_widget, provider=None, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self._provider = provider
        self._font = config.load_font_family("DM Sans")
        self._accent = config.load_accent_color(theme.ACCENT_COLOR)
        self._shortcuts = []
        self._rows = []
        self._favicons = FaviconCache.get_instance()
        self._favicons.loaded.connect(lambda _domain: self._apply_shortcuts(self._shortcuts))
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(REFRESH_INTERVAL_MS)
        self._refresh_timer.timeout.connect(self.reload)
        self._build_ui()

    # -- construction ---------------------------------------------------------
    def _title(self, text):
        return self._label(text, 9, "rgba(255, 255, 255, 130)", bold=True)

    def _label(self, text, size, color, bold=False):
        lbl = QLabel(text, self)
        lbl.setStyleSheet(
            f"color: {color}; font-family: '{self._font}', 'Segoe UI', sans-serif; "
            f"font-size: {size}px; font-weight: {'700' if bold else '400'}; "
            f"background: transparent; border: none;")
        return lbl

    def _block(self, heading, width):
        frame = QFrame(self)
        frame.setFixedWidth(width)
        frame.setStyleSheet(
            "QFrame { background: rgba(255, 255, 255, 8); "
            "border: 1px solid rgba(255, 255, 255, 16); border-radius: 12px; }")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, BLOCK_MARGIN_Y, 12, BLOCK_MARGIN_Y)
        lay.setSpacing(4)
        if heading:
            lay.addWidget(self._title(heading))
        return frame, lay

    def _svg_icon(self, svg, color="#FFFFFF", size=14):
        renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
        pm = QPixmap(size * 2, size * 2)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        renderer.render(painter)
        painter.end()
        return pm

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(BLOCK_GAP)

        # Screen time: today's total plus the busiest apps.
        screen, screen_lay = self._block("SCREEN TIME TODAY", SCREEN_W)
        self.lbl_screen_total = self._label("--", 19, "#FFFFFF", bold=True)
        screen_lay.addWidget(self.lbl_screen_total)
        for _ in range(SCREEN_APP_ROWS):
            row = QHBoxLayout()
            row.setSpacing(6)
            name = self._label("", 10, "rgba(255, 255, 255, 190)")
            name.setMinimumWidth(0)
            bar = _UsageBar(self._accent)
            bar.setFixedWidth(46)
            secs = self._label("", 10, "rgba(255, 255, 255, 130)")
            row.addWidget(name, 1)
            row.addWidget(bar, 0)
            row.addWidget(secs, 0)
            screen_lay.addLayout(row)
            self._rows.append((name, bar, secs))
        screen_lay.addStretch(1)
        root.addWidget(screen)

        # Totals for the things Ticky already tracks.
        tasks, tasks_lay = self._block("TASKS", TASKS_W)
        self.lbl_tasks_total = self._label("0", 19, "#FFFFFF", bold=True)
        tasks_lay.addWidget(self.lbl_tasks_total)
        self.lbl_tasks_notes = self._label("Notes  0", 10, "rgba(255, 255, 255, 160)")
        tasks_lay.addWidget(self.lbl_tasks_notes)
        self.lbl_tasks_reminders = self._label("Reminders  0", 10, "rgba(255, 255, 255, 160)")
        tasks_lay.addWidget(self.lbl_tasks_reminders)
        tasks_lay.addStretch(1)
        root.addWidget(tasks)

        # Website shortcuts in a three by two grid, icons only.
        shortcuts, shortcuts_lay = self._block(None, SHORTCUTS_W)
        tiles = QGridLayout()
        tiles.setSpacing(TILE_GAP)
        self.shortcut_buttons = []
        for index in range(config.NOTCH_SHORTCUT_SLOTS):
            btn = QToolButton()
            btn.setFixedSize(TILE_W, TILE_H)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            btn.clicked.connect(lambda _checked=False, i=index: self.shortcut_activated.emit(i))
            tiles.addWidget(btn, index // SHORTCUT_COLS, index % SHORTCUT_COLS)
            self.shortcut_buttons.append(btn)
        shortcuts_lay.addLayout(tiles)
        shortcuts_lay.addStretch(1)
        root.addWidget(shortcuts)

    # -- state ----------------------------------------------------------------
    def set_provider(self, provider):
        self._provider = provider

    def preferred_height(self):
        return PANEL_H

    def reload(self):
        data = {}
        if self._provider:
            try:
                data = self._provider() or {}
            except Exception:
                data = {}
        self._font = config.load_font_family("DM Sans")
        self._accent = config.load_accent_color(theme.ACCENT_COLOR)
        self._apply_screen_time(data.get("apps", []), data.get("screen_total", 0.0))
        self._apply_counts(data.get("tasks", 0), data.get("notes", 0), data.get("reminders", 0))
        self._apply_shortcuts(data.get("shortcuts", []))

    def _apply_screen_time(self, apps, total):
        self.lbl_screen_total.setText(format_duration(total) if total else "No data yet")
        self.lbl_screen_total.setStyleSheet(
            f"color: #FFFFFF; font-family: '{self._font}', 'Segoe UI', sans-serif; "
            f"font-size: 19px; font-weight: 700; background: transparent; border: none;")
        busiest = max((seconds for _name, seconds in apps), default=0.0) or 1.0
        for (name_lbl, bar, secs_lbl), pair in zip(self._rows, list(apps) + [("", 0.0)] * SCREEN_APP_ROWS):
            app, seconds = pair
            metrics = QFontMetrics(name_lbl.font())
            name_lbl.setText(metrics.elidedText(display_name(app), Qt.TextElideMode.ElideRight, 96) if app
                             else "—")
            bar.set_ratio(seconds / busiest if app else 0.0)
            secs_lbl.setText(format_duration(seconds) if app else "")

    def _apply_counts(self, tasks, notes, reminders=0):
        self.lbl_tasks_total.setText(str(int(tasks)))
        self.lbl_tasks_notes.setText(f"Notes  {int(notes)}")
        self.lbl_tasks_reminders.setText(f"Reminders  {int(reminders)}")
        self.lbl_tasks_total.setToolTip(f"{int(tasks)} active task{'s' if int(tasks) != 1 else ''}")
        self.lbl_tasks_notes.setToolTip(f"{int(notes)} saved note{'s' if int(notes) != 1 else ''}")
        self.lbl_tasks_reminders.setToolTip(f"{int(reminders)} upcoming reminder{'s' if int(reminders) != 1 else ''}")

    def _apply_shortcuts(self, slots):
        self._shortcuts = list(slots)
        for index, btn in enumerate(self.shortcut_buttons):
            slot = self._shortcuts[index] if index < len(self._shortcuts) else {}
            label = (slot.get("label") or "").strip()
            url = (slot.get("url") or "").strip()
            filled = bool(url)
            if filled:
                icon = self._favicons.icon_for(url)
                if icon is None:
                    btn.setIcon(QIcon(self._svg_icon(GLOBE_SVG, "#FFFFFF", 18)))
                    btn.setIconSize(QSize(18, 18))
                else:
                    btn.setIcon(icon)
                    btn.setIconSize(QSize(30, 30))
                btn.setToolTip(f"{label}\n{url}" if label else url)
            else:
                btn.setIcon(QIcon(_plus_icon()))
                btn.setIconSize(QSize(24, 24))
                btn.setToolTip("Add this shortcut in Ticky settings")
            btn.setText("")
            btn.setStyleSheet(f"""
                QToolButton {{
                    background: {'rgba(255, 255, 255, 12)' if filled else 'rgba(255, 255, 255, 6)'};
                    border: 1px solid {'rgba(255, 255, 255, 26)' if filled else 'rgba(255, 255, 255, 16)'};
                    border-radius: {TILE_RADIUS}px;
                }}
                QToolButton:hover {{
                    background: rgba(255, 255, 255, 26);
                    border: 1px solid {self._accent};
                }}
            """)
            btn.setEnabled(True)

    # -- lifecycle ------------------------------------------------------------
    def showEvent(self, event):
        self.reload()
        if not self._refresh_timer.isActive():
            self._refresh_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self._refresh_timer.stop()
        super().hideEvent(event)
