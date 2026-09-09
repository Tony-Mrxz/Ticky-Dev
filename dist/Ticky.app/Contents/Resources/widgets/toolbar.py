from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal, QRectF, QByteArray, QTimer
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel, QLineEdit
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtSvg import QSvgRenderer
from styles import theme, qss

# Raw SVG Templates with COLOR_PLACEHOLDER for dynamic dye colors
TIMER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M5 2H4v2h1v1c0 2.46 1.32 4.77 3.43 6.02.35.21.57.55.57.9v.16c0 .35-.21.69-.57.9A7.01 7.01 0 0 0 5 19v1H4v2h16v-2h-1v-1c0-2.46-1.32-4.77-3.43-6.02-.36-.21-.57-.55-.57-.9v-.16c0-.35.21-.69.57-.9A7.01 7.01 0 0 0 19 5V4h1V2zm12 3c0 1.76-.94 3.41-2.45 4.3-.97.57-1.55 1.55-1.55 2.62v.16c0 1.07.58 2.05 1.55 2.62 1.51.89 2.45 2.54 2.45 4.3v1H7v-1c0-1.76.94-3.41 2.45-4.3.97-.57 1.55-1.55 1.55-2.62v-.16c0-1.07-.58-2.05-1.55-2.62A5.01 5.01 0 0 1 7 5V4h10z"></path></svg>"""

POMODORO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M19.07 4.93a9.9 9.9 0 0 0-3.18-2.14A9.95 9.95 0 0 0 12 2c-.55 0-1 .45-1 1v5h2V4.06c.73.09 1.44.28 2.11.57.95.4 1.81.98 2.54 1.72.74.73 1.31 1.59 1.71 2.54.42.99.63 2.03.63 3.11s-.21 2.13-.63 3.11c-.4.95-.98 1.81-1.72 2.54-.73.74-1.59 1.31-2.54 1.71-1.97.83-4.26.83-6.23 0-.95-.4-1.81-.98-2.54-1.72a7.8 7.8 0 0 1-1.71-2.54c-.42-.99-.63-2.03-.63-3.11s.21-2.13.63-3.11c.4-.95.98-1.81 1.72-2.54L4.93 4.92c-.92.92-1.64 1.99-2.14 3.18C2.27 9.33 2 10.64 2 11.99s.26 2.66.79 3.89c.5 1.19 1.23 2.26 2.14 3.18s1.99 1.64 3.18 2.14c1.23.52 2.54.79 3.89.79s2.66-.26 3.89-.79c1.19-.5 2.26-1.23 3.18-2.14s1.64-1.99 2.14-3.18c.52-1.23.79-2.54.79-3.89s-.26-2.66-.79-3.89c-.5-1.19-1.23-2.26-2.14-3.18Z"></path><path d="M12.88 11.12 8 8l3.12 4.88c1.22 1.68 3.45-.55 1.77-1.77Z"></path></svg>"""

SPOTIFY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12.01 2.019c-5.495 0-9.991 4.496-9.991 9.991S6.515 22 12.01 22 22 17.504 22 12.01c0-5.495-4.446-9.991-9.99-9.991m4.595 14.436c-.199.299-.549.4-.85.201-2.349-1.45-5.296-1.75-8.793-.951-.348.102-.648-.148-.748-.449-.101-.35.149-.648.45-.749 3.795-.85 7.093-.499 9.69 1.1.35.149.4.548.251.848m1.2-2.747c-.251.349-.7.499-1.051.249-2.697-1.646-6.792-2.148-9.939-1.148-.398.101-.85-.1-.949-.498-.101-.402.1-.852.499-.952 3.646-1.098 8.143-.548 11.239 1.351.3.149.45.648.201.998m.099-2.799c-3.197-1.897-8.542-2.097-11.59-1.146a.94.94 0 0 1-1.148-.6.937.937 0 0 1 .599-1.151c3.547-1.049 9.392-.85 13.089 1.351.449.249.599.849.349 1.298-.25.35-.849.498-1.299.248"></path></svg>"""

