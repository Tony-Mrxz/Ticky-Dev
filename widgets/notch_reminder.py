# widgets/notch_reminder.py
import datetime
import uuid
from PySide6.QtCore import Qt, Signal, QRectF, QPointF, QPropertyAnimation, QEasingCurve, Property, QTimer, QByteArray, QEvent, QSize
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QScrollArea, QApplication
)
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPen, QLinearGradient, QCursor, QIcon, QPixmap
from PySide6.QtSvg import QSvgRenderer
from styles import theme
from utils import config

TICK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m10 15.586-3.293-3.293-1.414 1.414L10 18.414l9.707-9.707-1.414-1.414z"></path>
</svg>"""

CROSS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m16.192 6.344-4.243 4.242-4.242-4.242-1.414 1.414L10.535 12l-4.242 4.242 1.414 1.414 4.242-4.242 4.243 4.242 1.414-1.414L13.364 12l4.242-4.242z"></path>
</svg>"""

TRASH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M5 20a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8h2V6h-4V4a2 2 0 0 0-2-2h-6a2 2 0 0 0-2 2v2H3v2h2zM9 4h6v2H9zM8 8h9v12H7V8z"></path>
</svg>"""

X_CIRCLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M14.83 7.76 12 10.59 9.17 7.76 7.76 9.17 10.59 12l-2.83 2.83 1.41 1.41L12 13.41l2.83 2.83 1.41-1.41L13.41 12l2.83-2.83z"></path><path d="M12 2C9.33 2 6.82 3.04 4.93 4.93S2 9.33 2 12s1.04 5.18 2.93 7.07c1.95 1.95 4.51 2.92 7.07 2.92s5.12-.97 7.07-2.92S22 14.67 22 12s-1.04-5.18-2.93-7.07A9.93 9.93 0 0 0 12 2m5.66 15.66c-3.12 3.12-8.19 3.12-11.31 0-1.51-1.51-2.34-3.52-2.34-5.66s.83-4.15 2.34-5.66S9.87 4 12.01 4s4.15.83 5.66 2.34 2.34 3.52 2.34 5.66-.83 4.15-2.34 5.66Z"></path>
</svg>"""


