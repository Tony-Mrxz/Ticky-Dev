# widgets/clock.py
"""Multi-style Clock and Date header widget."""

from PySide6.QtCore import Qt, QTimer, QDateTime
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PySide6.QtGui import QPainter, QColor, QPen, QFont


class ClockWidget(QWidget):
    """
    Style-switchable clock widget supporting 5 display modes:
      classic  — HH:MM / full date below (default)
      split    — Hours and minutes stacked vertically, Day + Date beside
      casio    — Real 7-segment DSEG7 LED digital font with inner border box
      minimal  — Time only, no date
      neon     — Time in accent color with date below
    """

    STYLES = ["classic", "split", "casio", "minimal", "neon"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._labels = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(500)

        self._build_layout()
        self.update_time()

    # ------------------------------------------------------------------
    # Layout builders
    # ------------------------------------------------------------------
    def _clear_layout(self):
        """Destroy all child widgets and labels, leaving a blank slate."""
        if self.layout():
            while self.layout().count():
                item = self.layout().takeAt(0)
                w = item.widget()
                if w:
                    w.hide()
                    w.deleteLater()
                # Also recurse into sub-layouts
                sub = item.layout()
                if sub:
                    while sub.count():
                        si = sub.takeAt(0)
                        sw = si.widget()
                        if sw:
                            sw.hide()
                            sw.deleteLater()
            # Detach the old layout by transferring it to a throwaway widget
            QWidget().setLayout(self.layout())
        self._labels = {}

    def _make_label(self, key, obj_name):
        lbl = QLabel("", self)
        lbl.setObjectName(obj_name)
        lbl.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._labels[key] = lbl
        return lbl

    def _build_layout(self):
        from styles import theme

        style = theme.CLOCK_STYLE
        show_box = theme.CLOCK_BOX_BG

        pad = (10, 8, 10, 8) if show_box else (0, 0, 0, 0)

        if style == "split":
            self._build_split(pad)
        elif style == "casio":
            self._build_casio(pad)
        elif style == "minimal":
            self._build_minimal(pad)
        elif style == "neon":
            self._build_neon(pad)
        else:
            self._build_classic(pad)

        self._apply_label_styles()

    def _build_classic(self, pad):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*pad)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._make_label("time", "ClockLabel"))
        layout.addWidget(self._make_label("date", "DateLabel"))

    def _build_split(self, pad):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(*pad)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # Left column: stacked hours / minutes
        left = QVBoxLayout()
        left.setSpacing(-8)
        left.setContentsMargins(0, 0, 0, 0)
        left.addWidget(self._make_label("hours", "SplitDigitLabel"))
        left.addWidget(self._make_label("mins",  "SplitDigitLabel"))

        # Right column: Day / Month+Date
        right = QVBoxLayout()
        right.setSpacing(3)
        right.setContentsMargins(0, 0, 0, 0)
        right.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        right.addWidget(self._make_label("day",  "SplitDayLabel"))
        right.addWidget(self._make_label("date", "DateLabel"))

        layout.addLayout(left)
        layout.addLayout(right)

    def _build_casio(self, pad):
        # Casio uses a fixed inner-border box, always has box feel
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._make_label("time", "CasioTimeLabel"))
        layout.addWidget(self._make_label("date", "CasioDateLabel"))

    def _build_minimal(self, pad):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*pad)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._make_label("time", "ClockLabel"))

    def _build_neon(self, pad):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*pad)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._make_label("time", "NeonClockLabel"))
        layout.addWidget(self._make_label("date", "DateLabel"))

    # ------------------------------------------------------------------
    # Style application
    # ------------------------------------------------------------------
    def _apply_label_styles(self):
        from styles import qss
        self.setStyleSheet(qss.get_clock_style())

    def apply_style(self, style_name=None, show_box=None):
        """Public method: switch style and/or box, then rebuild."""
        from styles import theme
        self.timer.stop()
        if style_name is not None:
            theme.CLOCK_STYLE = style_name
        if show_box is not None:
            theme.CLOCK_BOX_BG = show_box

        self._clear_layout()
        self._build_layout()
        self.update_time()
        self.update()
        self.timer.start()

    # ------------------------------------------------------------------
    # Background box paint
    # ------------------------------------------------------------------
    def paintEvent(self, event):
        from styles import theme
        if theme.CLOCK_BOX_BG or theme.CLOCK_STYLE == "casio":
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if theme.CLOCK_STYLE == "casio":
                # Casio: dark tinted retro box with double-line border feel
                bg = QColor(10, 12, 18, 220)
                border = QColor(theme.ACCENT_COLOR)
                border.setAlpha(180)
                painter.setBrush(bg)
                painter.setPen(QPen(border, 1))
                painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 6, 6)
                # Inner accent line
                inner_col = QColor(theme.ACCENT_COLOR)
                inner_col.setAlpha(40)
                painter.setPen(QPen(inner_col, 1))
                painter.drawRoundedRect(self.rect().adjusted(3, 3, -4, -4), 4, 4)
            else:
                # Standard glass box — same as toolbar
                bg = QColor(theme.SEC_CARD_COLOR)
                bg.setAlpha(152)
                border = QColor(255, 255, 255, 24)
                painter.setBrush(bg)
                painter.setPen(QPen(border, 1))
                painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

        super().paintEvent(event)

    # ------------------------------------------------------------------
    # Time update
    # ------------------------------------------------------------------
    def update_time(self):
        from styles import theme

        # Adjust tick interval
        interval = 500 if theme.SHOW_SECONDS else 1000
        if self.timer.interval() != interval:
            self.timer.setInterval(interval)

        now = QDateTime.currentDateTime()
        use_24h = theme.USE_24H
        show_sec = theme.SHOW_SECONDS
        sty = theme.CLOCK_STYLE

        # Pre-build time string fragments
        if show_sec:
            time_str = now.toString("HH:mm:ss" if use_24h else "hh:mm:ss AP")
        else:
            time_str = now.toString("HH:mm" if use_24h else "hh:mm AP")

        hour_val = now.time().hour()
        if not use_24h:
            hour_12 = hour_val % 12
            if hour_12 == 0:
                hour_12 = 12
            hours_str = f"{hour_12:02d}"
        else:
            hours_str = f"{hour_val:02d}"
        mins_str  = now.toString("mm")
        day_str   = now.toString("ddd").upper()
        date_str  = now.toString("MMM d").upper()
        full_date = now.toString("dddd, MMMM d").upper()

        # Update labels based on active style
        lbl = self._labels

        try:
            if sty == "split":
                if "hours" in lbl: lbl["hours"].setText(hours_str)
                if "mins"  in lbl: lbl["mins"].setText(mins_str)
                if "day"   in lbl: lbl["day"].setText(day_str)
                if "date"  in lbl: lbl["date"].setText(date_str)

            elif sty == "casio":
                if "time" in lbl: lbl["time"].setText(time_str)
                if "date" in lbl: lbl["date"].setText(f"{day_str}  {date_str}")

            elif sty in ("classic", "neon"):
                if "time" in lbl:
                    lbl["time"].setText(time_str)
                if "date" in lbl:
                    if theme.SHOW_DATE:
                        lbl["date"].setText(full_date)
                        lbl["date"].setVisible(True)
                    else:
                        lbl["date"].setVisible(False)

            elif sty == "minimal":
                if "time" in lbl:
                    lbl["time"].setText(time_str)
        except RuntimeError:
            pass

        self.setAccessibleDescription(f"Clock showing {time_str}")