SETTINGS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M22 12.5v-1h-1.03c-.04-.78-.18-1.54-.41-2.26l.95-.37-.36-.93-.95.37c-.38-.85-.89-1.62-1.5-2.3l.73-.73-.71-.71-.73.73c-.57-.51-1.2-.95-1.89-1.3l.42-.93-.91-.41-.42.94a8.9 8.9 0 0 0-2.69-.57V2h-1v1.03c-.78.04-1.54.18-2.26.41l-.37-.95-.93.36.37.95c-.85.38-1.62.89-2.3 1.5l-.73-.73-.71.71.73.73c-.51.57-.95 1.2-1.3 1.89l-.93-.42-.41.91.94.42a8.9 8.9 0 0 0-.57 2.69H2v1h1.03c.04.78.18 1.54.41 2.26l-.95.37.36.93.95-.37c.38.85.89 1.62 1.5 2.3l-.73.73.71.71.73-.73c.57.51-1.2.95 1.89 1.3l-.42.93.91.41.42-.94a8.9 8.9 0 0 0 2.69.57V22h1v-1.03c.78-.04 1.54-.18 2.26-.41l.37.95.93-.36-.37-.95c.85-.38 1.62-.89 2.3-1.5l.73.73.71-.71-.73-.73c.51-.57.95-1.2 1.3-1.89l.93.42.41-.91-.94-.42a8.9 8.9 0 0 0 .57-2.69zM12 5c3.1 0 5.72 2.02 6.65 4.81l-4.05.71c-.52-.91-1.48-1.53-2.6-1.53-.37 0-.72.08-1.05.2L8.31 6.05a6.9 6.9 0 0 1 3.68-1.06Zm1 7c0 .55-.45 1-1 1s-1-.45-1-1 .45-1 1-1 1 .45 1 1m-4.31 6.17a6.99 6.99 0 0 1-1.9-10.83l2.64 3.14c-.26.45-.42.96-.42 1.51 0 .93.43 1.75 1.1 2.3L8.7 18.15ZM12 19c-.49 0-.97-.05-1.43-.15l1.4-3.85H12a2.99 2.99 0 0 0 2.95-2.5l4.04-.71c0 .07.01.14.01.22 0 3.86-3.14 7-7 7Z"></path></svg>"""

AI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M20 10c-.74 0-1.38.4-1.72 1H13V9h4c.55 0 1-.45 1-1V5.72c.6-.35 1-.98 1-1.72 0-1.1-.9-2-2-2s-2 .9-2 2c0 .74.4 1.38 1 1.72V7h-3V5c0-1.65-1.35-3-3-3-1.3 0-2.41.83-2.83 2.01A3.51 3.51 0 0 0 4 7.5c0 .33.05.65.14.96C2.87 9.14 2 10.49 2 12c0 1.08.43 2.09 1.17 2.83-.11.38-.17.77-.17 1.17 0 1.96 1.41 3.59 3.31 3.93C6.86 21.16 8.11 22 9.5 22c1.93 0 3.5-1.57 3.5-3.5V17h3v1.28c-.6.35-1 .98-1 1.72 0 1.1.9 2 2 2s2-.9 2-2c0-.74-.4-1.38-1-1.72V16c0-.55-.45-1-1-1h-4v-2h5.28c.35.6.98 1 1.72 1 1.1 0 2-.9 2-2s-.9-2-2-2m-9 8.5c0 .83-.67 1.5-1.5 1.5-.71 0-1.33-.5-1.47-1.2l-.21-.8H7c-1.1 0-2-.9-2-2 0-.35.08-.68.25-.98l.46-.82-.78-.51C4.35 13.31 4 12.68 4 12c0-.98.72-1.82 1.68-1.97l1.69-.26-1.06-1.35c-.2-.26-.32-.59-.32-.92 0-.83.67-1.5 1.5-1.5.11 0 .21.01.31.03l1.19.17V4.99c0-.55.45-1 1-1s1 .45 1 1v13.5Z"></path></svg>"""

PLAY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M6.51 18.87a1 1 0 0 0 1-.01l10-6c.3-.18.49-.51.49-.86s-.18-.68-.49-.86l-10-6a.99.99 0 0 0-1.01-.01c-.31.18-.51.51-.51.87v12c0 .36.19.69.51.87ZM8 7.77 15.06 12 8 16.23z"></path></svg>"""

