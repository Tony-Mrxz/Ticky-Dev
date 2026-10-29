from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal, QPoint, QEvent, QTimer, QRectF, QRegularExpression
from PySide6.QtWidgets import (QWidget, QAbstractButton, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QLabel, QPushButton, QGraphicsDropShadowEffect,
                               QStackedWidget, QSlider, QLineEdit, QFrame, QScrollArea,
                               QGraphicsOpacityEffect, QComboBox, QListWidget, QListWidgetItem,
                               QColorDialog)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QKeySequence, QRegularExpressionValidator
from styles import theme, qss
from utils import config
from utils.version import APP_VERSION

class MicLevelBar(QWidget):
    """Slim live input-level bar used to verify the selected microphone."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self.setFixedHeight(8)

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 28)))
        painter.drawRoundedRect(QRectF(1.0, 1.0, w - 2.0, h - 2.0), 4.0, 4.0)
        if self._level > 0.004:
            fill_w = max(6.0, (w - 2.0) * self._level)
            painter.setBrush(QBrush(QColor(theme.ACCENT_COLOR)))
            painter.drawRoundedRect(QRectF(1.0, 1.0, min(fill_w, w - 2.0), h - 2.0), 4.0, 4.0)
        painter.end()

class ToggleSwitch(QAbstractButton):
    toggled_state = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(36, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        
        # Position of the sliding handle (circle)
        # Range is from 3.0 (unchecked/left) to 19.0 (checked/right)
        self._handle_position = 3.0
        self.anim = QPropertyAnimation(self, b"handle_position", self)
        self.anim.setDuration(160)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    @Property(float)
    def handle_position(self):
        return self._handle_position

    @handle_position.setter
    def handle_position(self, val):
        self._handle_position = val
        self.update()

    def setChecked(self, checked):
        super().setChecked(checked)
        self.anim.stop()
        self.anim.setStartValue(self._handle_position)
        self.anim.setEndValue(19.0 if checked else 3.0)
        self.anim.start()

    def nextCheckState(self):
        checked = not self.isChecked()
        self.setChecked(checked)
        self.toggled_state.emit(checked)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        track_rect = self.rect().adjusted(1, 1, -1, -1)
        factor = (self._handle_position - 3.0) / 16.0
        factor = max(0.0, min(factor, 1.0))
        
        # Adjust track opacity when disabled
        if not self.isEnabled():
            off_color = QColor(theme.HOVER_COLOR)
            off_color.setAlpha(60)
            on_color = QColor(theme.ACCENT_COLOR)
            on_color.setAlpha(60)
            handle_color = QColor(255, 255, 255, 100)
        else:
            off_color = QColor(theme.HOVER_COLOR)
            if self._hovered:
                off_color = off_color.lighter(115)
                on_color = QColor(theme.ACCENT_COLOR).lighter(105)
            else:
                on_color = QColor(theme.ACCENT_COLOR)
            handle_color = QColor(255, 255, 255)
            
        r = off_color.red() + int((on_color.red() - off_color.red()) * factor)
        g = off_color.green() + int((on_color.green() - off_color.green()) * factor)
        b = off_color.blue() + int((on_color.blue() - off_color.blue()) * factor)
        track_color = QColor(r, g, b)
        if not self.isEnabled():
            track_color.setAlpha(60)
            
        painter.setBrush(track_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(track_rect, 9, 9)
        
        painter.setBrush(handle_color)
        painter.drawEllipse(self._handle_position, 3, 14, 14)


class ColorSwatch(QPushButton):
    color_selected = Signal(str)

    def __init__(self, color_hex, is_selected=False, parent=None):
        super().__init__("", parent)
        self.color_hex = color_hex
        self.is_selected = is_selected
        self.setFixedSize(18, 18)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.color_selected.emit(self.color_hex))
        
    def setSelected(self, selected):
        self.is_selected = selected
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Draw background solid color circle
        painter.setBrush(QColor(self.color_hex))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(rect)
        
        # Draw white inner ring if selected
        if self.is_selected:
            pen = QPen(QColor(255, 255, 255), 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(rect.adjusted(2, 2, -2, -2))


class ThemePreview(QPushButton):
    """Painted mock of the widget surface stack for one colour theme."""
    theme_selected = Signal(str)

    def __init__(self, theme_name, theme_data, is_active=False, parent=None):
        super().__init__("", parent)
        self.theme_name = theme_name
        self.theme_data = theme_data
        self.is_active = is_active
        self.setObjectName("ThemeStylePreview")
        self.setFixedSize(106, 72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(lambda: self.theme_selected.emit(self.theme_name))

    def setActive(self, active):
        self.is_active = active
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        data = self.theme_data
        bg = QColor(data["bg"])
        panel = QColor(data["main_card"])
        accent = QColor(theme.ACCENT_COLOR)
        # Neutral detail ink follows the theme's own text colour so light
        # themes still show their mock rows.
        ink = QColor(data.get("text_primary", theme.DARK_TEXT_PRIMARY))

        def tinted(color, alpha):
            c = QColor(color)
            c.setAlpha(alpha)
            return c

        if self.is_active:
            painter.setPen(QPen(accent, 1.5))
        else:
            painter.setPen(QPen(tinted(ink, 28), 1))
        painter.setBrush(bg)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)

        # Toolbar strip with three mock icons
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(panel)
        painter.drawRoundedRect(QRectF(3, 3, self.width() - 6, 16), 5, 5)
        for i in range(3):
            painter.setBrush(tinted(ink, 70))
            painter.drawEllipse(9 + i * 11, 8, 6, 6)

        # Content panel
        painter.setBrush(panel)
        painter.drawRoundedRect(QRectF(3, 22, self.width() - 6, self.height() - 25), 5, 5)

        # Mock clock line + sub line
        painter.setBrush(accent)
        painter.drawRoundedRect(9, 29, 26, 3, 1, 1)
        painter.setBrush(tinted(ink, 60))
        painter.drawRoundedRect(9, 35, 17, 2, 1, 1)

        # Two mock task rows
        for i in range(2):
            y = 43 + i * 8
            painter.setBrush(accent)
            painter.drawEllipse(9, y, 3, 3)
            painter.setBrush(tinted(ink, 55))
            painter.drawRoundedRect(16, y, 30, 2, 1, 1)


class ThemeStyleCard(QWidget):
    """Theme preview box with the theme name rendered on a line below it."""

    theme_selected = Signal(str)

    def __init__(self, theme_name, theme_data, is_active=False, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.setObjectName("ThemeStyleCard")
        self.setFixedSize(106, 92)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview = ThemePreview(theme_name, theme_data, is_active, self)
        self.preview.theme_selected.connect(self.theme_selected)
        outer.addWidget(self.preview)

        self.lbl_name = QLabel(theme_name, self)
        self.lbl_name.setObjectName("ThemeStyleName")
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.lbl_name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        outer.addWidget(self.lbl_name)

    def setActive(self, active):
        self.preview.setActive(active)
        self.setProperty("active", "true" if active else "false")
        self.lbl_name.setProperty("active", "true" if active else "false")
        for widget in (self.lbl_name,):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class ClockStyleCard(QWidget):
    """A clock style preview box with its name rendered on a line below the box."""

    clicked = Signal(str)

    def __init__(self, style_key, display_name, time_str, date_str, time_obj_name, active=False, parent=None):
        super().__init__(parent)
        self.style_key = style_key
        self.setObjectName("ClockStyleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(106, 104)
        self.setProperty("active", "true" if active else "false")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview = QFrame(self)
        self.preview.setObjectName("ClockStylePreview")
        self.preview.setFixedSize(106, 80)
        self.preview.setProperty("active", "true" if active else "false")

        preview_layout = QVBoxLayout(self.preview)
        preview_layout.setContentsMargins(8, 6, 8, 6)
        preview_layout.setSpacing(2)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_time = QLabel(time_str, self.preview)
        self.lbl_time.setObjectName(time_obj_name)
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(self.lbl_time)

        self.lbl_date = QLabel(date_str, self.preview)
        self.lbl_date.setObjectName("CardPreviewDate")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not date_str:
            self.lbl_date.hide()
        preview_layout.addWidget(self.lbl_date)

        outer.addWidget(self.preview)

        self.lbl_name = QLabel(display_name, self)
        self.lbl_name.setObjectName("CardStyleName")
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self.lbl_name.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        outer.addWidget(self.lbl_name)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.style_key)
            event.accept()
        else:
            super().mousePressEvent(event)

    def setActive(self, active):
        value = "true" if active else "false"
        self.setProperty("active", value)
        self.preview.setProperty("active", value)
        for widget in (self, self.preview, self.lbl_name, self.lbl_time, self.lbl_date):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.update()


class ShortcutLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Press key combination...")
        self.setReadOnly(True)
        self.setObjectName("SpotifyInput")
        
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()
        
        # Backspace or Delete to clear/disable the shortcut
        if key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            self.setText("None")
            event.accept()
            return
            
        # Ignore modifier-only key presses
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            super().keyPressEvent(event)
            return
            
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("Win")
            
        key_str = QKeySequence(key).toString()
        if key_str:
            parts.append(key_str)
            shortcut_text = "+".join(parts)
            self.setText(shortcut_text)
            event.accept()
        else:
            super().keyPressEvent(event)


class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(None) # Standalone window
        self.setWindowTitle("Ticky - Settings")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set window icon
        from utils.icon import load_ticky_icon
        self.setWindowIcon(load_ticky_icon())
        
        self.parent_window = parent
        self.selected_font = config.load_font_family("Inter")
        self.clock_weight = config.load_clock_weight("700")
        self.opened_from_ai = False
        
        # Movable drag state variables
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()
        self.is_dragging = False
        
        self.init_ui()

    def init_ui(self):
        # Increased window size to landscape orientation for sidebar dashboard layout
        self.setFixedSize(960, 680)

        # Main Outer Container Frame
        self.container = QFrame(self)
        self.container.setObjectName("SettingsWindowContainer")
        self.container.setFixedSize(960, 680)
        
        main_layout = QHBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Sidebar layout panel
        self.sidebar = QFrame(self.container)
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFixedWidth(190)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 12, 12, 12)
        sidebar_layout.setSpacing(6)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Sidebar Categories Title - changed to Ticky Settings
        sidebar_title = QLabel("Ticky Settings", self.sidebar)
        sidebar_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(sidebar_title)
        
        # Settings search bar (filters all pages, results replace the buttons while typing)
        self.search_edit = QLineEdit(self.sidebar)
        self.search_edit.setObjectName("SidebarSearch")
        self.search_edit.setPlaceholderText("Search settings…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedHeight(30)
        self.search_edit.textChanged.connect(self._on_settings_search)
        sidebar_layout.addWidget(self.search_edit)
        
        self.search_results = QListWidget(self.sidebar)
        self.search_results.setObjectName("SidebarSearchResults")
        self.search_results.setFixedHeight(320)
        self.search_results.setVisible(False)
        self.search_results.itemClicked.connect(self._on_search_result_clicked)
        sidebar_layout.addWidget(self.search_results)
        
        # Buttons sit below the search bar (small top gap, more room kept at the bottom)
        sidebar_layout.addStretch(1)
        
        self.sidebar_buttons = []
        sidebar_items = [
            ("General", 0),
            ("Clock", 1),
            ("Appearance", 2),
            ("Media Player", 3),
            ("AI Config", 4),
            ("Shortcuts", 5)
        ]
        
        for name, idx in sidebar_items:
            btn = QPushButton(name, self.sidebar)
            btn.setObjectName("SidebarButton")
            btn.setProperty("active", "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self.switch_page(i))
            sidebar_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
            
        sidebar_layout.addStretch(2)
        main_layout.addWidget(self.sidebar)
        
        # 2. Right settings content page panel
        content_widget = QWidget(self.container)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(18, 16, 18, 16)
        content_layout.setSpacing(10)
        
        # Header title bar inside content panel (fixed height so it can't absorb slack)
        header_bar = QWidget(content_widget)
        header_bar.setFixedHeight(38)
        title_layout = QHBoxLayout(header_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(8)
        
        # Invisible spacer mirrors the close button width so the pill stays exactly centered
        title_spacer = QWidget(header_bar)
        title_spacer.setFixedSize(30, 30)
        
        self.title_pill = QFrame(header_bar)
        self.title_pill.setObjectName("PageTitlePill")
        self.title_pill.setFixedSize(320, 38)
        pill_layout = QHBoxLayout(self.title_pill)
        pill_layout.setContentsMargins(16, 7, 16, 7)
        
        self.lbl_page_title = QLabel("General Settings", self.title_pill)
        self.lbl_page_title.setObjectName("SettingsTitle")
        self.lbl_page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill_layout.addWidget(self.lbl_page_title)
        
        close_btn = QPushButton("×", header_bar)
        close_btn.setObjectName("SettingsCloseButton")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(title_spacer)
        title_layout.addStretch(1)
        title_layout.addWidget(self.title_pill)
        title_layout.addStretch(1)
        title_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(header_bar)
        
        # Separator line
        sep = QWidget(content_widget)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {theme.BORDER_COLOR};")
        content_layout.addWidget(sep)
        
        # Stacked Widget for pages
        self.stacked_widget = QStackedWidget(content_widget)
        self.stacked_widget.setMinimumHeight(310)
        
        # Opacity effect for page transitions
        self.opacity_effect = QGraphicsOpacityEffect(self.stacked_widget)
        self.stacked_widget.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setEnabled(False)
        self.page_fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.page_fade_anim.setDuration(160)
        self.page_fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.page_fade_anim.finished.connect(lambda: self.opacity_effect.setEnabled(False))
        
        # --- Page 1: General Settings ---
        page_general = QWidget()
        page_general_layout = QVBoxLayout(page_general)
        page_general_layout.setContentsMargins(0, 0, 0, 0)
        page_general_layout.setSpacing(10)
        
        gen_scroll = QScrollArea(page_general)
        gen_scroll.setObjectName("GeneralSettingsScroll")
        gen_scroll.setWidgetResizable(True)
        gen_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        gen_content = QWidget()
        gen_content.setObjectName("GeneralScrollContent")
        gen_content_layout = QVBoxLayout(gen_content)
        gen_content_layout.setContentsMargins(0, 2, 6, 2)
        gen_content_layout.setSpacing(12)
        
        def _add_gen_row(layout, label, desc, widget):
            row = QHBoxLayout()
            row.setContentsMargins(0, 8, 0, 8)
            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            parent = layout.parentWidget()
            lbl = QLabel(label, parent)
            lbl.setObjectName("SettingLabel")
            lbl_desc = QLabel(desc, parent)
            lbl_desc.setObjectName("SettingDescription")
            text_col.addWidget(lbl)
            text_col.addWidget(lbl_desc)
            row.addLayout(text_col, 1)
            row.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            layout.addLayout(row)
            
        def _add_divider(layout):
            parent = layout.parentWidget()
            div = QFrame(parent)
            div.setObjectName("SettingRowDivider")
            div.setFixedHeight(1)
            layout.addWidget(div)
            
        # Behavior Card
        window_section = QFrame(gen_content)
        window_section.setObjectName("SettingSection")
        window_inner = QVBoxLayout(window_section)
        window_inner.setContentsMargins(12, 10, 12, 10)
        window_inner.setSpacing(0)
        
        self.switch_aot = ToggleSwitch(window_section)
        self.switch_aot.setChecked(config.load_always_on_top())
        _add_gen_row(window_inner, "Always on Top", "Keep Ticky visible over other windows", self.switch_aot)
        
        _add_divider(window_inner)
        
        self.switch_sos = ToggleSwitch(window_section)
        self.switch_sos.setChecked(config.load_start_on_startup())
        _add_gen_row(window_inner, "Start on Startup", "Open Ticky automatically when you sign in", self.switch_sos)
        
        # Display Card
        display_section = QFrame(gen_content)
        display_section.setObjectName("SettingSection")

        display_inner = QVBoxLayout(display_section)
        display_inner.setContentsMargins(12, 10, 12, 10)
        display_inner.setSpacing(0)
        
        self.switch_tfh = ToggleSwitch(display_section)
        self.switch_tfh.setChecked(config.load_use_24h())
        _add_gen_row(display_inner, "24-Hour Format", "Display clock using 24-hour style", self.switch_tfh)
        
        _add_divider(display_inner)
        
        self.switch_dat = ToggleSwitch(display_section)
        self.switch_dat.setChecked(config.load_show_date())
        _add_gen_row(display_inner, "Show Date", "Display date under the clock", self.switch_dat)
        
        # Privacy & Streaming Card
        streaming_section = QFrame(gen_content)
        streaming_section.setObjectName("SettingSection")
        streaming_inner = QVBoxLayout(streaming_section)
        streaming_inner.setContentsMargins(12, 10, 12, 10)
        streaming_inner.setSpacing(0)
        
        self.switch_hide_streaming = ToggleSwitch(streaming_section)
        self.switch_hide_streaming.setChecked(config.load_hide_while_streaming())
        self.switch_hide_streaming.toggled_state.connect(self.on_hide_streaming_toggled)
        _add_gen_row(
            streaming_inner, 
            "Hide while streaming", 
            "Ticky stays visible to you but is hidden from supported screen captures.", 
            self.switch_hide_streaming
        )

        # Updates Card
        updates_section = QFrame(gen_content)
        updates_section.setObjectName("SettingSection")
        updates_inner = QVBoxLayout(updates_section)
        updates_inner.setContentsMargins(12, 10, 12, 10)
        updates_inner.setSpacing(0)

        self.switch_update_notify = ToggleSwitch(updates_section)
        self.switch_update_notify.setChecked(config.load_check_for_updates())
        _add_gen_row(
            updates_inner,
            "Check for updates on startup",
            "Ask GitHub for a newer release when Ticky starts.",
            self.switch_update_notify
        )

        _add_divider(updates_inner)

        self.btn_check_updates = QPushButton("Check now", updates_section)
        self.btn_check_updates.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_check_updates.setStyleSheet(self.get_action_button_style())
        self.btn_check_updates.clicked.connect(self.check_for_updates_now)
        _add_gen_row(
            updates_inner,
            f"Version {APP_VERSION}",
            "Compare with the newest published release.",
            self.btn_check_updates
        )

        self.lbl_update_status = QLabel("", updates_section)
        self.lbl_update_status.setObjectName("SettingDescription")
        self.lbl_update_status.setWordWrap(True)
        updates_inner.addWidget(self.lbl_update_status)

        lbl_sys_title = QLabel("System & Behavior", gen_content)
        lbl_sys_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_sys_title)
        gen_content_layout.addWidget(window_section)

        lbl_streaming_title = QLabel("Privacy & Streaming", gen_content)
        lbl_streaming_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_streaming_title)
        gen_content_layout.addWidget(streaming_section)

        
        lbl_disp_title = QLabel("Display Options", gen_content)
        lbl_disp_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_disp_title)
        gen_content_layout.addWidget(display_section)

        lbl_updates_title = QLabel("Updates", gen_content)
        lbl_updates_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_updates_title)
        gen_content_layout.addWidget(updates_section)
        gen_content_layout.addStretch()
        
        gen_scroll.setWidget(gen_content)
        page_general_layout.addWidget(gen_scroll)
        
        self.btn_save_general = QPushButton("Save Settings", page_general)
        self.btn_save_general.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_general.setStyleSheet(self.get_action_button_style())
        self.btn_save_general.clicked.connect(self.save_general_settings)
        page_general_layout.addWidget(self.btn_save_general)
        
        self.stacked_widget.addWidget(page_general)
        
        # --- Page 2: Clock Style ---
        page_clock = QWidget()
        clock_page_layout = QVBoxLayout(page_clock)
        clock_page_layout.setContentsMargins(0, 0, 0, 0)
        clock_page_layout.setSpacing(8)

        clock_scroll = QScrollArea(page_clock)
        clock_scroll.setObjectName("ClockSettingsScroll")
        clock_scroll.setWidgetResizable(True)
        clock_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        clock_content = QWidget()
        clock_content.setObjectName("ClockScrollContent")
        clock_layout = QVBoxLayout(clock_content)
        clock_layout.setContentsMargins(0, 2, 4, 2)
        clock_layout.setSpacing(10)

        lbl_style_head = QLabel("Layout", clock_content)
        lbl_style_head.setObjectName("SettingSectionTitle")
        clock_layout.addWidget(lbl_style_head)

        lbl_style_desc = QLabel("Pick a clock display style for the header.", clock_content)
        lbl_style_desc.setObjectName("SettingDescription")
        clock_layout.addWidget(lbl_style_desc)

        cards_scroll = QScrollArea(clock_content)
        cards_scroll.setObjectName("CardsScrollArea")
        cards_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cards_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cards_scroll.setFixedHeight(116)
        cards_scroll.setWidgetResizable(True)

        cards_row = QWidget()
        cards_row.setObjectName("CardsRow")
        cards_row.setMinimumWidth(446)
        cards_row_layout = QHBoxLayout(cards_row)
        cards_row_layout.setContentsMargins(2, 2, 2, 2)
        cards_row_layout.setSpacing(8)
        cards_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.clock_style_cards = {}
        self.current_clock_style = config.load_clock_style("neon")

        clock_style_defs = [
            ("classic", "Classic",  "08:13",   "THU, JUL 10",  "CardPreviewTime"),
            ("casio",   "Casio",    "08:13",    "THU  JUL 10",  "CardPreviewTimeCasio"),
            ("minimal", "Minimal",  "08:13",    "",             "CardPreviewTime"),
            ("neon",    "Neon",     "08:13",    "THU, JUL 10",  "CardPreviewTimeNeon"),
        ]

        for style_key, display_name, time_preview, date_preview, time_obj_name in clock_style_defs:
            card = self._make_clock_style_card(
                clock_content, style_key, display_name,
                time_preview, date_preview, time_obj_name,
                active=(style_key == self.current_clock_style)
            )
            self.clock_style_cards[style_key] = card
            cards_row_layout.addWidget(card)

        cards_scroll.setWidget(cards_row)
        clock_layout.addWidget(cards_scroll)

        options_frame = QFrame(clock_content)
        options_frame.setObjectName("SettingSection")
        options_inner = QVBoxLayout(options_frame)
        options_inner.setContentsMargins(12, 10, 12, 10)
        options_inner.setSpacing(0)

        lbl_options_head = QLabel("Display", options_frame)
        lbl_options_head.setObjectName("SettingSectionTitle")
        options_inner.addWidget(lbl_options_head)

        def _add_option_row(label, desc, widget):
            row = QHBoxLayout()
            row.setContentsMargins(0, 8, 0, 8)
            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            lbl = QLabel(label, options_frame)
            lbl.setObjectName("SettingLabel")
            lbl_desc = QLabel(desc, options_frame)
            lbl_desc.setObjectName("SettingDescription")
            text_col.addWidget(lbl)
            text_col.addWidget(lbl_desc)
            row.addLayout(text_col, 1)
            row.addWidget(widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            options_inner.addLayout(row)

        self.switch_clock_box = ToggleSwitch(options_frame)
        self.switch_clock_box.setChecked(config.load_clock_box_bg(False))
        _add_option_row("Background Box", "Glass backdrop behind the clock", self.switch_clock_box)

        sep_opt = QFrame(options_frame)
        sep_opt.setObjectName("SettingRowDivider")
        sep_opt.setFixedHeight(1)
        options_inner.addWidget(sep_opt)

        self.switch_seconds = ToggleSwitch(options_frame)
        self.switch_seconds.setChecked(config.load_show_seconds(True))
        _add_option_row("Show Seconds", "Include seconds in the time display", self.switch_seconds)

        sep_opt2 = QFrame(options_frame)
        sep_opt2.setObjectName("SettingRowDivider")
        sep_opt2.setFixedHeight(1)
        options_inner.addWidget(sep_opt2)

        weight_row = QHBoxLayout()
        weight_row.setContentsMargins(0, 8, 0, 8)
        weight_text = QVBoxLayout()
        weight_text.setSpacing(1)
        lbl_weight = QLabel("Font Weight", options_frame)
        lbl_weight.setObjectName("SettingLabel")
        lbl_weight_desc = QLabel("Semibold or bold clock digits", options_frame)
        lbl_weight_desc.setObjectName("SettingDescription")
        weight_text.addWidget(lbl_weight)
        weight_text.addWidget(lbl_weight_desc)

        weight_buttons_layout = QHBoxLayout()
        weight_buttons_layout.setSpacing(6)
        self.btn_weight_semibold = QPushButton("Semibold", options_frame)
        self.btn_weight_semibold.setObjectName("ClockWeightButton")
        self.btn_weight_semibold.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_weight_semibold.clicked.connect(lambda: self.select_clock_weight("500"))
        self.btn_weight_bold = QPushButton("Bold", options_frame)
        self.btn_weight_bold.setObjectName("ClockWeightButton")
        self.btn_weight_bold.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_weight_bold.clicked.connect(lambda: self.select_clock_weight("700"))
        self.select_clock_weight(self.clock_weight)
        weight_buttons_layout.addWidget(self.btn_weight_semibold)
        weight_buttons_layout.addWidget(self.btn_weight_bold)

        weight_row.addLayout(weight_text, 1)
        weight_row.addLayout(weight_buttons_layout, 0)
        options_inner.addLayout(weight_row)

        clock_layout.addWidget(options_frame)
        clock_layout.addStretch()

        clock_scroll.setWidget(clock_content)
        clock_page_layout.addWidget(clock_scroll)

        self.btn_save_clock = QPushButton("Save Clock Settings", page_clock)
        self.btn_save_clock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_clock.setStyleSheet(self.get_action_button_style())
        self.btn_save_clock.clicked.connect(self.save_clock_settings)
        clock_page_layout.addWidget(self.btn_save_clock)

        self.stacked_widget.addWidget(page_clock)
        
        # --- Page 4: Tasks Customization ---
        page_tasks = QWidget()
        page_tasks_layout = QVBoxLayout(page_tasks)
        page_tasks_layout.setContentsMargins(0, 0, 0, 0)
        page_tasks_layout.setSpacing(10)
        
        tasks_scroll = QScrollArea(page_tasks)
        tasks_scroll.setObjectName("TasksSettingsScroll")
        tasks_scroll.setWidgetResizable(True)
        tasks_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        tasks_content = QWidget()
        tasks_content.setObjectName("TasksScrollContent")
        tasks_content_layout = QVBoxLayout(tasks_content)
        tasks_content_layout.setContentsMargins(0, 2, 4, 2)
        tasks_content_layout.setSpacing(12)
        
        accent_section = QFrame(tasks_content)
        accent_section.setObjectName("SettingSection")
        accent_inner = QVBoxLayout(accent_section)
        accent_inner.setContentsMargins(12, 10, 12, 10)
        accent_inner.setSpacing(8)
        
        lbl_col = QLabel("Accent Color", accent_section)
        lbl_col.setObjectName("SettingLabel")
        lbl_col_desc = QLabel("Select the highlight & active state color", accent_section)
        lbl_col_desc.setObjectName("SettingDescription")
        accent_inner.addWidget(lbl_col)
        accent_inner.addWidget(lbl_col_desc)

        swatches_layout = QHBoxLayout()
        swatches_layout.setSpacing(8)
        swatches_layout.setContentsMargins(0, 0, 0, 0)
        swatches_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.swatches = []
        colors = theme.ACCENT_PRESETS
        current_accent = config.load_accent_color()
        for hex_color in colors:
            is_active = (hex_color.lower() == current_accent.lower())
            swatch = ColorSwatch(hex_color, is_active, accent_section)
            swatch.color_selected.connect(self.on_accent_color_changed)
            swatches_layout.addWidget(swatch)
            self.swatches.append(swatch)

        accent_inner.addLayout(swatches_layout)

        # --- Custom accent: colour picker + hex input ---
        custom_row = QHBoxLayout()
        custom_row.setSpacing(8)
        custom_row.setContentsMargins(0, 2, 0, 0)

        self.btn_custom_accent = QPushButton(accent_section)
        self.btn_custom_accent.setObjectName("AccentCustomSwatch")
        self.btn_custom_accent.setFixedSize(26, 26)
        self.btn_custom_accent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_accent.setToolTip("Pick a custom accent color")
        self.btn_custom_accent.clicked.connect(self.pick_custom_accent)

        lbl_custom = QLabel("Custom", accent_section)
        lbl_custom.setObjectName("SettingDescription")

        self.hex_accent_input = QLineEdit(accent_section)
        self.hex_accent_input.setObjectName("AccentHexInput")
        self.hex_accent_input.setFixedSize(92, 26)
        self.hex_accent_input.setMaxLength(7)
        self.hex_accent_input.setPlaceholderText("#RRGGBB")
        self.hex_accent_input.setText(current_accent.upper())
        self.hex_accent_input.setValidator(QRegularExpressionValidator(QRegularExpression("#?[0-9A-Fa-f]{0,6}"), self))
        self.hex_accent_input.textChanged.connect(self._update_custom_accent_preview)
        self.hex_accent_input.returnPressed.connect(self.apply_hex_accent)

        btn_hex_apply = QPushButton("Apply", accent_section)
        btn_hex_apply.setObjectName("AccentHexApply")
        btn_hex_apply.setFixedHeight(26)
        btn_hex_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hex_apply.clicked.connect(self.apply_hex_accent)

        custom_row.addWidget(self.btn_custom_accent)
        custom_row.addWidget(lbl_custom)
        custom_row.addSpacing(6)
        custom_row.addWidget(self.hex_accent_input)
        custom_row.addWidget(btn_hex_apply)
        custom_row.addStretch()
        accent_inner.addLayout(custom_row)
        self._update_custom_accent_preview(self.hex_accent_input.text())
        
        size_section = QFrame(tasks_content)
        size_section.setObjectName("SettingSection")
        size_inner = QVBoxLayout(size_section)
        size_inner.setContentsMargins(12, 10, 12, 10)
        size_inner.setSpacing(8)
        
        slider_header = QHBoxLayout()
        lbl_siz = QLabel("Task Font Size", size_section)
        lbl_siz.setObjectName("SettingLabel")
        self.lbl_siz_val = QLabel(f"{config.load_task_font_size()}px", size_section)
        self.lbl_siz_val.setObjectName("SettingDescription")
        self.lbl_siz_val.setStyleSheet("font-weight: bold;")
        slider_header.addWidget(lbl_siz)
        slider_header.addStretch()
        slider_header.addWidget(self.lbl_siz_val)
        size_inner.addLayout(slider_header)
        
        slider_container = QHBoxLayout()
        slider_container.setSpacing(8)
        lbl_min_sz = QLabel("11px", size_section)
        lbl_min_sz.setObjectName("SettingDescription")
        lbl_max_sz = QLabel("16px", size_section)
        lbl_max_sz.setObjectName("SettingDescription")
        
        self.slider_size = QSlider(Qt.Orientation.Horizontal, size_section)
        self.slider_size.setRange(11, 16)
        self.slider_size.setValue(config.load_task_font_size())
        self.slider_size.setSingleStep(1)
        self.slider_size.setCursor(Qt.CursorShape.PointingHandCursor)
        self.slider_size.valueChanged.connect(self.on_task_font_size_changed)
        
        slider_container.addWidget(lbl_min_sz)
        slider_container.addWidget(self.slider_size)
        slider_container.addWidget(lbl_max_sz)
        size_inner.addLayout(slider_container)
        
        lbl_theme_title = QLabel("Theme Styling", tasks_content)
        lbl_theme_title.setObjectName("SettingSectionTitle")
        tasks_content_layout.addWidget(lbl_theme_title)
        tasks_content_layout.addWidget(accent_section)

        # --- UI Color Theme selector ---
        lbl_ui_theme_title = QLabel("UI Color Theme", tasks_content)
        lbl_ui_theme_title.setObjectName("SettingSectionTitle")
        tasks_content_layout.addWidget(lbl_ui_theme_title)

        theme_section = QFrame(tasks_content)
        theme_section.setObjectName("SettingSection")
        theme_inner = QVBoxLayout(theme_section)
        theme_inner.setContentsMargins(12, 10, 12, 10)
        theme_inner.setSpacing(8)

        lbl_theme_desc = QLabel("Changes the background and panel colors across the entire widget", theme_section)
        lbl_theme_desc.setObjectName("SettingDescription")
        theme_inner.addWidget(lbl_theme_desc)

        self.theme_cards = {}
        current_theme_name = config.load_theme("Amoled Pure")

        theme_grid = QGridLayout()
        theme_grid.setSpacing(8)
        theme_grid.setContentsMargins(0, 0, 0, 0)

        for i, (t_name, t_data) in enumerate(theme.THEMES.items()):
            is_active = (t_name == current_theme_name)
            card = ThemeStyleCard(t_name, t_data, is_active, theme_section)
            card.theme_selected.connect(self.on_theme_changed)
            self.theme_cards[t_name] = card
            theme_grid.addWidget(card, i // 5, i % 5, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        theme_inner.addLayout(theme_grid)
        tasks_content_layout.addWidget(theme_section)

        lbl_text_title = QLabel("Text Configuration", tasks_content)
        lbl_text_title.setObjectName("SettingSectionTitle")
        tasks_content_layout.addWidget(lbl_text_title)
        tasks_content_layout.addWidget(size_section)
        
        # Font Family selection (merged from the former Fonts page)
        lbl_font_title = QLabel("Font Family", tasks_content)
        lbl_font_title.setObjectName("SettingSectionTitle")
        tasks_content_layout.addWidget(lbl_font_title)
        
        font_section = QFrame(tasks_content)
        font_section.setObjectName("SettingSection")
        font_inner = QVBoxLayout(font_section)
        font_inner.setContentsMargins(12, 10, 12, 10)
        font_inner.setSpacing(8)
        
        lbl_fonts_desc = QLabel("Select active application typeface family:", font_section)
        lbl_fonts_desc.setObjectName("SettingDescription")
        font_inner.addWidget(lbl_fonts_desc)
        
        fonts_list = [
            "Inter", "Manrope", "Nunito", "DM Sans", "General Sans",
            "Satoshi", "Plus Jakarta Sans", "Outfit", "IBM Plex Sans", "Space Grotesk"
        ]
        
        font_grid = QGridLayout()
        font_grid.setSpacing(6)
        self.font_buttons = []
        for i, font_name in enumerate(fonts_list):
            btn_font = QPushButton(font_name, font_section)
            btn_font.setObjectName("FontItemButton")
            btn_font.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_font.setFont(QFont(font_name, 10, QFont.Weight.Medium))
            is_active = (font_name.lower() == self.selected_font.lower())
            btn_font.setProperty("active", "true" if is_active else "false")
            btn_font.clicked.connect(lambda checked=False, f=font_name: self.on_font_selected(f))
            font_grid.addWidget(btn_font, i // 2, i % 2)
            self.font_buttons.append(btn_font)
        font_inner.addLayout(font_grid)
        
        self.btn_save_fonts = QPushButton("Save Font", font_section)
        self.btn_save_fonts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_fonts.setStyleSheet(self.get_action_button_style())
        self.btn_save_fonts.clicked.connect(self.save_font_settings)
        font_inner.addWidget(self.btn_save_fonts)
        
        tasks_content_layout.addWidget(font_section)
        
        lbl_dynamic_save_notice = QLabel("💡 Colors, themes and font sizes are saved dynamically.", tasks_content)
        lbl_dynamic_save_notice.setObjectName("SettingDescription")
        lbl_dynamic_save_notice.setStyleSheet("color: #FF9F0A; padding-top: 8px;")
        tasks_content_layout.addWidget(lbl_dynamic_save_notice)
        tasks_content_layout.addStretch()
        
        tasks_scroll.setWidget(tasks_content)
        page_tasks_layout.addWidget(tasks_scroll)
        
        self.stacked_widget.addWidget(page_tasks)
        
        # --- Page 5: Spotify settings ---
        page_spotify = QWidget()
        page_spotify_layout = QVBoxLayout(page_spotify)
        page_spotify_layout.setContentsMargins(0, 0, 0, 0)
        page_spotify_layout.setSpacing(10)
        
        spot_scroll = QScrollArea(page_spotify)
        spot_scroll.setObjectName("SpotifySettingsScroll")
        spot_scroll.setWidgetResizable(True)
        spot_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        spot_content = QWidget()
        spot_content.setObjectName("SpotifyScrollContent")
        spot_content_layout = QVBoxLayout(spot_content)
        spot_content_layout.setContentsMargins(0, 2, 4, 2)
        spot_content_layout.setSpacing(12)
        
        status_section = QFrame(spot_content)
        status_section.setObjectName("SettingSection")
        status_inner = QVBoxLayout(status_section)
        status_inner.setContentsMargins(12, 10, 12, 10)
        status_inner.setSpacing(8)
        
        # 1. Integration Mode Row
        mode_row = QHBoxLayout()
        mode_row.setContentsMargins(0, 4, 0, 4)
        mode_text_col = QVBoxLayout()
        mode_text_col.setSpacing(2)
        lbl_mode = QLabel("Integration Mode", status_section)
        lbl_mode.setObjectName("SettingLabel")
        lbl_mode_desc = QLabel("Select media control backend source", status_section)
        lbl_mode_desc.setObjectName("SettingDescription")
        mode_text_col.addWidget(lbl_mode)
        mode_text_col.addWidget(lbl_mode_desc)
        
        self.combo_spot_mode = QComboBox(status_section)
        self.combo_spot_mode.addItems(["Automatic (Windows Media)", "Spotify Developer API (Advanced)"])
        self.combo_spot_mode.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(0, 0, 0, 60);
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                padding: 4px 8px;
                min-width: 170px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        current_mode = config.load_spotify_backend_mode("gsmtc")
        self.combo_spot_mode.setCurrentIndex(0 if current_mode == "gsmtc" else 1)
        self.combo_spot_mode.currentIndexChanged.connect(self.on_spot_mode_changed)
        
        mode_row.addLayout(mode_text_col, 1)
        mode_row.addWidget(self.combo_spot_mode, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_inner.addWidget(self.combo_spot_mode)
        status_inner.addLayout(mode_row)
        
        sep_spot = QFrame(status_section)
        sep_spot.setObjectName("SettingRowDivider")
        sep_spot.setFixedHeight(1)
        status_inner.addWidget(sep_spot)

        self.lbl_spot_status = QLabel("● Automatic Media Integration Active", status_section)
        self.lbl_spot_status.setObjectName("SettingDescription")
        status_inner.addWidget(self.lbl_spot_status)
        
        self.lbl_spotify_guide = QLabel(
            "<b>Automatic (Windows Media):</b><br>"
            "Ticky uses native Windows Global System Media Transport Controls (GSMTC) to automatically detect and control <b>Spotify Desktop</b> and <b>Spotify Web Player</b>.<br>"
            "No Client ID, Secret, or OAuth setup required.", 
            status_section
        )
        self.lbl_spotify_guide.setObjectName("SettingDescription")
        self.lbl_spotify_guide.setOpenExternalLinks(False)
        self.lbl_spotify_guide.setWordWrap(True)
        self.lbl_spotify_guide.setStyleSheet(f"""
            QLabel#SettingDescription {{
                line-height: 1.3;
                color: {theme.TEXT_SECONDARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 9px;
            }}
        """)
        
        def handle_guide_link(url_str):
            if url_str == "copy":
                from PySide6.QtWidgets import QApplication
                clipboard = QApplication.clipboard()
                if clipboard:
                    clipboard.setText("http://127.0.0.1:8888/callback")
                    orig_text = self.lbl_spotify_guide.text()
                    feedback_text = orig_text.replace("http://127.0.0.1:8888/callback", "Copied to clipboard!")
                    self.lbl_spotify_guide.setText(feedback_text)
                    QTimer.singleShot(1500, lambda: self.lbl_spotify_guide.setText(orig_text))
            else:
                import webbrowser
                webbrowser.open(url_str)
                
        self.lbl_spotify_guide.linkActivated.connect(handle_guide_link)
        status_inner.addWidget(self.lbl_spotify_guide)
        
        self.creds_section = QFrame(spot_content)
        self.creds_section.setObjectName("SettingSection")
        creds_inner = QVBoxLayout(self.creds_section)
        creds_inner.setContentsMargins(12, 10, 12, 10)
        creds_inner.setSpacing(8)
        
        self.lbl_creds_title = QLabel("Spotify Developer API Configuration", self.creds_section)
        self.lbl_creds_title.setObjectName("SettingLabel")
        creds_inner.addWidget(self.lbl_creds_title)
        
        self.input_client_id = QLineEdit(self.creds_section)
        self.input_client_id.setObjectName("SpotifyInput")
        self.input_client_id.setPlaceholderText("Spotify Client ID")
        
        self.input_client_secret = QLineEdit(self.creds_section)
        self.input_client_secret.setObjectName("SpotifyInput")
        self.input_client_secret.setPlaceholderText("Spotify Client Secret")
        self.input_client_secret.setEchoMode(QLineEdit.EchoMode.Password)
        
        saved_id, saved_secret = config.load_spotify_credentials()
        self.input_client_id.setText(saved_id)
        self.input_client_secret.setText(saved_secret)
        
        creds_inner.addWidget(self.input_client_id)
        creds_inner.addWidget(self.input_client_secret)
        
        lbl_conn_title = QLabel("Connection & Mode", spot_content)
        lbl_conn_title.setObjectName("SettingSectionTitle")
        spot_content_layout.addWidget(lbl_conn_title)
        spot_content_layout.addWidget(status_section)
        
        self.lbl_api_title = QLabel("Developer API Configuration (Optional)", spot_content)
        self.lbl_api_title.setObjectName("SettingSectionTitle")
        spot_content_layout.addWidget(self.lbl_api_title)
        spot_content_layout.addWidget(self.creds_section)
        spot_content_layout.addStretch()
        
        spot_scroll.setWidget(spot_content)
        page_spotify_layout.addWidget(spot_scroll)
        
        spot_btn_layout = QHBoxLayout()
        spot_btn_layout.setSpacing(10)
        spot_btn_layout.setContentsMargins(0, 4, 0, 0)
        
        self.btn_save_spotify = QPushButton("Save Mode / Credentials", page_spotify)
        self.btn_save_spotify.setStyleSheet(self.get_action_button_style())
        self.btn_save_spotify.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_spotify.clicked.connect(self.save_spotify_creds)
        
        self.btn_connect_spotify = QPushButton("Connect Account", page_spotify)
        self.btn_connect_spotify.setStyleSheet(self.get_action_button_style())
        self.btn_connect_spotify.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect_spotify.clicked.connect(self.connect_spotify_account)
        
        spot_btn_layout.addWidget(self.btn_save_spotify)
        spot_btn_layout.addWidget(self.btn_connect_spotify)
        page_spotify_layout.addLayout(spot_btn_layout)
        
        self.stacked_widget.addWidget(page_spotify)

        
        # --- Page 6: AI settings ---
        page_ai = QWidget()
        page_ai_layout = QVBoxLayout(page_ai)
        page_ai_layout.setContentsMargins(0, 0, 0, 0)
        page_ai_layout.setSpacing(10)
        
        ai_scroll = QScrollArea(page_ai)
        ai_scroll.setObjectName("AISettingsScroll")
        ai_scroll.setWidgetResizable(True)
        ai_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        ai_content = QWidget()
        ai_content.setObjectName("AIScrollContent")
        ai_content_layout = QVBoxLayout(ai_content)
        ai_content_layout.setContentsMargins(0, 0, 0, 0)
        ai_content_layout.setSpacing(12)
        
        # Guide section
        ai_guide_section = QFrame(ai_content)
        ai_guide_section.setObjectName("SettingSection")
        ai_guide_inner = QVBoxLayout(ai_guide_section)
        ai_guide_inner.setContentsMargins(12, 10, 12, 10)
        
        lbl_ai_guide_title = QLabel("AI Companion Setup", ai_guide_section)
        lbl_ai_guide_title.setObjectName("SettingLabel")
        lbl_ai_guide_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        ai_guide_inner.addWidget(lbl_ai_guide_title)
        
        self.lbl_ai_guide = QLabel(ai_guide_section)
        self.lbl_ai_guide.setObjectName("SettingDescription")
        self.lbl_ai_guide.setOpenExternalLinks(True)
        self.lbl_ai_guide.setWordWrap(True)
        self.lbl_ai_guide.setStyleSheet(f"""
            QLabel#SettingDescription {{
                line-height: 1.3;
                color: {theme.TEXT_SECONDARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 9px;
            }}
        """)
        ai_guide_inner.addWidget(self.lbl_ai_guide)
        
        # Credentials section
        ai_creds_section = QFrame(ai_content)
        ai_creds_section.setObjectName("SettingSection")
        ai_creds_inner = QVBoxLayout(ai_creds_section)
        ai_creds_inner.setContentsMargins(12, 10, 12, 10)
        
        # Provider Row
        provider_row = QHBoxLayout()
        lbl_provider = QLabel("AI Provider:", ai_creds_section)
        lbl_provider.setObjectName("SettingLabel")
        lbl_provider.setStyleSheet("font-weight: bold; font-size: 11px;")
        
        self.combo_provider = QComboBox(ai_creds_section)
        self.combo_provider.addItems(["Gemini", "OpenAI", "Claude", "Groq", "OpenRouter"])
        self.combo_provider.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(0, 0, 0, 60);
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                padding: 4px 8px;
                min-width: 120px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.combo_provider.setCurrentText(config.load_ai_provider())
        self.combo_provider.currentTextChanged.connect(self.on_ai_provider_changed)
        
        provider_row.addWidget(lbl_provider)
        provider_row.addWidget(self.combo_provider, 0, Qt.AlignmentFlag.AlignRight)
        ai_creds_inner.addLayout(provider_row)
        
        # Spacer Line
        sep = QFrame(ai_creds_section)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {theme.BORDER_COLOR}; max-height: 1px;")
        ai_creds_inner.addWidget(sep)
        
        # API Key Row
        lbl_ai_key_title = QLabel("API Key", ai_creds_section)
        lbl_ai_key_title.setObjectName("SettingLabel")
        lbl_ai_key_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        ai_creds_inner.addWidget(lbl_ai_key_title)
        
        self.input_ai_key = QLineEdit(ai_creds_section)
        self.input_ai_key.setObjectName("SpotifyInput")
        self.input_ai_key.setPlaceholderText("Paste your API Key here")
        self.input_ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_ai_key.setText(config.load_ai_api_key())
        ai_creds_inner.addWidget(self.input_ai_key)
        
        # Model Row
        lbl_ai_model_title = QLabel("AI Model", ai_creds_section)
        lbl_ai_model_title.setObjectName("SettingLabel")
        lbl_ai_model_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        ai_creds_inner.addWidget(lbl_ai_model_title)
        
        self.input_ai_model = QLineEdit(ai_creds_section)
        self.input_ai_model.setObjectName("SpotifyInput")
        self.input_ai_model.setPlaceholderText("e.g. gemini-1.5-flash")
        self.input_ai_model.setText(config.load_ai_model())
        ai_creds_inner.addWidget(self.input_ai_model)

        # Voice Dictation section (microphone selection)
        dictation_section = QFrame(ai_content)
        dictation_section.setObjectName("SettingSection")
        dictation_inner = QVBoxLayout(dictation_section)
        dictation_inner.setContentsMargins(12, 10, 12, 10)

        mic_row = QHBoxLayout()
        lbl_mic = QLabel("Microphone:", dictation_section)
        lbl_mic.setObjectName("SettingLabel")
        lbl_mic.setStyleSheet("font-weight: bold; font-size: 11px;")

        from PySide6.QtMultimedia import QMediaDevices
        self._media_devices = QMediaDevices(self)
        self.combo_mic = QComboBox(dictation_section)
        self.combo_mic.setStyleSheet(f"""
            QComboBox {{
                background-color: rgba(0, 0, 0, 60);
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                padding: 4px 8px;
                min-width: 180px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        self.combo_mic.addItem("System Default", "")
        for dev in self._media_devices.audioInputs():
            self.combo_mic.addItem(dev.description(), dev.id())
        saved_mic = config.load_mic_device_id("")
        saved_idx = self.combo_mic.findData(saved_mic)
        self.combo_mic.setCurrentIndex(saved_idx if saved_idx >= 0 else 0)
        self.combo_mic.currentIndexChanged.connect(self.on_mic_changed)

        mic_row.addWidget(lbl_mic)
        mic_row.addWidget(self.combo_mic, 0, Qt.AlignmentFlag.AlignRight)
        dictation_inner.addLayout(mic_row)

        lbl_mic_hint = QLabel(
            "Used by Voice Dictation (global hotkey). Pick a specific mic, or System Default.",
            dictation_section
        )
        lbl_mic_hint.setObjectName("SettingDescription")
        lbl_mic_hint.setWordWrap(True)
        lbl_mic_hint.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 9px;")
        dictation_inner.addWidget(lbl_mic_hint)

        # Live input level meter — lets the user SEE which mic hears them
        self.mic_level_bar = MicLevelBar(dictation_section)
        dictation_inner.addWidget(self.mic_level_bar)
        lbl_meter_hint = QLabel(
            "Speak into your mic — this bar should move. If it stays flat while you talk, "
            "your voice is going to a different device: pick that one above.",
            dictation_section
        )
        lbl_meter_hint.setObjectName("SettingDescription")
        lbl_meter_hint.setWordWrap(True)
        lbl_meter_hint.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 9px;")
        dictation_inner.addWidget(lbl_meter_hint)

        self._meter_source = None
        self._meter_io = None
        self._meter_fmt = None
        self._meter_level = 0.0
        self._meter_timer = QTimer(self)
        self._meter_timer.setInterval(50)
        self._meter_timer.timeout.connect(self._tick_mic_meter)

        ai_content_layout.addWidget(ai_guide_section)
        ai_content_layout.addWidget(ai_creds_section)
        ai_content_layout.addWidget(dictation_section)
        ai_content_layout.addStretch()
        
        ai_scroll.setWidget(ai_content)
        page_ai_layout.addWidget(ai_scroll)
        
        ai_btn_layout = QHBoxLayout()
        ai_btn_layout.setSpacing(10)
        ai_btn_layout.setContentsMargins(0, 4, 0, 0)
        
        self.btn_save_ai = QPushButton("Save Config", page_ai)
        self.btn_save_ai.setStyleSheet(self.get_action_button_style())
        self.btn_save_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_ai.clicked.connect(self.save_ai_key)
        
        ai_btn_layout.addWidget(self.btn_save_ai)
        page_ai_layout.addLayout(ai_btn_layout)
        
        self.stacked_widget.addWidget(page_ai)
        
        # --- Page 7: Shortcuts Settings ---
        page_shortcuts = QWidget()
        page_shortcuts_layout = QVBoxLayout(page_shortcuts)
        page_shortcuts_layout.setContentsMargins(0, 0, 0, 0)
        page_shortcuts_layout.setSpacing(10)
        
        shortcut_scroll = QScrollArea(page_shortcuts)
        shortcut_scroll.setObjectName("ShortcutsSettingsScroll")
        shortcut_scroll.setWidgetResizable(True)
        shortcut_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        shortcut_content = QWidget()
        shortcut_content.setObjectName("ShortcutsScrollContent")
        shortcut_content_layout = QVBoxLayout(shortcut_content)
        shortcut_content_layout.setContentsMargins(0, 0, 4, 0)
        shortcut_content_layout.setSpacing(12)
        
        # Guide section
        shortcuts_guide_section = QFrame(shortcut_content)
        shortcuts_guide_section.setObjectName("SettingSection")
        shortcuts_guide_inner = QVBoxLayout(shortcuts_guide_section)
        shortcuts_guide_inner.setContentsMargins(12, 10, 12, 10)
        
        lbl_shortcuts_guide_title = QLabel("Keyboard Shortcuts", shortcuts_guide_section)
        lbl_shortcuts_guide_title.setObjectName("SettingLabel")
        lbl_shortcuts_guide_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        
        lbl_shortcuts_guide_desc = QLabel(
            "Configure global hotkeys to control Ticky from anywhere on your system.<br>"
            "Click on an input box and press your key combination (e.g. <b>Alt+T</b>).<br>"
            "Voice Dictation expands the Notch, listens via your mic, and inserts speech into the focused text field.<br>"
            "Press <b>Backspace</b> or <b>Delete</b> to clear a shortcut.",
            shortcuts_guide_section
        )
        lbl_shortcuts_guide_desc.setObjectName("SettingDescription")
        lbl_shortcuts_guide_desc.setWordWrap(True)
        lbl_shortcuts_guide_desc.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 9px; line-height: 1.3;")
        
        shortcuts_guide_inner.addWidget(lbl_shortcuts_guide_title)
        shortcuts_guide_inner.addWidget(lbl_shortcuts_guide_desc)
        
        # Inputs Section
        inputs_section = QFrame(shortcut_content)
        inputs_section.setObjectName("SettingSection")
        inputs_inner = QVBoxLayout(inputs_section)
        inputs_inner.setContentsMargins(12, 10, 12, 10)
        inputs_inner.setSpacing(8)
        
        # 1. Toggle Window Shortcut Row
        row1 = QHBoxLayout()
        lbl_toggle = QLabel("Toggle Window:", inputs_section)
        lbl_toggle.setObjectName("SettingLabel")
        lbl_toggle.setStyleSheet("font-weight: bold; font-size: 11px;")
        
        self.input_toggle_shortcut = ShortcutLineEdit(inputs_section)
        self.input_toggle_shortcut.setFixedWidth(180)
        row1.addWidget(lbl_toggle)
        row1.addWidget(self.input_toggle_shortcut, 0, Qt.AlignmentFlag.AlignRight)
        inputs_inner.addLayout(row1)
        
        # Spacer Line
        sep_sc = QFrame(inputs_section)
        sep_sc.setObjectName("SettingRowDivider")
        sep_sc.setFixedHeight(1)
        inputs_inner.addWidget(sep_sc)
        
        # 2. New Task Shortcut Row
        row2 = QHBoxLayout()
        lbl_new_task = QLabel("Create New Task:", inputs_section)
        lbl_new_task.setObjectName("SettingLabel")
        lbl_new_task.setStyleSheet("font-weight: bold; font-size: 11px;")
        
        self.input_new_task_shortcut = ShortcutLineEdit(inputs_section)
        self.input_new_task_shortcut.setFixedWidth(180)
        row2.addWidget(lbl_new_task)
        row2.addWidget(self.input_new_task_shortcut, 0, Qt.AlignmentFlag.AlignRight)
        inputs_inner.addLayout(row2)

        # Spacer Line
        sep_sc2 = QFrame(inputs_section)
        sep_sc2.setObjectName("SettingRowDivider")
        sep_sc2.setFixedHeight(1)
        inputs_inner.addWidget(sep_sc2)

        # 3. Voice Dictation Shortcut Row
        row3 = QHBoxLayout()
        lbl_dictation = QLabel("Voice Dictation:", inputs_section)
        lbl_dictation.setObjectName("SettingLabel")
        lbl_dictation.setStyleSheet("font-weight: bold; font-size: 11px;")

        self.input_voice_dictation_shortcut = ShortcutLineEdit(inputs_section)
        self.input_voice_dictation_shortcut.setFixedWidth(180)
        row3.addWidget(lbl_dictation)
        row3.addWidget(self.input_voice_dictation_shortcut, 0, Qt.AlignmentFlag.AlignRight)
        inputs_inner.addLayout(row3)

        sep_sc3 = QFrame(inputs_section)
        sep_sc3.setFrameShape(QFrame.Shape.HLine)
        sep_sc3.setFrameShadow(QFrame.Shadow.Sunken)
        sep_sc3.setStyleSheet(f"background-color: {theme.BORDER_COLOR}; max-height: 1px;")
        inputs_inner.addWidget(sep_sc3)

        # 4. System-Wide App Search Shortcut Row
        row4 = QHBoxLayout()
        lbl_app_search = QLabel("App & Software Search:", inputs_section)
        lbl_app_search.setObjectName("SettingLabel")
        lbl_app_search.setStyleSheet("font-weight: bold; font-size: 11px;")

        self.input_app_search_shortcut = ShortcutLineEdit(inputs_section)
        self.input_app_search_shortcut.setFixedWidth(180)
        row4.addWidget(lbl_app_search)
        row4.addWidget(self.input_app_search_shortcut, 0, Qt.AlignmentFlag.AlignRight)
        inputs_inner.addLayout(row4)
        
        # Load values
        saved_shortcuts = config.load_shortcuts()
        self.input_toggle_shortcut.setText(saved_shortcuts.get("toggle_window", "Alt+T"))
        self.input_new_task_shortcut.setText(saved_shortcuts.get("new_task", "Alt+Q"))
        self.input_voice_dictation_shortcut.setText(saved_shortcuts.get("voice_dictation", "Alt+D"))
        self.input_app_search_shortcut.setText(saved_shortcuts.get("app_search", "Alt+W"))
        
        shortcut_content_layout.addWidget(shortcuts_guide_section)
        shortcut_content_layout.addWidget(inputs_section)
        shortcut_content_layout.addStretch()
        
        shortcut_scroll.setWidget(shortcut_content)
        page_shortcuts_layout.addWidget(shortcut_scroll)
        
        sc_btn_layout = QHBoxLayout()
        self.btn_save_shortcuts = QPushButton("Save Shortcuts", page_shortcuts)
        self.btn_save_shortcuts.setStyleSheet(self.get_action_button_style())
        self.btn_save_shortcuts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_shortcuts.clicked.connect(self.save_shortcut_settings)
        sc_btn_layout.addWidget(self.btn_save_shortcuts)
        page_shortcuts_layout.addLayout(sc_btn_layout)
        
        self.stacked_widget.addWidget(page_shortcuts)
        
        # Initialize dynamic welcome guide
        self.on_ai_provider_changed(self.combo_provider.currentText())
        
        content_layout.addWidget(self.stacked_widget, 1)
        
        # Separator line before exit button
        sep2 = QWidget(content_widget)
        sep2.setFixedHeight(1)
        sep2.setStyleSheet(f"background-color: {theme.BORDER_COLOR};")
        content_layout.addWidget(sep2)
        
        # Exit Application Button
        self.btn_exit = QPushButton("Exit Ticky", content_widget)
        self.btn_exit.setObjectName("ExitButton")
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self.exit_application)
        content_layout.addWidget(self.btn_exit)
        
        main_layout.addWidget(content_widget)
        
        # Apply drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
        
        outer_container_layout = QVBoxLayout(self)
        outer_container_layout.setContentsMargins(0, 0, 0, 0)
        outer_container_layout.addWidget(self.container)
        
        self._apply_fonts()
        self.update_spotify_status_ui()
        
        # Default active page: General
        self.switch_page(0)

    def switch_page(self, index):
        """Switch stacked pages and update sidebar active state with a smooth transition."""
        self.page_fade_anim.stop()
        self.opacity_effect.setEnabled(False)
        self.stacked_widget.setCurrentIndex(index)
        
        # Temporarily disable global hotkeys when entering the shortcuts page to prevent actions triggering
        if self.parent_window:
            if index == 5:
                if hasattr(self.parent_window, 'unregister_global_hotkeys'):
                    self.parent_window.unregister_global_hotkeys()
            else:
                if hasattr(self.parent_window, 'register_global_hotkeys'):
                    self.parent_window.register_global_hotkeys()
        
        # Update page header title
        titles = ["General Settings", "Clock Style Customization", "Appearance", "Media Player", "AI Config", "Keyboard Shortcuts"]
        self.lbl_page_title.setText(titles[index])
        
        # Update sidebar buttons style
        for i, btn in enumerate(self.sidebar_buttons):
            active_val = "true" if i == index else "false"
            btn.setProperty("active", active_val)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
        if self.isVisible():
            self.opacity_effect.setEnabled(True)
            self.opacity_effect.setOpacity(0.0)
            self.page_fade_anim.setStartValue(0.0)
            self.page_fade_anim.setEndValue(1.0)
            self.page_fade_anim.start()

    def _get_searchable_labels(self):
        """Lazily index every section/setting label on each page for the sidebar search."""
        if getattr(self, "_search_index_cache", None) is not None:
            return self._search_index_cache
        entries = []
        seen = set()
        for page_idx in range(self.stacked_widget.count()):
            page = self.stacked_widget.widget(page_idx)
            if page is None:
                continue
            category = self.sidebar_buttons[page_idx].text() if page_idx < len(self.sidebar_buttons) else ""
            key = (category.lower(), page_idx)
            if key not in seen:
                seen.add(key)
                entries.append((category, page_idx, category))
            for lbl in page.findChildren(QLabel):
                if lbl.objectName() not in ("SettingSectionTitle", "SettingLabel"):
                    continue
                text = lbl.text().strip()
                if not text:
                    continue
                key = (text.lower(), page_idx)
                if key in seen:
                    continue
                seen.add(key)
                entries.append((text, page_idx, category))
        self._search_index_cache = entries
        return entries

    def _on_settings_search(self, text):
        term = text.strip().lower()
        if not term:
            self.search_results.clear()
            self.search_results.setVisible(False)
            for btn in self.sidebar_buttons:
                btn.setVisible(True)
            return
        for btn in self.sidebar_buttons:
            btn.setVisible(False)
        self.search_results.clear()
        matches = [(label, page, cat) for label, page, cat in self._get_searchable_labels()
                   if term in label.lower()][:40]
        for label, page, cat in matches:
            item = QListWidgetItem(f"{label}  ·  {cat}")
            item.setData(Qt.ItemDataRole.UserRole, page)
            self.search_results.addItem(item)
        row_h = self.search_results.sizeHintForRow(0) if self.search_results.count() else 30
        self.search_results.setFixedHeight(min(320, self.search_results.count() * (row_h + 2) + 6))
        self.search_results.setVisible(True)

    def _on_search_result_clicked(self, item):
        page = item.data(Qt.ItemDataRole.UserRole)
        if page is None:
            return
        self.switch_page(int(page))
        self.search_edit.clear()

    def get_action_button_style(self):
        """Return the standard visual stylesheet for general action buttons."""
        return f"""
            QPushButton {{
                background-color: {theme.HOVER_COLOR};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                padding: 6px 12px;
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {theme.SEC_CARD_COLOR};
                border: 1px solid {theme.ACCENT_COLOR};
            }}
        """

    def select_clock_weight(self, weight):
        """Toggle active weight configuration values."""
        self.clock_weight = weight
        self.btn_weight_semibold.setProperty("active", "true" if weight == "500" else "false")
        self.btn_weight_bold.setProperty("active", "true" if weight == "700" else "false")
        self.btn_weight_semibold.style().unpolish(self.btn_weight_semibold)
        self.btn_weight_semibold.style().polish(self.btn_weight_semibold)
        self.btn_weight_bold.style().unpolish(self.btn_weight_bold)
        self.btn_weight_bold.style().polish(self.btn_weight_bold)
        preview_style = qss.get_clock_preview_card_style(weight)
        self.setStyleSheet(qss.get_settings_style() + qss.get_appearance_style() + preview_style)

    def on_font_selected(self, font_name):
        """Triggered when a font item is clicked in the Fonts scroll content list."""
        self.selected_font = font_name
        for btn in self.font_buttons:
            is_active = (btn.text().lower() == font_name.lower())
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Allow dragging the window only when clicking non-interactive header regions
            if event.position().y() < 40:
                self.drag_start_pos = event.globalPosition().toPoint()
                self.window_start_pos = self.pos()
                self.is_dragging = True
                event.accept()
                
    def mouseMoveEvent(self, event):
        if getattr(self, 'is_dragging', False):
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(self.window_start_pos + delta)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            event.accept()

    def update_settings_style(self):
        self.setStyleSheet(
            qss.get_settings_style()
            + qss.get_appearance_style()
            + qss.get_clock_preview_card_style(self.clock_weight)
        )
        self._refresh_action_buttons()

    def _refresh_action_buttons(self):
        """Re-apply inline button styles so font-family tokens stay current."""
        style = self.get_action_button_style()
        for btn in (
            self.btn_save_general, self.btn_save_fonts, self.btn_save_clock,
            self.btn_save_spotify, self.btn_connect_spotify, self.btn_save_ai,
            self.btn_save_shortcuts
        ):
            btn.setStyleSheet(style)

    def _apply_fonts(self):
        """Apply the active font family to the settings window and its children."""
        from PySide6.QtGui import QFont as _QFont
        font_name = theme.SELECTED_FONT

        base = _QFont(font_name, 10)
        base.setStyleStrategy(
            _QFont.StyleStrategy.PreferAntialias | _QFont.StyleStrategy.PreferQuality
        )
        self.setFont(base)

        for btn in self.font_buttons:
            btn.setFont(_QFont(btn.text(), 10, _QFont.Weight.Medium))

        self.update_settings_style()

    def on_hide_streaming_toggled(self, checked):
        config.save_hide_while_streaming(checked)
        from utils.window_capture import set_window_capture_exclusion
        set_window_capture_exclusion(int(self.winId()), checked)
        if self.parent_window and hasattr(self.parent_window, "apply_streaming_privacy"):
            self.parent_window.apply_streaming_privacy(checked)

    def showEvent(self, event):
        super().showEvent(event)
        from utils import config
        from utils.window_capture import set_window_capture_exclusion
        set_window_capture_exclusion(int(self.winId()), config.load_hide_while_streaming())
        self._start_mic_meter()

    def hideEvent(self, event):
        self._stop_mic_meter()
        super().hideEvent(event)

    def check_for_updates_now(self):
        """Asks the shared update service for a newer release and answers on this page."""
        from utils.update_checker import UpdateService
        service = UpdateService.get_instance()
        if getattr(self, "_update_service", None) is not service:
            service.checked.connect(self._on_update_checked)
            service.unavailable.connect(self._on_update_unavailable)
            service.download_changed.connect(self._on_download_changed)
            self._update_service = service

        pending = getattr(self, "_pending_update", None)
        if pending is not None:
            self.lbl_update_status.setText("Downloading the new setup…")
            self.btn_check_updates.setEnabled(False)
            service.download_and_install(pending)
            return

        self.lbl_update_status.setText("Checking GitHub…")
        self.btn_check_updates.setEnabled(False)
        service.check()

    def _on_update_checked(self, info):
        self.btn_check_updates.setEnabled(True)
        self._pending_update = info
        if info is None:
            self.btn_check_updates.setText("Check now")
            self.lbl_update_status.setText(f"You already have the newest build ({APP_VERSION}).")
            return
        self.btn_check_updates.setText("Update now")
        self.lbl_update_status.setText(
            f"Ticky {info.version} is available. The notch also offers to install it."
        )

    def _on_update_unavailable(self):
        self.btn_check_updates.setEnabled(True)
        self.lbl_update_status.setText("Couldn't reach GitHub. Try again later.")

    def _on_download_changed(self, status):
        if status == "ready":
            self._pending_update = None
            self.btn_check_updates.setText("Check now")
            self.lbl_update_status.setText("Setup is running - follow it to finish the update.")
        elif status == "failed":
            self.btn_check_updates.setEnabled(True)
            self.lbl_update_status.setText("Download failed. The release page is open instead.")

    def save_general_settings(self):
        aot = self.switch_aot.isChecked()
        tfh = self.switch_tfh.isChecked()
        dat = self.switch_dat.isChecked()
        sos = self.switch_sos.isChecked()
        hws = self.switch_hide_streaming.isChecked()
        cfu = self.switch_update_notify.isChecked()

        config.save_always_on_top(aot)
        config.save_use_24h(tfh)
        config.save_show_date(dat)
        config.save_start_on_startup(sos)
        config.save_hide_while_streaming(hws)
        config.save_check_for_updates(cfu)

        # Sync with Windows registry run key
        from utils.startup import set_startup
        set_startup(sos)
        
        theme.USE_24H = tfh
        theme.SHOW_DATE = dat

        from utils.window_capture import set_window_capture_exclusion
        set_window_capture_exclusion(int(self.winId()), hws)
        
        if self.parent_window:
            self.parent_window.set_always_on_top(aot)
            if hasattr(self.parent_window, "apply_streaming_privacy"):
                self.parent_window.apply_streaming_privacy(hws)
            self.parent_window.refresh_theme()

            
        self.btn_save_general.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_general.setText("Save Settings"))

    def save_font_settings(self):
        config.save_font_family(self.selected_font)
        
        # 1. Apply the new font family to global theme variables
        theme.update_font_theme(self.selected_font)
        
        # 2. Update the application-level QFont so all widgets inherit the new family
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QFont as _QFont
        app = QApplication.instance()
        if app:
            app_font = _QFont(self.selected_font)
            app_font.setStyleStrategy(_QFont.StyleStrategy.PreferAntialias | _QFont.StyleStrategy.PreferQuality)
            app.setFont(app_font)
        
        # 3. Refresh the current settings window styling and fonts
        self._apply_fonts()
        
        # 4. Refresh the parent main window with updated QSS
        if self.parent_window:
            self.parent_window.refresh_theme()
            
        self.btn_save_fonts.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_fonts.setText("Save Font"))

    def save_clock_settings(self):
        config.save_clock_weight(self.clock_weight)
        show_sec = self.switch_seconds.isChecked()
        config.save_show_seconds(show_sec)
        
        # Save style and background box toggle
        config.save_clock_style(self.current_clock_style)
        show_box = self.switch_clock_box.isChecked()
        config.save_clock_box_bg(show_box)
        
        theme.CLOCK_WEIGHT = self.clock_weight
        theme.SHOW_SECONDS = show_sec
        theme.CLOCK_STYLE = self.current_clock_style
        theme.CLOCK_BOX_BG = show_box
        
        if self.parent_window:
            if hasattr(self.parent_window, "clock_widget") and self.parent_window.clock_widget:
                self.parent_window.clock_widget.apply_style(self.current_clock_style, show_box)
            self.parent_window.refresh_theme()
            
        self.btn_save_clock.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_clock.setText("Save Clock Settings"))

    def _make_clock_style_card(self, parent, style_key, display_name, time_str, date_str, time_obj_name, active=False):
        card = ClockStyleCard(style_key, display_name, time_str, date_str, time_obj_name, active, parent)
        card.clicked.connect(self.on_clock_style_changed)
        return card

    def on_clock_style_changed(self, style_key):
        self.current_clock_style = style_key
        for key, card in self.clock_style_cards.items():
            card.setActive(key == style_key)

    def on_accent_color_changed(self, color_hex):
        config.save_accent_color(color_hex)
        theme.ACCENT_COLOR = color_hex

        for swatch in self.swatches:
            swatch.setSelected(swatch.color_hex.lower() == color_hex.lower())

        if hasattr(self, "hex_accent_input"):
            self.hex_accent_input.blockSignals(True)
            self.hex_accent_input.setText(color_hex.upper())
            self.hex_accent_input.blockSignals(False)
            self._update_custom_accent_preview(color_hex)

        # The theme mocks draw their clock line and task dots in the accent
        for card in getattr(self, "theme_cards", {}).values():
            card.preview.update()

        self.update_settings_style()
        if self.parent_window:
            self.parent_window.refresh_theme()

    def normalize_accent_hex(self, text):
        """Return '#RRGGBB' for a valid hex string, otherwise None."""
        value = (text or "").strip().lstrip("#")
        if len(value) == 3:
            value = "".join(ch * 2 for ch in value)
        if len(value) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
            return None
        return ("#" + value).upper()

    def _update_custom_accent_preview(self, text):
        hex_value = self.normalize_accent_hex(text)
        preview = QColor(hex_value) if hex_value else QColor(theme.TEXT_SECONDARY)
        self.btn_custom_accent.setStyleSheet(f"""
            QPushButton#AccentCustomSwatch {{
                background-color: {preview.name()};
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 13px;
            }}
            QPushButton#AccentCustomSwatch:hover {{
                border: 1px solid {theme.ACCENT_COLOR};
            }}
        """)

    def _set_hex_input_invalid(self, invalid):
        self.hex_accent_input.setProperty("invalid", "true" if invalid else "false")
        self.hex_accent_input.style().unpolish(self.hex_accent_input)
        self.hex_accent_input.style().polish(self.hex_accent_input)

    def pick_custom_accent(self):
        """Open the native colour picker and apply whatever the user chooses."""
        current = self.normalize_accent_hex(self.hex_accent_input.text()) or theme.ACCENT_COLOR
        chosen = QColorDialog.getColor(QColor(current), self, "Choose an accent colour")
        if chosen.isValid():
            self._set_hex_input_invalid(False)
            self.on_accent_color_changed(chosen.name().upper())

    def apply_hex_accent(self):
        hex_value = self.normalize_accent_hex(self.hex_accent_input.text())
        if not hex_value:
            self._set_hex_input_invalid(True)
            return
        self._set_hex_input_invalid(False)
        self.on_accent_color_changed(hex_value)

    def on_task_font_size_changed(self, value):
        config.save_task_font_size(value)
        theme.TASK_SIZE = value
        self.lbl_siz_val.setText(f"{value}px")
        if self.parent_window:
            self.parent_window.refresh_theme()

    def on_spot_mode_changed(self, index):
        mode = "gsmtc" if index == 0 else "api"
        config.save_spotify_backend_mode(mode)
        self.update_spotify_status_ui()
        if self.parent_window and hasattr(self.parent_window, 'spotify_panel'):
            self.parent_window.spotify_panel.update_playback()

    def save_spotify_creds(self):
        c_id = self.input_client_id.text().strip()
        c_secret = self.input_client_secret.text().strip()
        config.save_spotify_credentials(c_id, c_secret)
        mode = "gsmtc" if self.combo_spot_mode.currentIndex() == 0 else "api"
        config.save_spotify_backend_mode(mode)
        self.btn_save_spotify.setText("Saved!")
        self.update_spotify_status_ui()
        if self.parent_window and hasattr(self.parent_window, 'spotify_panel'):
            self.parent_window.spotify_panel.update_playback()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_spotify.setText("Save Mode / Credentials"))

    def on_mic_changed(self):
        config.save_mic_device_id(self.combo_mic.currentData() or "")
        if self.isVisible():
            self._start_mic_meter()

    # -- live mic level meter ------------------------------------------
    def _resolve_meter_device(self):
        wanted = self.combo_mic.currentData() or ""
        if wanted:
            for d in self._media_devices.audioInputs():
                if d.id() == wanted:
                    return d
        return self._media_devices.defaultAudioInput()

    def _start_mic_meter(self):
        self._stop_mic_meter()
        device = self._resolve_meter_device()
        if device is None or device.isNull():
            return
        try:
            from PySide6.QtMultimedia import QAudioSource, QAudioFormat
            from utils.dictation_service import DictationService
            fmt = DictationService._build_wave_format(device)
            if fmt.sampleFormat().value not in (
                QAudioFormat.SampleFormat.Int16.value,
                QAudioFormat.SampleFormat.Float.value,
            ):
                return
            self._meter_fmt = fmt
            self._meter_source = QAudioSource(device, fmt, self)
            self._meter_io = self._meter_source.start()
            if self._meter_io is None:
                self._meter_source.deleteLater()
                self._meter_source = None
                return
            self._meter_timer.start()
        except Exception:
            pass

    def _stop_mic_meter(self):
        self._meter_timer.stop()
        if self._meter_source is not None:
            try:
                self._meter_source.stop()
            except Exception:
                pass
            self._meter_source.deleteLater()
            self._meter_source = None
        self._meter_io = None
        self._meter_level = 0.0
        if hasattr(self, "mic_level_bar"):
            self.mic_level_bar.set_level(0.0)

    def _tick_mic_meter(self):
        io = self._meter_io
        fmt = self._meter_fmt
        if io is None or fmt is None:
            return
        data = bytes(io.readAll())
        if not data:
            return
        from PySide6.QtMultimedia import QAudioFormat
        from utils.dictation_service import DictationService
        if fmt.sampleFormat().value != QAudioFormat.SampleFormat.Int16.value:
            converted = DictationService._to_int16(data, fmt)
            if converted is None:
                return
            data = converted
        level = DictationService._level_from_pcm16(data)
        self._meter_level += (level - self._meter_level) * 0.45
        self.mic_level_bar.set_level(self._meter_level)

    def save_ai_key(self):
        provider = self.combo_provider.currentText()
        key = self.input_ai_key.text().strip()
        model = self.input_ai_model.text().strip()
        
        # Mismatch validation warnings
        warning_msg = None
        if key:
            if key.startswith("gsk_") and provider != "Groq":
                warning_msg = f"API key starts with 'gsk_' (Groq), but provider is '{provider}'."
            elif key.startswith("sk-or-v1-") and provider != "OpenRouter":
                warning_msg = f"API key starts with 'sk-or-v1-' (OpenRouter), but provider is '{provider}'."
            elif key.startswith("sk-ant-") and provider != "Claude":
                warning_msg = f"API key starts with 'sk-ant-' (Claude), but provider is '{provider}'."
            elif (key.startswith("sk-proj-") or (key.startswith("sk-") and not key.startswith("sk-or-v1-") and not key.startswith("sk-ant-"))) and provider != "OpenAI":
                warning_msg = f"API key starts with 'sk-' (OpenAI), but provider is '{provider}'."
            elif key.startswith("AIzaSy") and provider != "Gemini":
                warning_msg = f"API key starts with 'AIzaSy' (Gemini), but provider is '{provider}'."

        if warning_msg:
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.warning(
                self, 
                "Provider Mismatch Warning", 
                f"{warning_msg}\n\nAre you sure you want to save this configuration?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        config.save_ai_provider(provider)
        config.save_ai_api_key(key)
        config.save_ai_model(model)
        
        self.btn_save_ai.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_ai.setText("Save Config"))
        
        # Notify the parent window's AIPanel to update its welcome text
        if self.parent_window and hasattr(self.parent_window, "ai_panel") and self.parent_window.ai_panel:
            self.parent_window.ai_panel.update_welcome_text()

        # If opened from AI flow (e.g. AI toolbar button), close Settings and return to/show the AI chat panel
        if getattr(self, 'opened_from_ai', False):
            self.opened_from_ai = False
            self.close()
            if self.parent_window and hasattr(self.parent_window, 'ai_panel') and self.parent_window.ai_panel:
                if not self.parent_window.ai_panel.is_expanded:
                    self.parent_window.ai_panel.toggle()

    def save_shortcut_settings(self):
        t_sc = self.input_toggle_shortcut.text().strip()
        n_sc = self.input_new_task_shortcut.text().strip()
        d_sc = self.input_voice_dictation_shortcut.text().strip()
        s_sc = self.input_app_search_shortcut.text().strip()
        
        config.save_shortcuts({
            "toggle_window": t_sc if t_sc and t_sc != "None" else "",
            "new_task": n_sc if n_sc and n_sc != "None" else "",
            "voice_dictation": d_sc if d_sc and d_sc != "None" else "",
            "app_search": s_sc if s_sc and s_sc != "None" else "",
        })
        
        if self.parent_window and hasattr(self.parent_window, 'register_global_hotkeys'):
            self.parent_window.shortcuts = config.load_shortcuts()
            self.parent_window.register_global_hotkeys()
            
        self.btn_save_shortcuts.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_shortcuts.setText("Save Shortcuts"))

    def on_ai_provider_changed(self, provider_name):
        provider_instructions = {
            "Gemini": (
                "https://aistudio.google.com/",
                "Google AI Studio",
                "Get API Key",
                "Uses Gemini 1.5 Flash for rapid, intelligent answers."
            ),
            "OpenAI": (
                "https://platform.openai.com/api-keys",
                "OpenAI Platform",
                "Create new secret key",
                "Uses GPT-4o Mini for advanced reasoning and conversation."
            ),
            "Claude": (
                "https://console.anthropic.com/",
                "Anthropic Console",
                "Get API Keys",
                "Uses Claude 3.5 Sonnet for highly-detailed, smart responses."
            ),
            "Groq": (
                "https://console.groq.com/keys",
                "Groq Console",
                "Create API Key",
                "Available models:<br>"
                "<b>Reasoning:</b> qwen-qwq-32b, qwen3-32b<br>"
                "<b>Text-to-Text:</b> openai/gpt-oss-120b, llama-3.3-70b-versatile, llama-4-scout-17b-16e-instruct, meta-llama/llama-4-maverick-17b-128e-instruct"
            ),
            "OpenRouter": (
                "https://openrouter.ai/keys",
                "OpenRouter Keys",
                "Create Key",
                "Uses open-source models through OpenRouter's unified endpoint."
            )
        }
        
        inst = provider_instructions.get(provider_name, provider_instructions["Gemini"])
        link_url, site_name, action_name, description = inst
        
        self.lbl_ai_guide.setText(
            f"<b>Setup Instructions for {provider_name}:</b><br>"
            f"1. Visit <a href='{link_url}' style='color:#FF9F0A;'>{site_name}</a> and sign in.<br>"
            f"2. Click <b>{action_name}</b> and create a new key.<br>"
            f"3. Paste the API Key below.<br>"
            f"{description}"
        )
        
        # Load saved model or set default for this provider
        saved_provider = config.load_ai_provider()
        if provider_name == saved_provider:
            self.input_ai_model.setText(config.load_ai_model())
        else:
            defaults = {
                "Gemini": "gemini-1.5-flash",
                "OpenAI": "gpt-4o-mini",
                "Claude": "claude-3-5-sonnet-20241022",
                "Groq": "openai/gpt-oss-120b",
                "OpenRouter": "meta-llama/llama-3-8b-instruct:free"
            }
            self.input_ai_model.setText(defaults.get(provider_name, "gemini-1.5-flash"))

    def update_spotify_status_ui(self):
        c_id, c_secret = config.load_spotify_credentials()
        access, refresh = config.load_spotify_tokens()
        backend_mode = config.load_spotify_backend_mode("gsmtc")
        
        has_creds = bool(c_id.strip() and c_secret.strip())
        
        if backend_mode == "gsmtc":
            self.lbl_api_title.hide()
            self.creds_section.hide()
            self.btn_connect_spotify.hide()
            self.btn_save_spotify.setText("Save Mode")
            
            self.lbl_spot_status.setText("● Automatic Integration Active (Windows Media)")
            self.lbl_spot_status.setStyleSheet("color: #30D158; font-weight: bold;")
            self.lbl_spotify_guide.setText(
                    "<b>Automatic (Windows Media):</b><br>"
                    "Ticky uses native Windows Global System Media Transport Controls (GSMTC) to automatically detect and control <b>Spotify Desktop</b> and <b>Spotify Web Player</b>.<br>"
                    "No Client ID, Secret, or OAuth setup required."
                )
        else:
            self.lbl_api_title.show()
            self.creds_section.show()
            self.btn_connect_spotify.show()
            self.btn_connect_spotify.setEnabled(has_creds)
            self.btn_save_spotify.setText("Save Credentials")
            
            if access and refresh:
                self.lbl_spot_status.setText("Status: Linked & Connected via Web API")
                self.lbl_spot_status.setStyleSheet("color: #30D158; font-weight: bold;")
            elif c_id and c_secret:
                self.lbl_spot_status.setText("Status: Credentials Saved. Ready to Connect.")
                self.lbl_spot_status.setStyleSheet("color: #FF9F0A; font-weight: bold;")
            else:
                self.lbl_spot_status.setText("⚠️ Please link your Spotify Developer account below.")
                self.lbl_spot_status.setStyleSheet("color: #FF453A; font-weight: bold;")
            
            self.lbl_spotify_guide.setText(
                "<b>Developer API Setup Instructions:</b><br>"
                "1. Visit <a href='https://developer.spotify.com/dashboard' style='color:#FF9F0A;'>developer.spotify.com/dashboard</a> and log in.<br>"
                "2. Click <b>Create App</b>.<br>"
                "3. Add Redirect URI: <a href='copy' style='color:#FFD60A; text-decoration:underline;'>http://127.0.0.1:8888/callback</a> (Click to copy)<br>"
                "4. Paste the Client ID & Secret below."
            )


    def connect_spotify_account(self):
        c_id, c_secret = config.load_spotify_credentials()
        if not c_id or not c_secret:
            self.lbl_spot_status.setText("Error: Save Client ID & Secret first")
            self.lbl_spot_status.setStyleSheet("color: #FF453A;")
            return
            
        self.lbl_spot_status.setText("Status: Connecting... Check your browser")
        self.lbl_spot_status.setStyleSheet("color: #FF9F0A;")
        
        from utils.spotify import SpotifyOAuthServerThread
        self.oauth_thread = SpotifyOAuthServerThread(c_id, c_secret, self)
        self.oauth_thread.auth_completed.connect(self.on_spotify_auth_completed)
        self.oauth_thread.start()
        
        import webbrowser
        auth_url = self.oauth_thread.get_auth_url()
        webbrowser.open(auth_url)
        
    def on_spotify_auth_completed(self, success, message):
        if success:
            self.lbl_spot_status.setText("Status: Linked & Connected")
            self.lbl_spot_status.setStyleSheet("color: #30D158; font-weight: bold;")
            if self.parent_window:
                self.parent_window.refresh_theme()
        else:
            self.lbl_spot_status.setText(f"Error: {message}")
            self.lbl_spot_status.setStyleSheet("color: #FF453A;")

    def exit_application(self):
        from PySide6.QtWidgets import QApplication
        # Fully terminate Ticky (tray keeps the app alive otherwise)
        if self.parent_window and hasattr(self.parent_window, 'unregister_global_hotkeys'):
            try:
                self.parent_window.unregister_global_hotkeys()
            except Exception:
                pass
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()
        
    def show_centered(self):
        from PySide6.QtWidgets import QApplication
        self.selected_font = config.load_font_family("DM Sans")
        theme.update_font_theme(self.selected_font)
        for btn in self.font_buttons:
            is_active = btn.text().lower() == self.selected_font.lower()
            btn.setProperty("active", "true" if is_active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._apply_fonts()
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.geometry()
            x = screen_geom.x() + (screen_geom.width() - self.width()) // 2
            y = screen_geom.y() + (screen_geom.height() - self.height()) // 2
            self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        
        # Fade-in window animation
        self.setWindowOpacity(0.0)
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(220)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade_anim.start()

    def on_theme_changed(self, theme_name):
        """Apply selected UI color theme globally and refresh all panels."""
        theme.apply_theme(theme_name)

        # Update active state on all theme cards
        for name, card in self.theme_cards.items():
            card.setActive(name == theme_name)

        # Refresh settings window styling itself
        self.update_settings_style()

        # Refresh the main widget, notch widget, and all panels
        if self.parent_window:
            self.parent_window.refresh_theme()
            if hasattr(self.parent_window, "notch_widget") and self.parent_window.notch_widget:
                self.parent_window.notch_widget.apply_notch_style()
        else:
            from PySide6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if hasattr(widget, "refresh_theme"):
                    widget.refresh_theme()
                if hasattr(widget, "apply_notch_style"):
                    widget.apply_notch_style()

    def closeEvent(self, event):
        self.opened_from_ai = False
        self._stop_mic_meter()
        if self.parent_window and hasattr(self.parent_window, 'register_global_hotkeys'):
            self.parent_window.register_global_hotkeys()
        if self.parent_window and hasattr(self.parent_window, 'toolbar'):
            self.parent_window.toolbar.btn_settings.setActive(False)
        super().closeEvent(event)