def svg_icon(svg_template: str, color: str, size: int = 14) -> QIcon:
    svg = svg_template.replace("COLOR_PLACEHOLDER", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class HorizontalWheelPicker(QWidget):
    """
    Smooth, interactive horizontal number/item selector wheel.
    - Drag with mouse to scroll continuously.
    - Scroll with mouse wheel.
    - Click directly on any side item to select it.
    - Values loop infinitely in both directions (endless drag/wheel scrolling).
    - Center item is prominently highlighted; side items fade smoothly into distance.
    - Snaps cleanly to nearest item with easing animation on release.
    """
    valueChanged = Signal(int, str)

    def __init__(self, items, default_index=0, item_width=44, parent=None):
        super().__init__(parent)
        self.items = [str(x) for x in items]
        self.item_width = item_width
        self._current_index = max(0, min(len(self.items) - 1, default_index)) if self.items else 0
        self._scroll_offset = float(self._current_index * self.item_width)

        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_offset = 0.0
        self._has_moved_drag = False

        self.setFixedHeight(34)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        self._anim = QPropertyAnimation(self, b"scroll_offset", self)
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @Property(float)
    def scroll_offset(self):
        return self._scroll_offset

    @scroll_offset.setter
    def scroll_offset(self, val):
        self._scroll_offset = val
        self.update()

    def get_current_index(self):
        if not self.items:
            return 0
        return self._virtual_center() % len(self.items)

    def get_current_value(self):
        if not self.items:
            return ""
        return self.items[self.get_current_index()]

    def _virtual_center(self):
        """Unbounded index of the item currently nearest the centre (wraps conceptually)."""
        return int(round(self._scroll_offset / float(self.item_width)))

    def _animate_to_virtual(self, virtual_index):
        if not self.items:
            return
        index = virtual_index % len(self.items)
        self._current_index = index
        self._anim.stop()
        self._anim.setStartValue(self._scroll_offset)
        self._anim.setEndValue(float(virtual_index * self.item_width))
        self._anim.start()
        self.valueChanged.emit(index, self.items[index])

    def set_current_index(self, index, animated=True):
        if not self.items:
            return
        n = len(self.items)
        index %= n
        v = self._virtual_center()
        # Take the shortest looping path to the requested value
        delta = (index - (v % n) + n // 2) % n - n // 2
        target = v + delta
        if animated:
            self._animate_to_virtual(target)
        else:
            self._anim.stop()
            self._scroll_offset = float(target * self.item_width)
            self._current_index = index
            self.update()
            self.valueChanged.emit(index, self.items[index])

    def wheelEvent(self, event):
        delta = event.angleDelta().y() or event.angleDelta().x()
        if delta == 0 or not self.items:
            return
        step = -1 if delta > 0 else 1
        self._animate_to_virtual(self._virtual_center() + step)
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._anim.stop()
            self._is_dragging = True
            self._drag_start_x = event.pos().x()
            self._drag_start_offset = self._scroll_offset
            self._has_moved_drag = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            dx = event.pos().x() - self._drag_start_x
            if abs(dx) > 3:
                self._has_moved_drag = True
            # Unbounded: the item loop in paintEvent wraps values around
            self._scroll_offset = self._drag_start_offset - dx
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            cx = self.width() / 2.0
            p = float(self.item_width)
            if not self._has_moved_drag:
                # Direct click selection
                clicked_x = event.pos().x()
                rel_dist = clicked_x - cx
                clicked_v = int(round((self._scroll_offset + rel_dist) / p))
                self._animate_to_virtual(clicked_v)
            else:
                # Snap to nearest item after drag
                self._animate_to_virtual(int(round(self._scroll_offset / p)))
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        cx = w / 2.0
        cy = h / 2.0

        if not self.items:
            return

        font_family = config.load_font_family("DM Sans")

        # 1. Background capsule for the center selected item
        pill_w = float(self.item_width) + 8.0
        pill_h = h - 4.0
        pill_rect = QRectF(cx - (pill_w / 2.0), (h - pill_h) / 2.0, pill_w, pill_h)

        # Highlight center box with subtle accent tint
        accent_hex = config.load_accent_color(theme.ACCENT_COLOR)
        accent_col = QColor(accent_hex)
        accent_col.setAlpha(42)
        painter.setBrush(accent_col)
        border_col = QColor(accent_hex)
        border_col.setAlpha(120)
        painter.setPen(QPen(border_col, 1.2))
        painter.drawRoundedRect(pill_rect, 7.0, 7.0)

        # 2. Render items horizontally, looping the list endlessly in both directions
        n = len(self.items)
        p = float(self.item_width)
        v = self._virtual_center()
        span = int(cx / p) + 2
        for s in range(-span, span + 1):
            text = self.items[(v + s) % n]
            item_cx = cx + ((v + s) * p - self._scroll_offset)
            dist = abs(item_cx - cx)

            norm_dist = min(1.0, dist / max(1.0, cx))
            # Center item: bright, crisp, larger bold font.
            # Side items: smoothly fade in alpha and slightly smaller font.
            if dist < (self.item_width * 0.45):
                alpha = 255
                font_pt = 12.0 if len(text) <= 3 else 10.5
                is_bold = True
                text_col = QColor("#FFFFFF")
            else:
                alpha = int(max(40, 220 * (1.0 - (norm_dist * 0.72))))
                font_pt = 10.5 if len(text) <= 3 else 9.5
                is_bold = False
                text_col = QColor(255, 255, 255, alpha)

            font = QFont(font_family)
            font.setPointSizeF(font_pt)
            font.setBold(is_bold)
            painter.setFont(font)
            painter.setPen(text_col)

            # Place glyphs on their visual centre (cap-height based) so numbers
            # sit perfectly inside the pill, not low or high.
            fm = QFontMetrics(font)
            baseline_y = cy + fm.capHeight() / 2.0
            text_x = item_cx - fm.horizontalAdvance(text) / 2.0
            painter.drawText(QPointF(text_x, baseline_y), text)

        # 3. Soft gradient masks at far left and right edges for smooth visual fading
        fade_w = min(20.0, w * 0.12)
        left_grad = QLinearGradient(0, 0, fade_w, 0)
        left_grad.setColorAt(0.0, QColor(0, 0, 0, 180))
        left_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(QRectF(0, 0, fade_w, h), left_grad)

        right_grad = QLinearGradient(w - fade_w, 0, w, 0)
        right_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        right_grad.setColorAt(1.0, QColor(0, 0, 0, 180))
        painter.fillRect(QRectF(w - fade_w, 0, fade_w, h), right_grad)


class NotchReminderCreator(QWidget):
    """
    Interactive Reminder creation interface in the expanded notch.
    Contains:
    - Reminder Title input field (identical styling to task input)
    - Hours horizontal wheel selector (00-23 or 01-12 based on user time format)
    - Minutes horizontal wheel selector (00 to 59)
    - AM/PM wheel selector (only in 12-hour format)
    - Confirm (Save) and Cancel action buttons
    """
    reminder_created = Signal(dict)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.use_24h = config.load_use_24h(True)
        self._init_ui()

    def _default_time(self):
        now = datetime.datetime.now()
        hr24 = now.hour
        mi = ((now.minute // 5) + 1) * 5
        if mi >= 60:
            mi = 0
            hr24 = (hr24 + 1) % 24
        return hr24, mi

    def _apply_time_defaults(self):
        hr24, mi = self._default_time()
        if self.use_24h:
            self.picker_hr.set_current_index(hr24, animated=False)
        else:
            self.picker_hr.set_current_index((hr24 + 11) % 12, animated=False)
            self.picker_ap.set_current_index(0 if hr24 < 12 else 1, animated=False)
        self.picker_min.set_current_index(mi, animated=False)

    def _init_ui(self):
        font_family = config.load_font_family("DM Sans")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        # 1. Pickers row: Hour Box + Minute Box (wide enough to show neighbours)
        row_pickers = QHBoxLayout()
        row_pickers.setContentsMargins(0, 0, 0, 0)
        row_pickers.setSpacing(10)

        box_qss = """
            QFrame {
                background-color: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 16);
                border-radius: 10px;
            }
        """

        lbl_style = "color: rgba(255, 255, 255, 0.45); font-size: 9.5px; font-weight: 700; background: transparent; border: none;"

        # --- Hour Selection Box ---
        card_hr = QFrame(self)
        card_hr.setStyleSheet(box_qss)
        layout_hr = QHBoxLayout(card_hr)
        layout_hr.setContentsMargins(6, 2, 6, 2)
        layout_hr.setSpacing(6)
        lbl_hr = QLabel("HR", card_hr)
        lbl_hr.setFixedWidth(24)
        lbl_hr.setStyleSheet(lbl_style)
        if self.use_24h:
            hour_items = [f"{i:02d}" for i in range(24)]
        else:
            hour_items = [f"{i:02d}" for i in range(1, 13)]
        self.picker_hr = HorizontalWheelPicker(hour_items, default_index=0, item_width=40, parent=card_hr)
        layout_hr.addWidget(lbl_hr)
        layout_hr.addWidget(self.picker_hr, 1)
        row_pickers.addWidget(card_hr, 1)

        # --- Minute Selection Box ---
        card_min = QFrame(self)
        card_min.setStyleSheet(box_qss)
        layout_min = QHBoxLayout(card_min)
        layout_min.setContentsMargins(6, 2, 6, 2)
        layout_min.setSpacing(6)
        lbl_min = QLabel("MIN", card_min)
        lbl_min.setFixedWidth(24)
        lbl_min.setStyleSheet(lbl_style)
        self.picker_min = HorizontalWheelPicker([f"{i:02d}" for i in range(60)], default_index=0, item_width=40, parent=card_min)
        layout_min.addWidget(lbl_min)
        layout_min.addWidget(self.picker_min, 1)
        row_pickers.addWidget(card_min, 1)

        layout.addLayout(row_pickers)

        # 2. Action Row: AM/PM picker (12h only) on the left, Cancel + Set Reminder on the right
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)

        if not self.use_24h:
            card_ap = QFrame(self)
            card_ap.setStyleSheet(box_qss)
            card_ap.setFixedHeight(28)
            layout_ap = QHBoxLayout(card_ap)
            layout_ap.setContentsMargins(6, 2, 6, 2)
            layout_ap.setSpacing(0)
            self.picker_ap = HorizontalWheelPicker(["AM", "PM"], default_index=0, item_width=38, parent=card_ap)
            self.picker_ap.setFixedSize(96, 22)
            layout_ap.addWidget(self.picker_ap)
            btn_row.addWidget(card_ap)

        btn_row.addStretch(1)

        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedHeight(28)
        self.btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 14);
                color: rgba(255, 255, 255, 0.75);
                border: 1px solid rgba(255, 255, 255, 20);
                border-radius: 8px;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
                padding: 0px 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 26);
                color: #FFFFFF;
            }}
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.btn_cancel)

        self.btn_confirm = QPushButton("Set Reminder", self)
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.setFixedHeight(28)
        self.btn_confirm.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_COLOR};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 700;
                padding: 0px 16px;
            }}
            QPushButton:hover {{
                opacity: 0.92;
            }}
        """)
        self.btn_confirm.clicked.connect(self._on_confirm)
        btn_row.addWidget(self.btn_confirm)

        layout.addLayout(btn_row)
        self._apply_time_defaults()

    def _get_title_edit(self):
        """Find the QLineEdit used for reminder title in the notch header."""
        parent = self.parent()
        if parent:
            notch = getattr(parent, "notch", None)
            if notch and hasattr(notch, "reminder_title_edit"):
                return notch.reminder_title_edit
        return None

    def reset_inputs(self):
        """Reset inputs to defaults."""
        title_edit = self._get_title_edit()
        if title_edit:
            title_edit.clear()
            title_edit.setPlaceholderText("What would you like to be reminded of?")
            title_edit.setFocus()
        self._apply_time_defaults()

    def _on_confirm(self):
        title_edit = self._get_title_edit()
        title = title_edit.text().strip() if title_edit else ""
        if not title:
            if title_edit:
                title_edit.setPlaceholderText("⚠️ Please enter a title for the reminder...")
                title_edit.setFocus()
            return

        hr = int(self.picker_hr.get_current_value())
        mi = int(self.picker_min.get_current_value())
        if not self.use_24h:
            is_pm = self.picker_ap.get_current_value() == "PM"
            hr = (hr % 12) + (12 if is_pm else 0)

        # Date defaults to today, or tomorrow if the time has already passed today
        now = datetime.datetime.now()
        target_date = datetime.date.today()
        if (hr < now.hour) or (hr == now.hour and mi <= now.minute):
            target_date = target_date + datetime.timedelta(days=1)
            date_display = "Tomorrow"
        else:
            date_display = "Today"
        date_key = target_date.strftime("%Y-%m-%d")

        reminder_data = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "hour": hr,
            "minute": mi,
            "date": date_key,
            "date_display": date_display,
            "completed": False,
            "created_at": datetime.datetime.now().timestamp()
        }
        self.reminder_created.emit(reminder_data)

    def _on_cancel(self):
        self.cancelled.emit()


class NotchReminderRow(QFrame):
    """Row widget representing an active reminder in the notch reminders list."""
    deleted = Signal(str)

    def __init__(self, reminder_data, parent=None):
        super().__init__(parent)
        self.reminder_data = reminder_data
        self.reminder_id = reminder_data.get("id", "")
        self.setFixedHeight(34)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 10);
                border: 1px solid rgba(255, 255, 255, 18);
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: rgba(255, 255, 255, 16);
                border: 1px solid rgba(255, 255, 255, 30);
            }
        """)

        font_family = config.load_font_family("DM Sans")
        accent_hex = config.load_accent_color(theme.ACCENT_COLOR)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 2, 8, 2)
        layout.setSpacing(8)

        # Title (no checkbox)
        title_text = reminder_data.get("title", "")
        self.lbl_title = QLabel(title_text, self)
        self.lbl_title.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.lbl_title, 1)

        # Time & Date (plain accent text, no box)
        hr = reminder_data.get("hour", 0)
        mi = reminder_data.get("minute", 0)
        date_disp = reminder_data.get("date_display", "Today")
        time_str = f"{date_disp} {hr:02d}:{mi:02d}"

        badge = QLabel(time_str, self)
        badge.setStyleSheet(f"""
            QLabel {{
                color: {accent_hex};
                background: transparent;
                border: none;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 9.5px;
                font-weight: 700;
                padding: 0px;
            }}
        """)
        layout.addWidget(badge)

        # Delete Button (x-circle icon, turns red on hover)
        self.btn_del = QPushButton(self)
        self.btn_del.setFixedSize(20, 20)
        self.btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_del.setToolTip("Delete reminder")
        self._del_icon_normal = svg_icon(X_CIRCLE_SVG, "#8CFFFFFF")
        self._del_icon_hover = svg_icon(X_CIRCLE_SVG, "#FF453A")
        self.btn_del.setIcon(self._del_icon_normal)
        self.btn_del.setIconSize(QSize(14, 14))
        self.btn_del.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)
        self.btn_del.clicked.connect(lambda: self.deleted.emit(self.reminder_id))
        self.btn_del.installEventFilter(self)
        layout.addWidget(self.btn_del)

    def eventFilter(self, obj, event):
        if obj is self.btn_del:
            if event.type() == QEvent.Type.Enter:
                self.btn_del.setIcon(self._del_icon_hover)
            elif event.type() == QEvent.Type.Leave:
                self.btn_del.setIcon(self._del_icon_normal)
        return super().eventFilter(obj, event)


