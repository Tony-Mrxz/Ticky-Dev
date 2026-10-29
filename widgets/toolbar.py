from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal, QRectF, QByteArray, QTimer
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QLabel, QLineEdit, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtSvg import QSvgRenderer
from styles import theme, qss

# Raw SVG Templates with COLOR_PLACEHOLDER for dynamic dye colors
TIMER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M11 2v2.06c-4.49.5-8 4.32-8 8.94 0 4.96 4.04 9 9 9s9-4.04 9-9c0-2.12-.74-4.07-1.98-5.61l1.46-1.46-1.41-1.41-1.46 1.46A9 9 0 0 0 13 4.06V2zm8 11c0 3.86-3.14 7-7 7s-7-3.14-7-7 3.14-7 7-7 7 3.14 7 7"></path><path d="M11 8h2v6h-2z"></path></svg>"""

POMODORO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M19.07 4.93a9.9 9.9 0 0 0-3.18-2.14A9.95 9.95 0 0 0 12 2c-.55 0-1 .45-1 1v5h2V4.06c.73.09 1.44.28 2.11.57.95.4 1.81.98 2.54 1.72.74.73 1.31 1.59 1.71 2.54.42.99.63 2.03.63 3.11s-.21 2.13-.63 3.11c-.4.95-.98 1.81-1.72 2.54-.73.74-1.59 1.31-2.54 1.71-1.97.83-4.26.83-6.23 0-.95-.4-1.81-.98-2.54-1.72a7.8 7.8 0 0 1-1.71-2.54c-.42-.99-.63-2.03-.63-3.11s.21-2.13.63-3.11c.4-.95.98-1.81 1.72-2.54L4.93 4.92c-.92.92-1.64 1.99-2.14 3.18C2.27 9.33 2 10.64 2 11.99s.26 2.66.79 3.89c.5 1.19 1.23 2.26 2.14 3.18s1.99 1.64 3.18 2.14c1.23.52 2.54.79 3.89.79s2.66-.26 3.89-.79c1.19-.5 2.26-1.23 3.18-2.14s1.64-1.99 2.14-3.18c.52-1.23.79-2.54.79-3.89s-.26-2.66-.79-3.89c-.5-1.19-1.23-2.26-2.14-3.18Z"></path><path d="M12.88 11.12 8 8l3.12 4.88c1.22 1.68 3.45-.55 1.77-1.77Z"></path></svg>"""

SPOTIFY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M11 8h2v8h-2zm8 2h2v4h-2zm-4-5h2v14h-2zM7 3h2v18H7zM3 9h2v6H3z"></path></svg>"""

SETTINGS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 8c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4-1.79-4-4-4m0 6c-1.08 0-2-.92-2-2s.92-2 2-2 2 .92 2 2-.92 2-2 2"></path><path d="m20.42 13.4-.51-.29c.05-.37.08-.74.08-1.11s-.03-.74-.08-1.11l.51-.29c.96-.55 1.28-1.78.73-2.73l-1-1.73a2.006 2.006 0 0 0-2.73-.73l-.53.31c-.58-.46-1.22-.83-1.9-1.11v-.6c0-1.1-.9-2-2-2h-2c-1.1 0-2 .9-2 2v.6c-.67.28-1.31.66-1.9 1.11l-.53-.31c-.96-.55-2.18-.22-2.73.73l-1 1.73c-.55.96-.22 2.18.73 2.73l.51.29c-.05.37-.08.74-.08 1.11s.03.74.08 1.11l-.51.29c-.96.55-1.28 1.78-.73 2.73l1 1.73c.55.95 1.77 1.28 2.73.73l.53-.31c.58.46 1.22.83 1.9 1.11v.6c0 1.1.9 2 2 2h2c1.1 0 2-.9 2-2v-.6a8.7 8.7 0 0 0 1.9-1.11l.53.31c.95.55 2.18.22 2.73-.73l1-1.73c.55-.96.22-2.18-.73-2.73m-2.59-2.78c.11.45.17.92.17 1.38s-.06.92-.17 1.38a1 1 0 0 0 .47 1.11l1.12.65-1 1.73-1.14-.66c-.38-.22-.87-.16-1.19.14-.68.65-1.51 1.13-2.38 1.4-.42.13-.71.52-.71.96v1.3h-2v-1.3c0-.44-.29-.83-.71-.96-.88-.27-1.7-.75-2.38-1.4a1.01 1.01 0 0 0-1.19-.15l-1.14.66-1-1.73 1.12-.65c.39-.22.58-.68.47-1.11-.11-.45-.17-.92-.17-1.38s.06-.93.17-1.38A1 1 0 0 0 5.7 9.5l-1.12-.65 1-1.73 1.14.66c.38.22.87.16 1.19-.14.68-.65 1.51-1.13 2.38-1.4.42-.13.71-.52.71-.96v-1.3h2v1.3c0 .44.29.83.71.96.88.27 1.7.75 2.38 1.4.32.31.81.36 1.19.14l1.14-.66 1 1.73-1.12.65c-.39.22-.58.68-.47 1.11Z"></path></svg>"""

