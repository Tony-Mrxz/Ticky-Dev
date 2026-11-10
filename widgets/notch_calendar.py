# widgets/notch_calendar.py
"""Embedded calendar stage for the notch: today card, month grid and events."""

import datetime
import re
import uuid

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel,
                               QPushButton, QLineEdit, QScrollArea, QFrame, QComboBox,
                               QSizePolicy)
from PySide6.QtCore import Qt, Signal, QByteArray, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

from utils import config
from styles import theme
from utils.festivals import festivals_for_month

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
WEEKDAY_HEADERS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Layout metrics: circular/rounded day cells, dividing line, right-hand events block.
DAY_W = 33
DAY_H = 30
GRID_SPACING_X = 4
GRID_SPACING_Y = 3
CALENDAR_W = 7 * DAY_W + 6 * GRID_SPACING_X  # 7 * 33 + 6 * 4 = 255
DIVIDER_W = 1
DIVIDER_GAP = 12
EVENTS_W = 176
NOTCH_PADDING_X = 22  # 10px notch ear + 12px inner border margin = 22px
NOTCH_PADDING_Y = 12  # 12px top and bottom inner border margin
NOTCH_EXTRA_H = NOTCH_PADDING_Y * 2  # 24px
NOTCH_WIDTH = CALENDAR_W + DIVIDER_GAP + DIVIDER_W + DIVIDER_GAP + EVENTS_W + (NOTCH_PADDING_X * 2)  # 500
CALENDAR_UNHOVER_TIMEOUT_MS = 1200  # 1.2s unhover fallback timer (reduced from 3s)

CHEVRON_LEFT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" '
    'viewBox="0 0 24 24"><path d="M14.29 6.29 8.59 12l5.7 5.71 1.42-1.42-4.3-4.29 4.3-4.29z"></path></svg>'
)
CHEVRON_RIGHT_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="currentColor" '
    'viewBox="0 0 24 24"><path d="m9.71 17.71 5.7-5.71-5.7-5.71-1.42 1.42 4.3 4.29-4.3 4.29z"></path></svg>'
)


def collect_month_events(year, month):
    """User events plus festivals for a month, sorted by (date, time, title)."""
    items = []
    for ev in config.load_events():
        try:
            day = datetime.date.fromisoformat(ev.get("date", ""))
        except (ValueError, TypeError):
            continue
        if (day.year, day.month) == (year, month):
            items.append({"date": day, "title": ev.get("title", ""),
                          "time": ev.get("time", ""), "kind": "user",
                          "id": ev.get("id", "")})
    for day, name in festivals_for_month(year, month):
        items.append({"date": day, "title": name, "time": "",
                      "kind": "festival", "id": f"fest-{day.isoformat()}"})
    items.sort(key=lambda e: (e["date"], e["time"] or "", e["title"]))
    return items


def month_grid(year, month):
    """Weeks of 7 cells (date or None) covering the month, Sunday-first."""
    first = datetime.date(year, month, 1)
    lead = (first.weekday() + 1) % 7
    next_month = datetime.date(year + (month == 12), month % 12 + 1, 1)
    days = (next_month - first).days
    cells = [None] * lead + [datetime.date(year, month, d) for d in range(1, days + 1)]
    while len(cells) % 7:
        cells.append(None)
    return [cells[i:i + 7] for i in range(0, len(cells), 7)]