STOP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10 10-4.49 10-10S17.51 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8"></path><path d="M8 8h8v8H8z"></path></svg>"""

RESTART_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 9a3 3 0 1 0 0 6 3 3 0 1 0 0-6"></path><path d="M19.07 4.93c-.45-.45-.95-.86-1.48-1.22a9.6 9.6 0 0 0-1.7-.92c-.6-.25-1.24-.45-1.88-.58-1.32-.27-2.71-.27-4.03 0-.64.13-1.27.33-1.88.58a9.96 9.96 0 0 0-4.4 3.62 9.6 9.6 0 0 0-.92 1.7c-.25.6-.45 1.24-.58 1.88-.13.66-.2 1.34-.2 2.01s.07 1.35.2 2.01c.13.64.33 1.27.58 1.88a9.96 9.96 0 0 0 3.62 4.4 9.96 9.96 0 0 0 5.59 1.7c.67 0 1.36-.07 2.01-.2.64-.13 1.27-.33 1.88-.58a9.96 9.96 0 0 0 4.4-3.62c.36-.53.67-1.1.92-1.7s.45-1.24.58-1.88c.13-.66.2-1.34.2-2.01h-2a7.85 7.85 0 0 1-.63 3.11c-.2.48-.45.93-.74 1.36-.28.42-.61.82-.98 1.19-.36.36-.76.69-1.18.98-.43.29-.88.54-1.36.74s-.99.36-1.5.47c-1.05.22-2.17.22-3.23 0a7.3 7.3 0 0 1-1.5-.47c-.47-.2-.93-.45-1.36-.74-.42-.29-.82-.62-1.18-.98s-.69-.76-.98-1.19a8 8 0 0 1-.74-1.36c-.2-.48-.36-.99-.47-1.5A8 8 0 0 1 3.97 12a7.85 7.85 0 0 1 .63-3.11c.2-.48.45-.93.74-1.36.29-.42.62-.82.98-1.18s.76-.69 1.18-.98c.43-.29.88-.54 1.36-.74s.99-.36 1.5-.47a8 8 0 0 1 4.73.47c.48.2.93.45 1.36.74.42.29.82.62 1.18.98.17.17.32.34.48.52L15.98 9h6V3l-2.45 2.45c-.15-.18-.31-.36-.48-.52Z"></path></svg>"""