AI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M20.57 10.18c.45-1.36.3-2.85-.43-4.09a5.03 5.03 0 0 0-5.42-2.42 5.05 5.05 0 0 0-7.14-.38c-.66.59-1.15 1.35-1.43 2.19A4.98 4.98 0 0 0 2.82 7.9c-1.1 1.9-.85 4.29.62 5.91-.45 1.36-.3 2.85.43 4.09a5.045 5.045 0 0 0 5.43 2.42A5.03 5.03 0 0 0 13.06 22c2.19 0 4.14-1.41 4.81-3.5a4.98 4.98 0 0 0 3.33-2.42 5.04 5.04 0 0 0-.62-5.89Zm-7.52 10.51c-.88 0-1.72-.31-2.4-.87l.12-.07 3.98-2.3c.2-.12.33-.33.33-.57v-5.61l1.68.97s.03.02.03.04v4.65c0 2.07-1.68 3.74-3.75 3.75ZM5 17.25c-.44-.76-.6-1.65-.45-2.51l.12.07 3.99 2.3c.2.12.45.12.65 0l4.87-2.81v1.94s-.01.04-.03.05l-4.03 2.33A3.756 3.756 0 0 1 5 17.25M3.95 8.58a3.7 3.7 0 0 1 1.97-1.64v4.73c0 .23.12.45.32.56l4.85 2.8-1.68.97h-.06l-4.03-2.32a3.754 3.754 0 0 1-1.37-5.12zm13.83 3.21-4.86-2.82L14.6 8h.06l4.03 2.33a3.743 3.743 0 0 1 1.37 5.12 3.8 3.8 0 0 1-1.94 1.64v-4.73a.67.67 0 0 0-.34-.56Zm1.68-2.52-.12-.07-3.98-2.32a.63.63 0 0 0-.65 0L9.84 9.69V7.75s0-.04.02-.05l4.03-2.32a3.75 3.75 0 0 1 5.12 1.38c.44.76.59 1.64.45 2.51v.02ZM8.93 12.72l-1.68-.97s-.03-.03-.03-.05V7.06c0-2.07 1.68-3.75 3.75-3.74.87 0 1.72.31 2.39.87l-.12.07-3.98 2.3c-.2.12-.33.33-.33.57v5.6Zm.91-1.97 2.17-1.25 2.17 1.25v2.5l-2.16 1.25-2.17-1.25v-2.5Z"></path></svg>"""

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
        self._icon_angle = 0.0
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

    @Property(float)
    def icon_angle(self):
        return getattr(self, '_icon_angle', 0.0)

    @icon_angle.setter
    def icon_angle(self, val):
        self._icon_angle = val
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
        
        angle = getattr(self, '_icon_angle', 0.0)
        if angle != 0.0:
            painter.save()
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            cx = float(icon_rect.x()) + float(icon_rect.width()) / 2.0
            cy = float(icon_rect.y()) + float(icon_rect.height()) / 2.0
            painter.translate(cx, cy)
            painter.rotate(angle)
            half = float(icon_rect.width()) / 2.0
            renderer.render(painter, QRectF(-half, -half, icon_rect.width(), icon_rect.height()))
            painter.restore()
        else:
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
        
        self.opacity_play = QGraphicsOpacityEffect(self.btn_play_stop)
        self.btn_play_stop.setGraphicsEffect(self.opacity_play)
        
        self.opacity_restart = QGraphicsOpacityEffect(self.btn_restart)
        self.btn_restart.setGraphicsEffect(self.opacity_restart)
        
        self.opacity_lbl = QGraphicsOpacityEffect(self.lbl_time)
        self.lbl_time.setGraphicsEffect(self.opacity_lbl)
        
        self.opacity_play.setOpacity(0.0)
        self.opacity_restart.setOpacity(0.0)
        self.opacity_lbl.setOpacity(0.0)
        
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
        
        progress = max(0.0, min(1.0, val / 144.0))
        show_widgets = val > 0
        self.btn_play_stop.setVisible(show_widgets)
        self.btn_restart.setVisible(show_widgets)
        self.lbl_time.setVisible(show_widgets)
        
        if hasattr(self, 'opacity_play') and self.opacity_play:
            fade = progress * progress  # Smooth acceleration
            self.opacity_play.setOpacity(fade)
            self.opacity_restart.setOpacity(fade)
            self.opacity_lbl.setOpacity(fade)

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

    def __init__(self, parent=None, solid_background: bool = False):
        super().__init__(parent)
        self.solid_background = solid_background
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
        
        self.timer_icon_anim = QPropertyAnimation(self.btn_timer, b"icon_angle", self)
        self.timer_icon_anim.setDuration(300)
        self.timer_icon_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

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
        self.timer_icon_anim.stop()
        
        if not self.is_stopwatch_active:
            # Expand to 318px
            self.stopwatch_anim.setStartValue(self.stopwatch_container.width())
            self.stopwatch_anim.setEndValue(144)
            
            self.toolbar_min_anim.setStartValue(self.width())
            self.toolbar_min_anim.setEndValue(318)
            self.toolbar_max_anim.setStartValue(self.width())
            self.toolbar_max_anim.setEndValue(318)
            
            self.timer_icon_anim.setStartValue(self.btn_timer.icon_angle)
            self.timer_icon_anim.setEndValue(180.0)
            
            self.stopwatch_anim.start()
            self.toolbar_min_anim.start()
            self.toolbar_max_anim.start()
            self.timer_icon_anim.start()
            
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
            
            self.timer_icon_anim.setStartValue(self.btn_timer.icon_angle)
            self.timer_icon_anim.setEndValue(360.0 if self.btn_timer.icon_angle > 90 else 0.0)
            
            self.stopwatch_anim.start()
            self.toolbar_min_anim.start()
            self.toolbar_max_anim.start()
            self.timer_icon_anim.start()
            
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        theme_border = QColor(theme.BORDER_COLOR)
        if not theme_border.isValid():
            theme_border = QColor(255, 255, 255, 24)
        elif theme_border.alpha() < 30:
            theme_border.setAlpha(36)

        if getattr(self, "solid_background", False):
            # Pure solid opaque background matching the notch (zero transparency)
            bg_color = QColor(theme.BG_COLOR)
            border_color = theme_border
        else:
            # Static 60% opacity background (152 alpha) and themed border
            bg_color = QColor(theme.SEC_CARD_COLOR)
            bg_color.setAlpha(152) 
            border_color = theme_border
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        
        # Reduced border radius (10px rounded rectangle style)
        painter.drawRoundedRect(rect, 10, 10)