class NotchCalendarWidget(QWidget):
    """Calendar panel embedded into NotchWidget; the notch sizes it manually."""
    closed = Signal()
    height_changed = Signal(int)

    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self._today = datetime.date.today()
        self._year = self._today.year
        self._month = self._today.month
        self._selected = self._today
        self._adding = False
        self._picker_open = False
        self._font = config.load_font_family("DM Sans")
        self._accent = config.load_accent_color(theme.ACCENT_COLOR)
        self._day_buttons = []
        self._build_ui()
        self.reload()

    # -- construction ---------------------------------------------------------
    def _label(self, text, size, color, bold=False, parent=None):
        lbl = QLabel(text, parent or self)
        lbl.setStyleSheet(
            f"color: {color}; font-family: '{self._font}', 'Segoe UI', sans-serif; "
            f"font-size: {size}px; font-weight: {'700' if bold else '400'}; "
            f"background: transparent; border: none;")
        return lbl

    def _flat_button(self, text, size=12, color="#FFFFFF", bold=False):
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none; border-radius: 6px;
                color: {color}; font-family: '{self._font}', 'Segoe UI', sans-serif;
                font-size: {size}px; font-weight: {'700' if bold else '500'};
                padding: 2px 6px;
            }}
            QPushButton:hover {{ background: rgba(255, 255, 255, 20); }}
        """)
        return btn

    def _svg_icon(self, svg, color="#FFFFFF", size=16):
        renderer = QSvgRenderer(QByteArray(svg.replace("currentColor", color).encode("utf-8")))
        pm = QPixmap(size * 2, size * 2)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        renderer.render(painter)
        painter.end()
        return QIcon(pm)

    def _input(self, placeholder):
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 8px; color: #FFFFFF;
                font-family: '{self._font}', 'Segoe UI', sans-serif;
                font-size: 11px; padding: 4px 8px;
                selection-background-color: {self._accent};
            }}
            QLineEdit:focus {{ border: 1px solid {self._accent}; }}
        """)
        return edit

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)

        # Left: calendar section (nav + picker + weekday headers + day grid)
        # Flush with left edge, full CALENDAR_W width with zero wasted gaps.
        cal_col = QVBoxLayout()
        cal_col.setContentsMargins(0, 0, 0, 0)
        cal_col.setSpacing(5)

        nav = QHBoxLayout()
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(2)
        self.btn_prev = self._flat_button("")
        self.btn_prev.setFixedSize(22, 22)
        self.btn_prev.setIcon(self._svg_icon(CHEVRON_LEFT_SVG))
        self.btn_prev.setIconSize(QSize(16, 16))
        self.btn_prev.setToolTip("Previous month")
        self.btn_prev.clicked.connect(lambda: self._shift_month(-1))
        self.btn_month_year = self._flat_button("", 12, "#FFFFFF", bold=True)
        self.btn_month_year.setToolTip("Pick a month and year")
        self.btn_month_year.clicked.connect(self._toggle_picker)
        self.btn_next = self._flat_button("")
        self.btn_next.setFixedSize(22, 22)
        self.btn_next.setIcon(self._svg_icon(CHEVRON_RIGHT_SVG))
        self.btn_next.setIconSize(QSize(16, 16))
        self.btn_next.setToolTip("Next month")
        self.btn_next.clicked.connect(lambda: self._shift_month(1))
        nav.addWidget(self.btn_prev)
        nav.addStretch(1)
        nav.addWidget(self.btn_month_year)
        nav.addStretch(1)
        nav.addWidget(self.btn_next)
        cal_col.addLayout(nav)

        picker = QHBoxLayout()
        picker.setContentsMargins(0, 0, 0, 0)
        picker.setSpacing(6)
        self.combo_month = QComboBox()
        self.combo_month.addItems(MONTH_NAMES)
        self.combo_year = QComboBox()
        for year in range(self._today.year - 5, self._today.year + 6):
            self.combo_year.addItem(str(year))
        for combo in (self.combo_month, self.combo_year):
            combo.setStyleSheet(f"""
                QComboBox {{
                    background: rgba(255, 255, 255, 14);
                    border: 1px solid rgba(255, 255, 255, 22);
                    border-radius: 6px; color: #FFFFFF;
                    font-family: '{self._font}', 'Segoe UI', sans-serif;
                    font-size: 10px; padding: 2px 6px;
                }}
                QComboBox QAbstractItemView {{
                    background: #1A1A1A; color: #FFFFFF;
                    selection-background-color: {self._accent};
                }}
            """)
        self.combo_month.currentIndexChanged.connect(self._picker_changed)
        self.combo_year.currentIndexChanged.connect(self._picker_changed)
        picker.addWidget(self.combo_month, 1)
        picker.addWidget(self.combo_year, 0)
        self.picker_row = QWidget()
        self.picker_row.setLayout(picker)
        self.picker_row.hide()
        cal_col.addWidget(self.picker_row)

        weekdays = QHBoxLayout()
        weekdays.setContentsMargins(0, 0, 0, 0)
        weekdays.setSpacing(GRID_SPACING_X)
        for name in WEEKDAY_HEADERS:
            color = "rgba(255, 130, 130, 235)" if name == "Su" else "rgba(255, 255, 255, 220)"
            lbl = self._label(name, 11, color, bold=True)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(DAY_W)
            weekdays.addWidget(lbl)
        cal_col.addLayout(weekdays)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(GRID_SPACING_X)
        self.grid.setVerticalSpacing(GRID_SPACING_Y)
        for index in range(42):
            btn = QPushButton("")
            btn.setFixedSize(DAY_W, DAY_H)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=index: self._on_day_clicked(i))
            self.grid.addWidget(btn, index // 7, index % 7)
            self._day_buttons.append(btn)
        cal_col.addLayout(self.grid)

        self.calendar_box = QWidget()
        self.calendar_box.setLayout(cal_col)
        self.calendar_box.setFixedWidth(CALENDAR_W)
        top.addWidget(self.calendar_box)

        # Vertical dividing line between calendar and events box
        top.addSpacing(DIVIDER_GAP)
        divider_wrap = QWidget()
        divider_wrap.setFixedWidth(DIVIDER_W)
        div_lay = QVBoxLayout(divider_wrap)
        div_lay.setContentsMargins(0, 4, 0, 4)
        div_lay.setSpacing(0)
        self.divider = QFrame()
        self.divider.setFixedWidth(DIVIDER_W)
        self.divider.setStyleSheet("background-color: rgba(255, 255, 255, 22); border: none;")
        div_lay.addWidget(self.divider)
        top.addWidget(divider_wrap)
        top.addSpacing(DIVIDER_GAP)

        # Right: events block (today/future + selected-day only).
        self.events_block = QFrame()
        self.events_block.setFixedWidth(EVENTS_W)
        self.events_block.setStyleSheet(
            "QFrame { background: rgba(255, 255, 255, 6); "
            "border: 1px solid rgba(255, 255, 255, 12); border-radius: 10px; }")
        ev_lay = QVBoxLayout(self.events_block)
        ev_lay.setContentsMargins(8, 8, 8, 8)
        ev_lay.setSpacing(6)
        events_head = QHBoxLayout()
        events_head.setContentsMargins(0, 0, 0, 0)
        events_head.setSpacing(4)
        self.lbl_events_title = self._label("EVENTS", 9,
                                            "rgba(255, 255, 255, 180)", bold=True)
        self.btn_add = self._flat_button("+ Add", 10, self._accent, bold=True)
        self.btn_add.clicked.connect(self._start_add)
        events_head.addWidget(self.lbl_events_title)
        events_head.addStretch(1)
        events_head.addWidget(self.btn_add)
        ev_lay.addLayout(events_head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                border: none; background: transparent; width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 40); border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        self.events_content = QWidget()
        self.events_content.setStyleSheet("background: transparent;")
        self.events_layout = QVBoxLayout(self.events_content)
        self.events_layout.setContentsMargins(0, 0, 4, 0)
        self.events_layout.setSpacing(4)
        self.events_layout.addStretch(1)
        self.scroll.setWidget(self.events_content)
        ev_lay.addWidget(self.scroll, 1)
        top.addWidget(self.events_block)

        root.addLayout(top)

        # Add-event form (spans the full width when open).
        self.creator = QFrame()
        self.creator.setStyleSheet(
            "QFrame { background: rgba(255, 255, 255, 8); "
            "border: 1px solid rgba(255, 255, 255, 16); border-radius: 10px; }")
        creator_lay = QVBoxLayout(self.creator)
        creator_lay.setContentsMargins(10, 8, 10, 8)
        creator_lay.setSpacing(6)
        self.lbl_creator_date = self._label("", 10, "rgba(255, 255, 255, 180)", bold=True)
        self.input_title = self._input("Event title — meeting, plan, birthday...")
        self.input_title.returnPressed.connect(self._save_event)
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.input_time = self._input("Time optional (HH:MM)")
        self.input_time.setFixedWidth(130)
        self.btn_cancel = self._flat_button("Cancel", 10, "rgba(255, 255, 255, 180)")
        self.btn_cancel.clicked.connect(self._cancel_add)
        self.btn_save = self._flat_button("Save", 10, self._accent, bold=True)
        self.btn_save.clicked.connect(self._save_event)
        bottom.addWidget(self.input_time)
        bottom.addStretch(1)
        bottom.addWidget(self.btn_cancel)
        bottom.addWidget(self.btn_save)
        creator_lay.addWidget(self.lbl_creator_date)
        creator_lay.addWidget(self.input_title)
        creator_lay.addLayout(bottom)
        self.creator.hide()
        root.addWidget(self.creator)

    # -- state ----------------------------------------------------------------
    def reset_view(self):
        self._font = config.load_font_family("DM Sans")
        self._accent = config.load_accent_color(theme.ACCENT_COLOR)
        self._today = datetime.date.today()
        self._year = self._today.year
        self._month = self._today.month
        self._selected = self._today
        self._adding = False
        self._picker_open = False
        self.picker_row.hide()
        self.reload()

    def preferred_height(self):
        return self.layout().sizeHint().height()

    def _shift_month(self, delta):
        month = self._month + delta
        year = self._year
        if month < 1:
            month, year = 12, year - 1
        elif month > 12:
            month, year = 1, year + 1
        self._year, self._month = year, month
        if self._selected and (self._selected.year, self._selected.month) != (year, month):
            self._selected = None
        self.reload()

    def _toggle_picker(self):
        self._picker_open = not self._picker_open
        if self._picker_open:
            self.combo_month.blockSignals(True)
            self.combo_year.blockSignals(True)
            self.combo_month.setCurrentIndex(self._month - 1)
            idx = self.combo_year.findText(str(self._year))
            if idx < 0:
                self.combo_year.addItem(str(self._year))
                idx = self.combo_year.findText(str(self._year))
            self.combo_year.setCurrentIndex(idx)
            self.combo_month.blockSignals(False)
            self.combo_year.blockSignals(False)
        self.picker_row.setVisible(self._picker_open)
        self.height_changed.emit(self.preferred_height())

    def _picker_changed(self, _index):
        if not self._picker_open:
            return
        self._month = self.combo_month.currentIndex() + 1
        self._year = int(self.combo_year.currentText())
        if self._selected and (self._selected.year, self._selected.month) != (self._year, self._month):
            self._selected = None
        self.reload()

    def _on_day_clicked(self, index):
        weeks = month_grid(self._year, self._month)
        row, col = index // 7, index % 7
        if row >= len(weeks):
            return
        day = weeks[row][col]
        if day is None:
            return
        self._selected = day
        if self._adding:
            self._refresh_creator_date()
        self.reload()

    def _start_add(self):
        self._adding = True
        if self._selected is None:
            self._selected = datetime.date(self._year, self._month, 1)
        self.input_title.clear()
        self.input_time.clear()
        self._refresh_creator_date()
        self.reload()
        self.input_title.setFocus()

    def _refresh_creator_date(self):
        day = self._selected or self._today
        self.lbl_creator_date.setText(
            f"NEW EVENT — {day.strftime('%a, %d %b %Y').upper()}")

    def _cancel_add(self):
        self._adding = False
        self.reload()

    def _save_event(self):
        title = self.input_title.text().strip()
        if not title:
            self.input_title.setFocus()
            return
        time_text = self.input_time.text().strip()
        if time_text and not TIME_RE.match(time_text):
            self.input_time.setFocus()
            self.input_time.selectAll()
            return
        day = self._selected or self._today
        events = config.load_events()
        events.append({"id": uuid.uuid4().hex, "title": title,
                       "date": day.isoformat(), "time": time_text})
        config.save_events(events)
        self._adding = False
        self.reload()

    def _delete_event(self, event_id):
        config.save_events([e for e in config.load_events() if e.get("id") != event_id])
        self.reload()

    # -- rendering ------------------------------------------------------------
    def reload(self):
        self.btn_month_year.setText(f"{MONTH_NAMES[self._month - 1]} {self._year}")

        radius = 8
        weeks = month_grid(self._year, self._month)
        month_events = collect_month_events(self._year, self._month)

        for index, btn in enumerate(self._day_buttons):
            row, col = index // 7, index % 7
            day = weeks[row][col] if row < len(weeks) else None
            if day is None:
                btn.hide()
                continue
            btn.show()
            btn.setText(str(day.day))
            is_today = (day == self._today)
            is_selected = (day == self._selected)

            if is_selected and is_today:
                style = (f"background: {self._accent}; color: #FFFFFF; "
                         f"border: 1.5px solid #FFFFFF; border-radius: {radius}px;")
            elif is_selected:
                style = (f"background: {self._accent}; color: #FFFFFF; "
                         f"border: none; border-radius: {radius}px;")
            elif is_today:
                style = (f"background: rgba(255, 255, 255, 18); color: #FFFFFF; "
                         f"border: 1.5px solid {self._accent}; border-radius: {radius}px;")
            else:
                style = ("background: transparent; color: #FFFFFF; "
                         f"border: 1px solid transparent; border-radius: {radius}px;")

            is_bold = is_selected or is_today
            btn.setStyleSheet(f"""
                QPushButton {{
                    {style}
                    font-family: '{self._font}', 'Segoe UI', sans-serif;
                    font-size: 11px;
                    font-weight: {'700' if is_bold else '600'};
                }}
                QPushButton:hover {{
                    background: {'rgba(255, 255, 255, 28)' if not is_selected else self._accent};
                    color: #FFFFFF;
                }}
            """)

            # Informative tooltip showing weekday, date and events
            day_events = [e for e in month_events if e["date"] == day]
            if day_events:
                ev_summary = " · ".join(e["title"] for e in day_events)
                btn.setToolTip(f"{day.strftime('%A, %b %d')}\n{ev_summary}")
            else:
                btn.setToolTip(day.strftime("%A, %b %d"))

        self.btn_add.setVisible(not self._adding)
        self.creator.setVisible(self._adding)
        self.scroll.setVisible(not self._adding)
        if self._adding:
            self._refresh_creator_date()
        else:
            self._reload_events()
        self.height_changed.emit(self.preferred_height())

    def _reload_events(self):
        while self.events_layout.count():
            item = self.events_layout.takeAt(0)
            old = item.widget()
            if old is not None:
                # Detach now so a stale row can't paint over the rebuilt list
                # before the deferred delete runs.
                old.hide()
                old.setParent(None)
                old.deleteLater()
        events = self._visible_events()
        if not events:
            empty = self._label("No upcoming events. Add a meeting or a plan?",
                                10, "rgba(255, 255, 255, 150)")
            empty.setWordWrap(True)
            self.events_layout.insertWidget(0, empty)
        else:
            for event in events:
                self.events_layout.addWidget(self._event_row(event))
        self.events_layout.addStretch(1)

    def _visible_events(self):
        """Only today/future events, plus anything on the selected day."""
        events = collect_month_events(self._year, self._month)
        return [e for e in events
                if e["date"] >= self._today
                or (self._selected is not None and e["date"] == self._selected)]

    def _event_row(self, event):
        row = QFrame()
        row.setFixedHeight(30)
        row.setStyleSheet(
            "QFrame { background: rgba(255, 255, 255, 8); "
            "border: none; border-radius: 8px; }")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(8, 0, 6, 0)
        lay.setSpacing(6)

        badge = self._label(event["date"].strftime("%d"), 11,
                            self._accent if event["kind"] == "festival" else "#FFFFFF",
                            bold=True)
        badge.setFixedWidth(20)
        badge.setToolTip("Festival" if event["kind"] == "festival" else "Your event")
        lay.addWidget(badge)

        title = self._label(event["title"], 10, "rgba(255, 255, 255, 230)")
        tip = event["title"] if not event["time"] else f"{event['title']} · {event['time']}"
        title.setToolTip(tip)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay.addWidget(title, 1)

        if event["kind"] == "user":
            btn_del = self._flat_button("✕", 9, "rgba(255, 255, 255, 140)")
            btn_del.setFixedSize(18, 18)
            btn_del.setToolTip("Delete event")
            btn_del.clicked.connect(lambda checked=False, eid=event["id"]: self._delete_event(eid))
            lay.addWidget(btn_del)
        return row