class ToolbarButton(QPushButton):
    wheeled = Signal(int)

    def __init__(self, svg_template, tooltip_text="", parent=None, draw_background_hover=True):
        super().__init__("", parent)
        self.svg_template = svg_template
        self.draw_background_hover = draw_background_hover
        self.setObjectName("ToolbarButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip_text)
            
        self._hover_progress = 0.0
        self._active = False
        self.hover_anim = QPropertyAnimation(self, b"hover_progress", self)
        self.hover_anim.setDuration(180) # Smooth, slightly longer transitions
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic) # Silky ease deceleration

    def wheelEvent(self, event):
        self.wheeled.emit(event.angleDelta().y())
        super().wheelEvent(event)

    def setActive(self, active):
        if self._active != active:
            self._active = active
            self.update()

    def set_svg_template(self, svg_template, tooltip_text=""):
        self.svg_template = svg_template
        if tooltip_text:
            self.setToolTip(tooltip_text)
        self.update()

    @Property(float)
    def hover_progress(self):
        return self._hover_progress

    @hover_progress.setter
    def hover_progress(self, val):
        self._hover_progress = val
        self.update()

    def enterEvent(self, event):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self._hover_progress)
        self.hover_anim.setEndValue(1.0)
        self.hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.stop()
        self.hover_anim.setStartValue(self._hover_progress)
        self.hover_anim.setEndValue(0.0)
        self.hover_anim.start()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        # Animate background hover color fill (6px rounded corners)
        if self.draw_background_hover and self.isEnabled():
            if self._active:
                alpha = int(140 + 115 * self._hover_progress)
                bg_color = QColor(theme.HOVER_COLOR)
                bg_color.setAlpha(alpha)
                painter.setBrush(bg_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 6, 6)
            elif self._hover_progress > 0.0:
                bg_color = QColor(theme.HOVER_COLOR)
                bg_color.setAlpha(int(255 * self._hover_progress))
                painter.setBrush(bg_color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(rect, 6, 6)
            
        # Draw dynamic vector icon with color transition (Secondary Gray -> Accent Blue)
        if not self.isEnabled():
            text_color = QColor(255, 255, 255, 25) # Faint disabled color
            icon_size = 22.0
        else:
            if self._active:
                text_color = QColor(theme.ACCENT_COLOR)
                icon_size = 22.0 + 4.0 * self._hover_progress
            else:
                sec_color = QColor(theme.TEXT_SECONDARY)
                accent_color = QColor(theme.ACCENT_COLOR)
                
                r = sec_color.red() + int((accent_color.red() - sec_color.red()) * self._hover_progress)
                g = sec_color.green() + int((accent_color.green() - sec_color.green()) * self._hover_progress)
                b = sec_color.blue() + int((accent_color.blue() - sec_color.blue()) * self._hover_progress)
                text_color = QColor(r, g, b)
                icon_size = 22.0 + 4.0 * self._hover_progress
        
        # Replace color placeholder in SVG XML template
        hex_color = text_color.name()
        colored_svg = self.svg_template.replace("COLOR_PLACEHOLDER", hex_color)
        
        # Render dynamic vector SVG
        renderer = QSvgRenderer(QByteArray(colored_svg.encode('utf-8')))
        
        # Smoothly scale from 22.0 to 26.0 on hover using subpixel float rect rendering
        ix = float(rect.x()) + (float(rect.width()) - icon_size) / 2.0
        iy = float(rect.y()) + (float(rect.height()) - icon_size) / 2.0
        icon_rect = QRectF(ix, iy, icon_size, icon_size)
        
        renderer.render(painter, icon_rect)


class StopwatchContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StopwatchContainer")
        self._anim_width = 0
        self.setFixedWidth(0)
        self.mode = "stopwatch"
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_play_stop = ToolbarButton(PLAY_SVG, "Start Timer", self)
        self.btn_play_stop.setObjectName("StopwatchButton")
        
        self.btn_restart = ToolbarButton(RESTART_SVG, "Reset Timer", self)
        self.btn_restart.setObjectName("StopwatchButton")
        
        self.lbl_time = QLineEdit("00:00:00", self)
        self.lbl_time.setObjectName("StopwatchLabel")
        self.lbl_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_time.setReadOnly(True)
        self.lbl_time.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        layout.addWidget(self.btn_play_stop)
        layout.addWidget(self.btn_restart)
        layout.addSpacing(6)
        layout.addWidget(self.lbl_time)
        
        # Initially hidden
        self.btn_play_stop.setVisible(False)
        self.btn_restart.setVisible(False)
        self.lbl_time.setVisible(False)
        
        # Connect signals for interactive input editing
        self.lbl_time.returnPressed.connect(self.btn_play_stop.click)
        self.lbl_time.editingFinished.connect(self.normalize_input)
        
    @Property(int)
    def anim_width(self):
        return self._anim_width

    @anim_width.setter
    def anim_width(self, val):
        self._anim_width = val
        self.setFixedWidth(val)
        # Show/hide children based on layout space
        has_space = val > 40
        self.btn_play_stop.setVisible(has_space)
        self.btn_restart.setVisible(has_space)
        self.lbl_time.setVisible(has_space)

    def set_mode(self, mode):
        self.mode = mode
        if mode == "stopwatch":
            self.lbl_time.setInputMask("")
            self.lbl_time.setReadOnly(True)
            self.lbl_time.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.lbl_time.setText("00:00:00")
        else: # pomodoro
            self.lbl_time.setInputMask("00:00:00;0")
            self.lbl_time.setReadOnly(False)
            self.lbl_time.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.lbl_time.setText("00:25:00")

    def normalize_input(self):
        if self.mode == "pomodoro":
            time_str = self.lbl_time.text()
            try:
                parts = time_str.split(':')
                hours = int(parts[0]) if len(parts) > 0 and parts[0].strip() else 0
                mins = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 0
                secs = int(parts[2]) if len(parts) > 2 and parts[2].strip() else 0
                
                total_seconds = hours * 3600 + mins * 60 + secs
                total_seconds = min(total_seconds, 99 * 3600 + 59 * 60 + 59)
                
                hours = total_seconds // 3600
                mins = (total_seconds // 60) % 60
                secs = total_seconds % 60
                self.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
            except Exception:
                self.lbl_time.setText("00:25:00")


class FloatingToolbar(QWidget):
    timer_clicked = Signal()
    music_clicked = Signal()
    ai_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ToolbarCapsule")
        self.is_stopwatch_active = False
        self.is_timer_running = False
        self.stopwatch_ms = 0
        self.timer_mode = "stopwatch"
        self.pomodoro_ms = 25 * 60 * 1000
        
        # Setup stopwatch QTimer
        self.stopwatch_timer = QTimer(self)
        self.stopwatch_timer.setInterval(1000)
        self.stopwatch_timer.timeout.connect(self.update_stopwatch_time)
        
        self.init_ui()

    def init_ui(self):
        # Base dimensions of capsule toolbar - initially collapsed
        self.setFixedHeight(44)
        self.setMinimumWidth(174)
        self.setMaximumWidth(174)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Stopwatch container (starts with width 0)
        self.stopwatch_container = StopwatchContainer(self)
        
        # Connect stopwatch container buttons
        self.stopwatch_container.btn_play_stop.clicked.connect(self.handle_play_stop)
        self.stopwatch_container.btn_restart.clicked.connect(self.restart_stopwatch)
        
        # Standard buttons
        self.btn_timer = ToolbarButton(TIMER_SVG, "Focus Stopwatch", self)
        self.btn_music = ToolbarButton(SPOTIFY_SVG, "Spotify Integration", self)
        self.btn_ai = ToolbarButton(AI_SVG, "Gemini AI Chat", self)
        self.btn_settings = ToolbarButton(SETTINGS_SVG, "Settings", self)
        
        self.btn_timer.clicked.connect(self.toggle_stopwatch)
        self.btn_timer.wheeled.connect(self.handle_timer_wheel)
        self.btn_music.clicked.connect(self.music_clicked.emit)
        self.btn_ai.clicked.connect(self.ai_clicked.emit)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        
        # Assemble from left to right: [Stopwatch Container] [Timer] [Spotify] [AI] [Settings]
        layout.addWidget(self.stopwatch_container)
        layout.addWidget(self.btn_timer)
        layout.addWidget(self.btn_music)
        layout.addWidget(self.btn_ai)
        layout.addWidget(self.btn_settings)
        
        self.setStyleSheet(qss.get_toolbar_style())
        
        # Setup property animations
        self.stopwatch_anim = QPropertyAnimation(self.stopwatch_container, b"anim_width", self)
        self.stopwatch_anim.setDuration(300)
        self.stopwatch_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.toolbar_min_anim = QPropertyAnimation(self, b"minimumWidth", self)
        self.toolbar_min_anim.setDuration(300)
        self.toolbar_min_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.toolbar_max_anim = QPropertyAnimation(self, b"maximumWidth", self)
        self.toolbar_max_anim.setDuration(300)
        self.toolbar_max_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def handle_timer_wheel(self, delta):
        if delta == 0:
            return
        # Do not allow mode switching if the timer is actively running
        if self.is_timer_running:
            return
            
        if self.timer_mode == "stopwatch":
            self.timer_mode = "pomodoro"
            self.btn_timer.set_svg_template(POMODORO_SVG, "Pomodoro Timer")
            self.stopwatch_container.set_mode("pomodoro")
        else:
            self.timer_mode = "stopwatch"
            self.btn_timer.set_svg_template(TIMER_SVG, "Focus Stopwatch")
            self.stopwatch_container.set_mode("stopwatch")
            
        # Update displayed time immediately based on the current mode
        if self.is_stopwatch_active:
            if self.timer_mode == "stopwatch":
                hours = self.stopwatch_ms // 3600000
                mins = (self.stopwatch_ms // 60000) % 60
                secs = (self.stopwatch_ms // 1000) % 60
                self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
            else:
                hours = self.pomodoro_ms // 3600000
                mins = (self.pomodoro_ms // 60000) % 60
                secs = (self.pomodoro_ms // 1000) % 60
                self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")

    def toggle_stopwatch(self):
        # Stop animations if running
        self.stopwatch_anim.stop()
        self.toolbar_min_anim.stop()
        self.toolbar_max_anim.stop()
        
        if not self.is_stopwatch_active:
            # Expand to 318px
            self.stopwatch_anim.setStartValue(self.stopwatch_container.width())
            self.stopwatch_anim.setEndValue(144)
            
            self.toolbar_min_anim.setStartValue(self.width())
            self.toolbar_min_anim.setEndValue(318)
            self.toolbar_max_anim.setStartValue(self.width())
            self.toolbar_max_anim.setEndValue(318)
            
            self.stopwatch_anim.start()
            self.toolbar_min_anim.start()
            self.toolbar_max_anim.start()
            
            # Reset timer running state when opening (do not start automatically)
            self.is_timer_running = False
            self.stopwatch_container.btn_play_stop.set_svg_template(PLAY_SVG, "Start Timer")
            
            if self.timer_mode == "stopwatch":
                self.stopwatch_container.set_mode("stopwatch")
                hours = self.stopwatch_ms // 3600000
                mins = (self.stopwatch_ms // 60000) % 60
                secs = (self.stopwatch_ms // 1000) % 60
                self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
            else:
                self.stopwatch_container.set_mode("pomodoro")
                hours = self.pomodoro_ms // 3600000
                mins = (self.pomodoro_ms // 60000) % 60
                secs = (self.pomodoro_ms // 1000) % 60
                self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
                
            self.is_stopwatch_active = True
            self.btn_timer.setActive(True)
        else:
            # Collapse back to 174px
            self.stopwatch_anim.setStartValue(self.stopwatch_container.width())
            self.stopwatch_anim.setEndValue(0)
            
            self.toolbar_min_anim.setStartValue(self.width())
            self.toolbar_min_anim.setEndValue(174)
            self.toolbar_max_anim.setStartValue(self.width())
            self.toolbar_max_anim.setEndValue(174)
            
            self.stopwatch_anim.start()
            self.toolbar_min_anim.start()
            self.toolbar_max_anim.start()
            
            # Stop timer when collapsed
            self.stopwatch_timer.stop()
            self.is_timer_running = False
            self.is_stopwatch_active = False
            self.btn_timer.setActive(False)
            
            # Reset edit modes when collapsed
            self.stopwatch_container.lbl_time.setReadOnly(True)
            self.stopwatch_container.lbl_time.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def start_stopwatch_for_task(self):
        # Force stopwatch mode when starting stopwatch for a task
        if self.timer_mode != "stopwatch":
            self.timer_mode = "stopwatch"
            self.btn_timer.set_svg_template(TIMER_SVG, "Focus Stopwatch")
            self.stopwatch_container.set_mode("stopwatch")
            
        # Open stopwatch if collapsed
        if not self.is_stopwatch_active:
            self.toggle_stopwatch()
        else:
            self.btn_timer.setActive(True)
        # Reset stopwatch
        self.restart_stopwatch()
        # Start if not already running
        if not self.is_timer_running:
            self.stopwatch_timer.start()
            self.is_timer_running = True
            self.stopwatch_container.btn_play_stop.set_svg_template(STOP_SVG, "Pause Timer")

    def stop_stopwatch(self):
        # Stop stopwatch timer without triggering callback
        if self.is_timer_running:
            self.stopwatch_timer.stop()
            self.is_timer_running = False
            self.stopwatch_container.btn_play_stop.set_svg_template(PLAY_SVG, "Start Timer")
        # Collapse stopwatch if expanded
        if self.is_stopwatch_active:
            self.toggle_stopwatch()
        else:
            self.btn_timer.setActive(False)

    def update_stopwatch_time(self):
        if self.timer_mode == "stopwatch":
            self.stopwatch_ms += 1000
            hours = self.stopwatch_ms // 3600000
            mins = (self.stopwatch_ms // 60000) % 60
            secs = (self.stopwatch_ms // 1000) % 60
            self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
        else:
            if self.pomodoro_ms > 0:
                self.pomodoro_ms -= 1000
                if self.pomodoro_ms < 0:
                    self.pomodoro_ms = 0
                hours = self.pomodoro_ms // 3600000
                mins = (self.pomodoro_ms // 60000) % 60
                secs = (self.pomodoro_ms // 1000) % 60
                self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
                if self.pomodoro_ms == 0:
                    self.stopwatch_timer.stop()
                    self.is_timer_running = False
                    self.stopwatch_container.btn_play_stop.set_svg_template(PLAY_SVG, "Start Timer")
                    self.stopwatch_container.lbl_time.setReadOnly(False)
                    self.stopwatch_container.lbl_time.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
                    # Notify parent window
                    if self.parent() and hasattr(self.parent(), "on_pomodoro_finished"):
                        self.parent().on_pomodoro_finished()
            else:
                self.stopwatch_timer.stop()
                self.is_timer_running = False
                self.stopwatch_container.btn_play_stop.set_svg_template(PLAY_SVG, "Start Timer")
                self.stopwatch_container.lbl_time.setReadOnly(False)
                self.stopwatch_container.lbl_time.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def handle_play_stop(self):
        if not self.is_timer_running:
            if self.timer_mode == "pomodoro":
                # Parse input before starting countdown
                time_str = self.stopwatch_container.lbl_time.text()
                try:
                    parts = time_str.split(':')
                    hours = int(parts[0]) if len(parts) > 0 and parts[0].strip() else 0
                    mins = int(parts[1]) if len(parts) > 1 and parts[1].strip() else 0
                    secs = int(parts[2]) if len(parts) > 2 and parts[2].strip() else 0
                    
                    total_seconds = hours * 3600 + mins * 60 + secs
                    if total_seconds <= 0:
                        return
                    self.pomodoro_ms = total_seconds * 1000
                    
                    # Update with formatted/normalized values
                    hours = total_seconds // 3600
                    mins = (total_seconds // 60) % 60
                    secs = total_seconds % 60
                    self.stopwatch_container.lbl_time.setText(f"{hours:02d}:{mins:02d}:{secs:02d}")
                except Exception:
                    return
                self.stopwatch_container.lbl_time.setReadOnly(True)
                self.stopwatch_container.lbl_time.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                
            self.stopwatch_timer.start()
            self.is_timer_running = True
            self.stopwatch_container.btn_play_stop.set_svg_template(STOP_SVG, "Pause Timer")
        else:
            self.stopwatch_timer.stop()
            self.is_timer_running = False
            self.stopwatch_container.btn_play_stop.set_svg_template(PLAY_SVG, "Start Timer")
            if self.timer_mode == "pomodoro":
                self.stopwatch_container.lbl_time.setReadOnly(False)
                self.stopwatch_container.lbl_time.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
                
            # Notify parent window if stopped manually via toolbar
            if self.parent() and hasattr(self.parent(), "on_stopwatch_stopped"):
                self.parent().on_stopwatch_stopped()

    def restart_stopwatch(self):
        if self.timer_mode == "stopwatch":
            self.stopwatch_ms = 0
            self.stopwatch_container.lbl_time.setText("00:00:00")
        else:
            self.stopwatch_timer.stop()
            self.is_timer_running = False
            self.stopwatch_container.btn_play_stop.set_svg_template(PLAY_SVG, "Start Timer")
            self.stopwatch_container.lbl_time.setReadOnly(False)
            self.stopwatch_container.lbl_time.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
            self.stopwatch_container.lbl_time.setText("00:25:00")
            self.pomodoro_ms = 25 * 60 * 1000

    def paintEvent(self, event):
        # We draw the static glassy rounded rect
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Static 60% opacity background (152 alpha) and 10% opacity border (24 alpha)
        bg_color = QColor(theme.SEC_CARD_COLOR)
        bg_color.setAlpha(152) 
        
        border_color = QColor(255, 255, 255, 24) 
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        
        # Reduced border radius (10px rounded rectangle style)
        painter.drawRoundedRect(rect, 10, 10)