class NotchReminderList(QWidget):
    """
    Displays the list of active reminders in the expanded notch with 'Upcoming reminders' title.
    """
    request_new_reminder = Signal()
    reminders_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reminders = []
        self._init_ui()
        self.reload_reminders()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header Title: "Upcoming reminders"
        font_family = config.load_font_family("DM Sans")
        self.lbl_title = QLabel("Upcoming reminders", self)
        self.lbl_title.setFixedHeight(18)
        self.lbl_title.setStyleSheet(f"""
            QLabel {{
                color: rgba(255, 255, 255, 0.65);
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 10.5px;
                font-weight: 700;
                letter-spacing: 0.5px;
                padding-left: 2px;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(self.lbl_title)

        # Scroll Area for Reminders List
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 40);
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self.items_container = QWidget()
        self.items_container.setStyleSheet("background: transparent;")
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(6)
        self.items_layout.addStretch(1)

        self.scroll.setWidget(self.items_container)
        layout.addWidget(self.scroll, 1)

    def reload_reminders(self):
        """Load reminders from config and populate list."""
        font_family = config.load_font_family("DM Sans")
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(f"""
                QLabel {{
                    color: rgba(255, 255, 255, 0.65);
                    font-family: '{font_family}', 'Segoe UI', sans-serif;
                    font-size: 10.5px;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                    padding-left: 2px;
                    background: transparent;
                    border: none;
                }}
            """)

        self.reminders = config.load_reminders()
        # Clear items except stretch
        while self.items_layout.count() > 1:
            item = self.items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active_reminders = [r for r in self.reminders if not r.get("completed", False)]

        for r in active_reminders:
            row = NotchReminderRow(r, self.items_container)
            row.deleted.connect(self._delete_reminder)
            self.items_layout.insertWidget(self.items_layout.count() - 1, row)

    def _complete_reminder(self, reminder_id):
        reminders = config.load_reminders()
        for r in reminders:
            if r.get("id") == reminder_id:
                r["completed"] = True
                break
        config.save_reminders(reminders)
        self.reload_reminders()
        self.reminders_changed.emit()

    def _delete_reminder(self, reminder_id):
        reminders = [r for r in config.load_reminders() if r.get("id") != reminder_id]
        config.save_reminders(reminders)
        self.reload_reminders()
        self.reminders_changed.emit()


class NotchReminderWidget(QWidget):
    """
    Parent container widget embedded into NotchWidget for the Reminders feature.
    Seamlessly switches between Creator view and Reminders List view.
    """
    closed = Signal()

    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self._mode = "create"  # "create" or "list"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.creator = NotchReminderCreator(self)
        self.creator.reminder_created.connect(self._on_reminder_created)
        self.creator.cancelled.connect(self._on_cancelled)
        layout.addWidget(self.creator)

        self.reminder_list = NotchReminderList(self)
        self.reminder_list.request_new_reminder.connect(self.show_creator)
        self.reminder_list.reminders_changed.connect(self._on_reminders_changed)
        self.reminder_list.hide()
        layout.addWidget(self.reminder_list)

    def is_creating(self):
        return getattr(self, "_mode", "create") == "create"

    def show_creator(self):
        self._mode = "create"
        self.reminder_list.hide()
        self.creator.show()
        self.creator.reset_inputs()
        if hasattr(self.notch, "update_reminder_geometry"):
            self.notch.update_reminder_geometry()

    def show_list(self):
        self._mode = "list"
        self.creator.hide()
        self.reminder_list.reload_reminders()
        self.reminder_list.show()
        if hasattr(self.notch, "update_reminder_geometry"):
            self.notch.update_reminder_geometry()

    def _on_reminder_created(self, reminder_data):
        reminders = config.load_reminders()
        reminders.insert(0, reminder_data)
        config.save_reminders(reminders)
        if hasattr(self.notch, "finish_reminder_creation"):
            self.notch.finish_reminder_creation()
        elif hasattr(self.notch, "collapse_reminders"):
            self.notch.collapse_reminders()
        else:
            self.show_list()

    def _on_cancelled(self):
        reminders = [r for r in config.load_reminders() if not r.get("completed", False)]
        if len(reminders) > 0 and hasattr(self.notch, "show_reminders_in_notch"):
            self.notch.show_reminders_in_notch()
        else:
            self.closed.emit()

    def _on_reminders_changed(self):
        if hasattr(self.notch, "_update_reminders_notch_geometry"):
            self.notch._update_reminders_notch_geometry()
        elif hasattr(self.notch, "update_reminder_geometry"):
            self.notch.update_reminder_geometry()

