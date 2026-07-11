from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal, QPoint, QEvent
from PySide6.QtWidgets import (QWidget, QAbstractButton, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QGraphicsDropShadowEffect, 
                               QStackedWidget, QSlider, QLineEdit, QFrame, QScrollArea,
                               QGraphicsOpacityEffect)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from styles import theme, qss
from utils import config

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


class ClockStyleCard(QFrame):
    clicked = Signal(str)

    def __init__(self, style_key, display_name, time_str, date_str, time_obj_name, active=False, parent=None):
        super().__init__(parent)
        self.style_key = style_key
        self.setObjectName("ClockStyleCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(88, 76)
        self.setProperty("active", "true" if active else "false")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(1)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_name = QLabel(display_name, self)
        self.lbl_name.setObjectName("CardStyleName")
        self.lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_name)

        self.lbl_time = None
        self.lbl_hours = None
        self.lbl_mins = None

        if style_key == "split":
            split_col = QVBoxLayout()
            split_col.setSpacing(-3)
            split_col.setAlignment(Qt.AlignmentFlag.AlignCenter)
            parts = time_str.split("\n")
            self.lbl_hours = QLabel(parts[0], self)
            self.lbl_hours.setObjectName("CardPreviewTimeSplit")
            self.lbl_hours.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.lbl_mins = QLabel(parts[1] if len(parts) > 1 else "00", self)
            self.lbl_mins.setObjectName("CardPreviewTimeSplit")
            self.lbl_mins.setAlignment(Qt.AlignmentFlag.AlignCenter)
            split_col.addWidget(self.lbl_hours)
            split_col.addWidget(self.lbl_mins)
            layout.addLayout(split_col)
        else:
            self.lbl_time = QLabel(time_str, self)
            self.lbl_time.setObjectName(time_obj_name)
            self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.lbl_time)

        self.lbl_date = QLabel(date_str, self)
        self.lbl_date.setObjectName("CardPreviewDate")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not date_str:
            self.lbl_date.hide()
        layout.addWidget(self.lbl_date)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.style_key)
            event.accept()
        else:
            super().mousePressEvent(event)

    def setActive(self, active):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        for lbl in (self.lbl_name, self.lbl_time, self.lbl_date, self.lbl_hours, self.lbl_mins):
            if lbl:
                lbl.style().unpolish(lbl)
                lbl.style().polish(lbl)
        self.update()


class SettingsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(None) # Standalone window
        self.setWindowTitle("Ticky - Settings")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        # Set window icon
        from utils.icon import create_ticky_icon
        self.setWindowIcon(create_ticky_icon())
        
        self.parent_window = parent
        self.selected_font = config.load_font_family("Inter")
        self.clock_weight = config.load_clock_weight("700")
        
        # Movable drag state variables
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()
        self.is_dragging = False
        
        self.init_ui()

    def init_ui(self):
        # Increased window size to landscape orientation for sidebar dashboard layout
        self.setFixedSize(520, 450)
        
        # Main Outer Container Frame
        self.container = QFrame(self)
        self.container.setObjectName("SettingsWindowContainer")
        self.container.setFixedSize(520, 450)
        
        main_layout = QHBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Left Sidebar layout panel
        self.sidebar = QFrame(self.container)
        self.sidebar.setObjectName("SettingsSidebar")
        self.sidebar.setFixedWidth(135)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(6)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # Sidebar Categories Title - changed to Ticky Settings
        sidebar_title = QLabel("Ticky Settings", self.sidebar)
        sidebar_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(sidebar_title)
        
        self.sidebar_buttons = []
        sidebar_items = [
            ("General", 0),
            ("Fonts", 1),
            ("Clock", 2),
            ("Tasks", 3),
            ("Spotify", 4),
            ("AI Chat", 5)
        ]
        
        for name, idx in sidebar_items:
            btn = QPushButton(name, self.sidebar)
            btn.setObjectName("SidebarButton")
            btn.setProperty("active", "false")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=idx: self.switch_page(i))
            sidebar_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
            
        sidebar_layout.addStretch()
        main_layout.addWidget(self.sidebar)
        
        # 2. Right settings content page panel
        content_widget = QWidget(self.container)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(18, 16, 18, 16)
        content_layout.setSpacing(10)
        
        # Header title bar inside content panel
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_page_title = QLabel("General Settings", content_widget)
        self.lbl_page_title.setObjectName("SettingsTitle")
        
        close_btn = QPushButton("×", content_widget)
        close_btn.setObjectName("SettingsCloseButton")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.close)
        
        title_layout.addWidget(self.lbl_page_title)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        content_layout.addLayout(title_layout)
        
        # Separator line
        sep = QWidget(content_widget)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {theme.BORDER_COLOR};")
        content_layout.addWidget(sep)
        
        # Stacked Widget for pages
        self.stacked_widget = QStackedWidget(content_widget)
        self.stacked_widget.setFixedHeight(310)
        
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
        
        _add_divider(window_inner)
        
        self.switch_pin = ToggleSwitch(window_section)
        self.switch_pin.setChecked(config.load_pin_position())
        _add_gen_row(window_inner, "Pin Position", "Lock window position and disable dragging", self.switch_pin)
        
        _add_divider(window_inner)
        
        self.switch_sod = ToggleSwitch(window_section)
        self.switch_sod.setChecked(config.load_stick_on_desktop())
        _add_gen_row(window_inner, "Stick on Desktop", "Pin Ticky to the background behind windows", self.switch_sod)
        
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
        
        # Idle minimize card
        idle_section = QFrame(gen_content)
        idle_section.setObjectName("SettingSection")
        idle_inner = QVBoxLayout(idle_section)
        idle_inner.setContentsMargins(12, 10, 12, 10)
        idle_inner.setSpacing(0)
        
        idle_row = QHBoxLayout()
        idle_row.setContentsMargins(0, 8, 0, 8)
        idle_text_col = QVBoxLayout()
        idle_text_col.setSpacing(1)
        self.lbl_moi = QLabel("Minimize on Inactivity", idle_section)
        self.lbl_moi.setObjectName("SettingLabel")
        self.lbl_moi_desc = QLabel("Auto-minimize to a floating ball after minutes", idle_section)
        self.lbl_moi_desc.setObjectName("SettingDescription")
        idle_text_col.addWidget(self.lbl_moi)
        idle_text_col.addWidget(self.lbl_moi_desc)
        idle_row.addLayout(idle_text_col, 1)
        
        from PySide6.QtWidgets import QSpinBox
        self.spin_idle_minutes = QSpinBox(idle_section)
        self.spin_idle_minutes.setRange(1, 60)
        self.spin_idle_minutes.setSuffix(" min")
        self.spin_idle_minutes.setValue(config.load_idle_minutes())
        self.spin_idle_minutes.setFixedWidth(70)
        self.spin_idle_minutes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.spin_idle_minutes.setObjectName("SettingSpinBox")
        self.spin_idle_minutes.setStyleSheet(f"""
            QSpinBox#SettingSpinBox {{
                background-color: {theme.MAIN_CARD_COLOR};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                padding: 3px 6px;
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
            }}
            QSpinBox#SettingSpinBox::up-button, QSpinBox#SettingSpinBox::down-button {{
                width: 0px;
            }}
            QSpinBox#SettingSpinBox:disabled {{
                background-color: transparent;
                color: rgba(255, 255, 255, 0.15);
                border: 1px solid rgba(255, 255, 255, 0.05);
            }}
        """)
        
        self.switch_minimize_idle = ToggleSwitch(idle_section)
        self.switch_minimize_idle.setChecked(config.load_minimize_on_idle())
        
        aot_on = self.switch_aot.isChecked()
        self.switch_minimize_idle.setEnabled(aot_on)
        self.spin_idle_minutes.setEnabled(aot_on)
        self.lbl_moi.setEnabled(aot_on)
        self.lbl_moi_desc.setEnabled(aot_on)
        if not aot_on:
            self.switch_minimize_idle.setChecked(False)
            
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        controls_layout.addWidget(self.spin_idle_minutes)
        controls_layout.addWidget(self.switch_minimize_idle)
        idle_row.addLayout(controls_layout, 0)
        idle_inner.addLayout(idle_row)
        
        self.switch_aot.toggled_state.connect(self.on_aot_toggled)
        self.switch_sod.toggled_state.connect(self.on_sod_toggled)
        
        lbl_sys_title = QLabel("System & Behavior", gen_content)
        lbl_sys_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_sys_title)
        gen_content_layout.addWidget(window_section)
        
        lbl_disp_title = QLabel("Display Options", gen_content)
        lbl_disp_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_disp_title)
        gen_content_layout.addWidget(display_section)
        
        lbl_inact_title = QLabel("Inactivity Control", gen_content)
        lbl_inact_title.setObjectName("SettingSectionTitle")
        gen_content_layout.addWidget(lbl_inact_title)
        gen_content_layout.addWidget(idle_section)
        gen_content_layout.addStretch()
        
        gen_scroll.setWidget(gen_content)
        page_general_layout.addWidget(gen_scroll)
        
        self.btn_save_general = QPushButton("Save Settings", page_general)
        self.btn_save_general.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_general.setStyleSheet(self.get_action_button_style())
        self.btn_save_general.clicked.connect(self.save_general_settings)
        page_general_layout.addWidget(self.btn_save_general)
        
        self.stacked_widget.addWidget(page_general)
        
        # --- Page 2: Fonts Selection ---
        page_fonts = QWidget()
        page_fonts_layout = QVBoxLayout(page_fonts)
        page_fonts_layout.setContentsMargins(0, 0, 0, 0)
        page_fonts_layout.setSpacing(10)
        
        lbl_fonts_desc = QLabel("Select active application typeface family:", page_fonts)
        lbl_fonts_desc.setObjectName("SettingDescription")
        page_fonts_layout.addWidget(lbl_fonts_desc)
        
        scroll_area = QScrollArea(page_fonts)
        scroll_area.setObjectName("FontsScrollArea")
        scroll_area.setWidgetResizable(True)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_content_layout = QVBoxLayout(scroll_content)
        scroll_content_layout.setContentsMargins(0, 0, 4, 0)
        scroll_content_layout.setSpacing(6)
        
        fonts_list = [
            "Inter", "Manrope", "Nunito", "DM Sans", "General Sans",
            "Satoshi", "Plus Jakarta Sans", "Outfit", "IBM Plex Sans", "Space Grotesk"
        ]
        
        self.font_buttons = []
        for font_name in fonts_list:
            btn_font = QPushButton(font_name, scroll_content)
            btn_font.setObjectName("FontItemButton")
            btn_font.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_font.setFont(QFont(font_name, 10, QFont.Weight.Medium))
            is_active = (font_name.lower() == self.selected_font.lower())
            btn_font.setProperty("active", "true" if is_active else "false")
            btn_font.clicked.connect(lambda checked=False, f=font_name: self.on_font_selected(f))
            scroll_content_layout.addWidget(btn_font)
            self.font_buttons.append(btn_font)
            
        scroll_area.setWidget(scroll_content)
        page_fonts_layout.addWidget(scroll_area)
        
        self.btn_save_fonts = QPushButton("Save Font", page_fonts)
        self.btn_save_fonts.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_fonts.setStyleSheet(self.get_action_button_style())
        self.btn_save_fonts.clicked.connect(self.save_font_settings)
        page_fonts_layout.addWidget(self.btn_save_fonts)
        
        self.stacked_widget.addWidget(page_fonts)
        
        # --- Page 3: Clock Style ---
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
        cards_scroll.setFixedHeight(88)
        cards_scroll.setWidgetResizable(True)

        cards_row = QWidget()
        cards_row.setObjectName("CardsRow")
        cards_row.setMinimumWidth(468)
        cards_row_layout = QHBoxLayout(cards_row)
        cards_row_layout.setContentsMargins(2, 2, 2, 2)
        cards_row_layout.setSpacing(6)
        cards_row_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.clock_style_cards = {}
        self.current_clock_style = config.load_clock_style("neon")

        clock_style_defs = [
            ("classic", "Classic",  "08:13",   "THU, JUL 10",  "CardPreviewTime"),
            ("split",   "Split",    "08\n13",   "THU / JUL 10", "CardPreviewTime"),
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
        lbl_col_desc = QLabel("Select the main accent theme color", accent_section)
        lbl_col_desc.setObjectName("SettingDescription")
        accent_inner.addWidget(lbl_col)
        accent_inner.addWidget(lbl_col_desc)
        
        swatches_layout = QHBoxLayout()
        swatches_layout.setSpacing(10)
        swatches_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.swatches = []
        colors = ["#4CC2FF", "#FF453A", "#FF9F0A", "#30D158", "#BF5AF2", "#FFD60A"]
        current_accent = config.load_accent_color()
        for hex_color in colors:
            is_active = (hex_color.lower() == current_accent.lower())
            swatch = ColorSwatch(hex_color, is_active, accent_section)
            swatch.color_selected.connect(self.on_accent_color_changed)
            swatches_layout.addWidget(swatch)
            self.swatches.append(swatch)
            
        accent_inner.addLayout(swatches_layout)
        
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
        
        lbl_text_title = QLabel("Text Configuration", tasks_content)
        lbl_text_title.setObjectName("SettingSectionTitle")
        tasks_content_layout.addWidget(lbl_text_title)
        tasks_content_layout.addWidget(size_section)
        
        lbl_dynamic_save_notice = QLabel("💡 Colors and font sizes are saved dynamically.", tasks_content)
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
        
        self.lbl_spot_status = QLabel("⚠️ Please link your Spotify account below.", status_section)
        self.lbl_spot_status.setObjectName("SettingDescription")
        status_inner.addWidget(self.lbl_spot_status)
        
        demo_row = QHBoxLayout()
        demo_row.setContentsMargins(0, 4, 0, 4)
        demo_text_col = QVBoxLayout()
        demo_text_col.setSpacing(2)
        lbl_demo = QLabel("Spotify Demo Mode", status_section)
        lbl_demo.setObjectName("SettingLabel")
        lbl_demo_desc = QLabel("Simulate playback without Spotify credentials", status_section)
        lbl_demo_desc.setObjectName("SettingDescription")
        demo_text_col.addWidget(lbl_demo)
        demo_text_col.addWidget(lbl_demo_desc)
        
        self.switch_demo = ToggleSwitch(status_section)
        self.switch_demo.setChecked(config.load_spotify_demo_mode())
        self.switch_demo.toggled_state.connect(self.on_demo_mode_toggled)
        
        demo_row.addLayout(demo_text_col, 1)
        demo_row.addWidget(self.switch_demo, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        status_inner.addLayout(demo_row)
        
        self.lbl_spotify_guide = QLabel(
            "<b>Setup Instructions:</b><br>"
            "1. Visit <a href='https://developer.spotify.com/dashboard' style='color:#FF9F0A;'>developer.spotify.com/dashboard</a> and log in.<br>"
            "2. Click <b>Create App</b>.<br>"
            "3. Add Redirect URI: <code style='color:#FFD60A;'>http://127.0.0.1:8888/callback</code><br>"
            "4. Paste the Client ID & Secret below.<br>"
            "<span style='color:#FF453A; font-weight:bold;'>⚠️ Spotify Policy Note:</span> Playback controls (play, pause, skip) require a <b>Spotify Premium</b> account. Free accounts can only fetch currently playing details.", 
            status_section
        )
        self.lbl_spotify_guide.setObjectName("SettingDescription")
        self.lbl_spotify_guide.setOpenExternalLinks(True)
        self.lbl_spotify_guide.setWordWrap(True)
        self.lbl_spotify_guide.setStyleSheet(f"""
            QLabel#SettingDescription {{
                line-height: 1.3;
                color: {theme.TEXT_SECONDARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 9px;
            }}
        """)
        status_inner.addWidget(self.lbl_spotify_guide)
        
        creds_section = QFrame(spot_content)
        creds_section.setObjectName("SettingSection")
        creds_inner = QVBoxLayout(creds_section)
        creds_inner.setContentsMargins(12, 10, 12, 10)
        creds_inner.setSpacing(8)
        
        lbl_creds_title = QLabel("API Credentials Configuration", creds_section)
        lbl_creds_title.setObjectName("SettingLabel")
        creds_inner.addWidget(lbl_creds_title)
        
        self.input_client_id = QLineEdit(creds_section)
        self.input_client_id.setObjectName("SpotifyInput")
        self.input_client_id.setPlaceholderText("Spotify Client ID")
        
        self.input_client_secret = QLineEdit(creds_section)
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
        
        lbl_api_title = QLabel("Developer API Configuration", spot_content)
        lbl_api_title.setObjectName("SettingSectionTitle")
        spot_content_layout.addWidget(lbl_api_title)
        spot_content_layout.addWidget(creds_section)
        spot_content_layout.addStretch()
        
        spot_scroll.setWidget(spot_content)
        page_spotify_layout.addWidget(spot_scroll)
        
        spot_btn_layout = QHBoxLayout()
        spot_btn_layout.setSpacing(10)
        spot_btn_layout.setContentsMargins(0, 4, 0, 0)
        
        self.btn_save_spotify = QPushButton("Save Credentials", page_spotify)
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
        
        self.lbl_ai_guide = QLabel(
            "<b>Setup Instructions:</b><br>"
            "1. Visit <a href='https://aistudio.google.com/' style='color:#FF9F0A;'>Google AI Studio</a> and sign in.<br>"
            "2. Click <b>Get API Key</b> and create a new API Key.<br>"
            "3. Paste the API Key below to enable the chat panel.<br>"
            "This integration uses Gemini 1.5 Flash for rapid, intelligent answers.",
            ai_guide_section
        )
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
        
        lbl_ai_creds_title = QLabel("Gemini API Key", ai_creds_section)
        lbl_ai_creds_title.setObjectName("SettingLabel")
        lbl_ai_creds_title.setStyleSheet("font-weight: bold; font-size: 11px;")
        ai_creds_inner.addWidget(lbl_ai_creds_title)
        
        self.input_gemini_key = QLineEdit(ai_creds_section)
        self.input_gemini_key.setObjectName("SpotifyInput") # Reuse styling
        self.input_gemini_key.setPlaceholderText("Paste your Gemini API Key here")
        self.input_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_gemini_key.setText(config.load_gemini_api_key())
        ai_creds_inner.addWidget(self.input_gemini_key)
        
        ai_content_layout.addWidget(ai_guide_section)
        ai_content_layout.addWidget(ai_creds_section)
        ai_content_layout.addStretch()
        
        ai_scroll.setWidget(ai_content)
        page_ai_layout.addWidget(ai_scroll)
        
        ai_btn_layout = QHBoxLayout()
        ai_btn_layout.setSpacing(10)
        ai_btn_layout.setContentsMargins(0, 4, 0, 0)
        
        self.btn_save_ai = QPushButton("Save API Key", page_ai)
        self.btn_save_ai.setStyleSheet(self.get_action_button_style())
        self.btn_save_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save_ai.clicked.connect(self.save_ai_key)
        
        ai_btn_layout.addWidget(self.btn_save_ai)
        page_ai_layout.addLayout(ai_btn_layout)
        
        self.stacked_widget.addWidget(page_ai)
        
        content_layout.addWidget(self.stacked_widget)
        
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
        
        # Update page header title
        titles = ["General Settings", "Typography Font Selection", "Clock Style Customization", "Task Preferences", "Spotify Integration", "AI Integration"]
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
        self.setStyleSheet(qss.get_settings_style() + preview_style)

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
            + qss.get_clock_preview_card_style(self.clock_weight)
        )
        self._refresh_action_buttons()

    def _refresh_action_buttons(self):
        """Re-apply inline button styles so font-family tokens stay current."""
        style = self.get_action_button_style()
        for btn in (
            self.btn_save_general, self.btn_save_fonts, self.btn_save_clock,
            self.btn_save_spotify, self.btn_connect_spotify, self.btn_save_ai
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

    def on_aot_toggled(self, checked):
        if checked:
            self.switch_sod.setChecked(False)
            self.switch_minimize_idle.setEnabled(True)
            self.spin_idle_minutes.setEnabled(True)
            self.lbl_moi.setEnabled(True)
            self.lbl_moi_desc.setEnabled(True)
        else:
            self.switch_minimize_idle.setChecked(False)
            self.switch_minimize_idle.setEnabled(False)
            self.spin_idle_minutes.setEnabled(False)
            self.lbl_moi.setEnabled(False)
            self.lbl_moi_desc.setEnabled(False)

    def on_sod_toggled(self, checked):
        if checked:
            self.switch_aot.setChecked(False)
            self.on_aot_toggled(False)

    def save_general_settings(self):
        aot = self.switch_aot.isChecked()
        tfh = self.switch_tfh.isChecked()
        dat = self.switch_dat.isChecked()
        pin = self.switch_pin.isChecked()
        sod = self.switch_sod.isChecked()
        moi = self.switch_minimize_idle.isChecked()
        moi_min = self.spin_idle_minutes.value()
        sos = self.switch_sos.isChecked()
        
        config.save_always_on_top(aot)
        config.save_use_24h(tfh)
        config.save_show_date(dat)
        config.save_pin_position(pin)
        config.save_stick_on_desktop(sod)
        config.save_minimize_on_idle(moi)
        config.save_idle_minutes(moi_min)
        config.save_start_on_startup(sos)
        
        # Sync with Windows registry run key
        from utils.startup import set_startup
        set_startup(sos)
        
        theme.USE_24H = tfh
        theme.SHOW_DATE = dat
        theme.PIN_POSITION = pin
        theme.STICK_ON_DESKTOP = sod
        
        if self.parent_window:
            if hasattr(self.parent_window, "set_stick_on_desktop"):
                self.parent_window.set_stick_on_desktop(sod)
            self.parent_window.set_always_on_top(aot)
            if hasattr(self.parent_window, "update_inactivity_timer_settings"):
                self.parent_window.update_inactivity_timer_settings()
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
            
        self.update_settings_style()
        if self.parent_window:
            self.parent_window.refresh_theme()

    def on_task_font_size_changed(self, value):
        config.save_task_font_size(value)
        theme.TASK_SIZE = value
        self.lbl_siz_val.setText(f"{value}px")
        if self.parent_window:
            self.parent_window.refresh_theme()

    def save_spotify_creds(self):
        c_id = self.input_client_id.text().strip()
        c_secret = self.input_client_secret.text().strip()
        config.save_spotify_credentials(c_id, c_secret)
        self.btn_save_spotify.setText("Saved!")
        self.update_spotify_status_ui()
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_spotify.setText("Save Credentials"))

    def save_ai_key(self):
        key = self.input_gemini_key.text().strip()
        config.save_gemini_api_key(key)
        self.btn_save_ai.setText("Saved!")
        from PySide6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self.btn_save_ai.setText("Save API Key"))

    def on_demo_mode_toggled(self, checked):
        config.save_spotify_demo_mode(checked)
        self.update_spotify_status_ui()
        if self.parent_window and hasattr(self.parent_window, 'spotify_panel'):
            self.parent_window.spotify_panel.update_playback()

    def update_spotify_status_ui(self):
        c_id, c_secret = config.load_spotify_credentials()
        access, refresh = config.load_spotify_tokens()
        demo = config.load_spotify_demo_mode()
        
        has_creds = bool(c_id.strip() and c_secret.strip())
        self.btn_connect_spotify.setEnabled(has_creds)
        
        if demo:
            self.lbl_spot_status.setText("Status: Running in Demo / Simulation Mode")
            self.lbl_spot_status.setStyleSheet("color: #FF9F0A; font-weight: bold;")
        elif access and refresh:
            self.lbl_spot_status.setText("Status: Linked & Connected")
            self.lbl_spot_status.setStyleSheet("color: #30D158; font-weight: bold;")
        elif c_id and c_secret:
            self.lbl_spot_status.setText("Status: Credentials Saved. Ready to Connect.")
            self.lbl_spot_status.setStyleSheet("color: #FF9F0A; font-weight: bold;")
        else:
            self.lbl_spot_status.setText("⚠️ Please link your Spotify account below.")
            self.lbl_spot_status.setStyleSheet("color: #FF453A; font-weight: bold;")

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
        if self.parent_window:
            self.parent_window.close()
        self.close()
        
    def show_centered(self):
        from PySide6.QtWidgets import QApplication
        self.selected_font = config.load_font_family("Inter")
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

    def closeEvent(self, event):
        if self.parent_window and hasattr(self.parent_window, 'toolbar'):
            self.parent_window.toolbar.btn_settings.setActive(False)
        super().closeEvent(event)
