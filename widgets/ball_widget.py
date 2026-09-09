# widgets/ball_widget.py
"""Draggable floating glass-like ball widget with task reminders and overlay menu options."""

import random
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QTimer, Property
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QMenu
from PySide6.QtGui import QPainter, QColor, QPen, QCursor, QPainterPath
from styles import theme

class BallWidget(QWidget):
    def __init__(self, parent_window=None):
        # Pass None to parent to make it a standalone floating window on desktop
        super().__init__(None)
        self.parent_window = parent_window
        
        import sys
        if sys.platform == 'darwin':
            flags = (
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Window
            )
        else:
            flags = (
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.SubWindow
            )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        if sys.platform == 'darwin':
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        
        # Dimensions: 40px height, starts with 40px width (perfect circle)
        self.setFixedHeight(40)
        self.setMinimumWidth(40)
        self.setMaximumWidth(40)
        self._current_width = 40
        
        # Dragging state
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()
        self.is_dragging = False
        self._hovered = False
        
        # UI components
        self.init_ui()
        
        # Setup task reminder loop (triggers every 45s)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(45000)
        self.reminder_timer.timeout.connect(self.trigger_task_reminder)
        self.reminder_timer.start()
        
        # Setup width expand/collapse animation
        self.width_anim = QPropertyAnimation(self, b"current_width", self)
        self.width_anim.setDuration(350)
        self.width_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.width_anim.finished.connect(self.on_width_anim_finished)
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        # Margins: 14px left, 10px right margin (reversed for leftward expansion)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Text label for task reminder (placed first/left)
        self.lbl_task = QLabel(self)
        self.lbl_task.setObjectName("BallTaskLabel")
        self.lbl_task.setStyleSheet(f"""
            QLabel#BallTaskLabel {{
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                font-weight: 500;
                background-color: transparent;
                border: none;
            }}
        """)
        self.lbl_task.hide()
        layout.addWidget(self.lbl_task)
        
        # Spacer for the ticky checkmark icon (placed second/right)
        self.icon_spacer = QWidget(self)
        self.icon_spacer.setFixedSize(20, 20)
        layout.addWidget(self.icon_spacer)

    @Property(int)
    def current_width(self):
        return self._current_width

    @current_width.setter
    def current_width(self, val):
        old_width = self._current_width
        self._current_width = val
        
        # Shift the X coordinate to the left to anchor the right edge during expansion
        delta = val - 40
        if hasattr(self, 'original_x'):
            self.move(self.original_x - delta, self.y())
            
        self.setFixedWidth(val)
        
        # Show/hide task label depending on expansion size
        if val > 80:
            self.lbl_task.show()
        else:
            self.lbl_task.hide()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._current_width = 40
        self.setFixedWidth(40)
        self.lbl_task.hide()
        self.lbl_task.setText("")
        self.task_color = None
        self.original_x = self.x()
        self.reminder_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.reminder_timer.stop()
        self.width_anim.stop()

    def on_width_anim_finished(self):
        if self.width() <= 45:
            self.task_color = None
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.globalPosition().toPoint()
            self.window_start_pos = self.frameGeometry().topLeft()
            self.is_dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            new_pos = self.window_start_pos + delta
            self.move(new_pos)
            self.original_x = new_pos.x() + (self.width() - 40)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
            delta_pos = event.globalPosition().toPoint() - self.drag_start_pos
            # Manhattan length check to separate dragging from clicking
            if delta_pos.manhattanLength() < 5:
                self.handle_click()
            event.accept()

    def handle_click(self):
        # Open contextual settings menu at cursor position
        menu = QMenu(self)
        
        expand_action = menu.addAction("Expand Ticky")
        spotify_action = menu.addAction("Spotify Player")
        settings_action = menu.addAction("Settings")
        
        if self.parent_window:
            expand_action.triggered.connect(self.parent_window.restore_from_ball)
            spotify_action.triggered.connect(self.parent_window.enter_spotify_mini_mode)
            settings_action.triggered.connect(self.parent_window.show_settings_menu)
            
        menu.exec(QCursor.pos())

    def trigger_task_reminder(self):
        # Check if tasks exist in parent window
        if not self.parent_window or not hasattr(self.parent_window, "tasks") or not self.parent_window.tasks:
            return
            
        # Select random task from lists
        random_task = random.choice(self.parent_window.tasks)
        
        # Get task color dynamically
        from widgets.task_card import get_task_color
        self.task_color = QColor(get_task_color(random_task))
        # Elide text if too long
        if len(random_task) > 28:
            random_task = random_task[:25] + "..."
            
        self.lbl_task.setText(random_task)
        
        # Store original coordinates for shifting leftward
        self.original_x = self.x()
        self.original_width = self.width()
        
        # Animate horizontal expand
        self.width_anim.stop()
        self.width_anim.setStartValue(self.width())
        self.width_anim.setEndValue(240)
        self.width_anim.start()
        
        # Single-shot timer to collapse back after 5 seconds
        QTimer.singleShot(5000, self.collapse_ball)

    def collapse_ball(self):
        # Collapse back to circle
        self.width_anim.stop()
        self.width_anim.setStartValue(self.width())
        self.width_anim.setEndValue(40)
        self.width_anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Opaque background matching Ticky's card background exactly
        bg_color = QColor(theme.MAIN_CARD_COLOR)
        bg_color.setAlpha(255) 
        painter.setBrush(bg_color)
        
        # Paint glowing active-accent border
        if self.width() > 45 and hasattr(self, 'task_color') and self.task_color:
            # We are expanded and showing a task - draw a glowing outline with task color
            border_color = self.task_color
            
            # Subtle soft glow backdrop
            glow_color = QColor(self.task_color)
            glow_color.setAlpha(60)
            painter.setPen(QPen(glow_color, 4.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 20.0, 20.0)
            
            # Sharp main border
            painter.setPen(QPen(border_color, 1.5))
            painter.setBrush(bg_color)
        else:
            border_color = QColor(theme.ACCENT_COLOR) if self._hovered else QColor(theme.BORDER_COLOR)
            painter.setPen(QPen(border_color, 1.5))
            
        # Draw rounded rect capsule
        painter.drawRoundedRect(rect, 20.0, 20.0)
        
        # Paint the Ticky checkmark icon inside the spacer widget rect (at right coordinates)
        if self.width() > 45 and hasattr(self, 'task_color') and self.task_color:
            icon_color = self.task_color
        else:
            icon_color = QColor(theme.ACCENT_COLOR) if self._hovered else QColor(theme.TEXT_PRIMARY)
        
        painter.save()
        # Translate to the right side of the capsule (width - 30px)
        painter.translate(self.width() - 30.0, 10.0)
        painter.scale(20.0 / 24.0, 20.0 / 24.0)
        
        pen = QPen(icon_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Frame
        frame_path = QPainterPath()
        frame_path.addRoundedRect(3, 3, 18, 18, 2, 2)
        painter.drawPath(frame_path)
        
        # Checkmark
        pen.setWidth(1.5)
        painter.setPen(pen)
        checkmark = QPainterPath()
        checkmark.moveTo(7.29, 12.71)
        checkmark.lineTo(10.49, 15.91)
        checkmark.lineTo(16.69, 9.71)
        painter.drawPath(checkmark)
        
        painter.restore()

    def showEvent(self, event):
        super().showEvent(event)
        import sys
        if sys.platform == 'darwin':
            from utils.mac_window import configure_mac_window
            configure_mac_window(self.winId(), True)
