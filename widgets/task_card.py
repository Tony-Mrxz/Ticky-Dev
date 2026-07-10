# widgets/task_card.py
"""Interactive custom task card component with micro-animations."""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property, Signal, QTimer, QByteArray, QRectF
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect, QLineEdit, QPushButton
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtSvg import QSvgRenderer
from styles import theme, qss

FOCUS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M14.59 6.59c-.78.78-.78 2.05 0 2.83s2.05.78 2.83 0 .78-2.05 0-2.83-2.05-.78-2.83 0M5 16c-2 1-2 5-2 5s3 0 5-2z"></path><path d="M21 2h-3.69c-2.4 0-4.66.94-6.36 2.64L8.69 6.9a8.4 8.4 0 0 0-6.24 1.27c-.25.17-.41.44-.44.73s.08.59.29.81l12 12c.2.2.45.29.71.29s.51-.1.71-.29c1.9-1.9 1.6-5.08 1.38-6.38l2.28-2.28c1.7-1.7 2.64-3.96 2.64-6.36V3c0-.55-.45-1-1-1Zm-1 4.69c0 1.87-.73 3.63-2.05 4.95l-2.66 2.66c-.25.25-.35.61-.26.95.19.79.45 2.78-.17 4.2L4.65 9.24c2.11-.89 3.94-.32 4.03-.29.36.12.76.03 1.02-.24l2.66-2.66A6.96 6.96 0 0 1 17.31 4H20z"></path></svg>"""

STOP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 2C6.49 2 2 6.49 2 12s4.49 10 10 10 10-4.49 10-10S17.51 2 12 2m0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8"></path><path d="M8 8h8v8H8z"></path></svg>"""

class PlayTaskButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setObjectName("PlayTaskButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(20, 20)
        self._active = False
        self._hovered = False

    def setActive(self, active):
        self._active = active
        self.update()

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Decide SVG template and color based on active/hover state
        if self._active:
            svg_template = STOP_SVG
            base_color = QColor("#FF453A")
            hover_color = QColor("#FF6961")
        else:
            svg_template = FOCUS_SVG
            base_color = QColor(theme.TEXT_SECONDARY)
            hover_color = QColor(theme.ACCENT_COLOR)
            
        color = hover_color if self._hovered else base_color
        
        # Replace color placeholder in SVG XML template
        hex_color = color.name()
        colored_svg = svg_template.replace("COLOR_PLACEHOLDER", hex_color)
        
        # Render dynamic vector SVG
        renderer = QSvgRenderer(QByteArray(colored_svg.encode('utf-8')))
        
        # Draw icon inside the button rect (size 18x18)
        icon_size = 18.0
        ix = float(rect.x()) + (float(rect.width()) - icon_size) / 2.0
        iy = float(rect.y()) + (float(rect.height()) - icon_size) / 2.0
        icon_rect = QRectF(ix, iy, icon_size, icon_size)
        
        renderer.render(painter, icon_rect)

class TaskInputField(QLineEdit):
    escape_pressed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AddTaskInput")
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        # We delay slightly to allow click/submit events to register first
        QTimer.singleShot(150, self.escape_pressed.emit)
        super().focusOutEvent(event)


from styles.theme import RAINBOW_COLORS

def get_task_color(text):
    if not RAINBOW_COLORS:
        return "#0A84FF"
    h = sum(ord(c) for c in text)
    return RAINBOW_COLORS[h % len(RAINBOW_COLORS)]


class TaskCheckbox(QWidget):
    toggled = Signal(bool)

    def __init__(self, color_hex, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self._checked = False
        self._hovered = False
        self.color = QColor(color_hex)
        
        # Hover progress animation
        self._hover_progress = 0.0
        self.hover_anim = QPropertyAnimation(self, b"hover_progress", self)
        self.hover_anim.setDuration(120)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        # Check progress animation
        self._check_progress = 0.0
        self.check_anim = QPropertyAnimation(self, b"check_progress", self)
        self.check_anim.setDuration(150)
        self.check_anim.setEasingCurve(QEasingCurve.Type.OutQuad)

    @Property(float)
    def hover_progress(self):
        return self._hover_progress

    @hover_progress.setter
    def hover_progress(self, val):
        self._hover_progress = val
        self.update()

    @Property(float)
    def check_progress(self):
        return self._check_progress

    @check_progress.setter
    def check_progress(self, val):
        self._check_progress = val
        self.update()

    def set_hovered(self, hovered):
        if self._hovered != hovered:
            self._hovered = hovered
            self.hover_anim.stop()
            self.hover_anim.setStartValue(self._hover_progress)
            self.hover_anim.setEndValue(1.0 if hovered else 0.0)
            self.hover_anim.start()

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self.check_anim.stop()
            self.check_anim.setStartValue(self._check_progress)
            self.check_anim.setEndValue(1.0 if checked else 0.0)
            self.check_anim.start()
            self.toggled.emit(checked)

    def isChecked(self):
        return self._checked

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._checked)
            event.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Calculate background fill color:
        # Subtle 15% opacity fill on hover when unchecked, solid fill when checked
        fill_alpha = int((38 * self._hover_progress * (1.0 - self._check_progress)) + (255 * self._check_progress))
        fill_color = QColor(self.color.red(), self.color.green(), self.color.blue(), fill_alpha)
        
        # Calculate border color:
        # Subtle white border by default, dynamic color on hover/check
        c_base = QColor(255, 255, 255, 38)
        active_factor = max(self._hover_progress, self._check_progress)
        r = c_base.red() + int((self.color.red() - c_base.red()) * active_factor)
        g = c_base.green() + int((self.color.green() - c_base.green()) * active_factor)
        b = c_base.blue() + int((self.color.blue() - c_base.blue()) * active_factor)
        a = c_base.alpha() + int((255 - c_base.alpha()) * active_factor)
        border_color = QColor(r, g, b, a)
        
        # Draw outer rounded rect border and background
        painter.setPen(QPen(border_color, 1.5))
        painter.setBrush(fill_color)
        painter.drawRoundedRect(rect, 4.0, 4.0)


class TaskCard(QWidget):
    completed = Signal()
    focus_toggled = Signal(bool)

    def __init__(self, text, color_hex=None, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskCardContainer")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        
        # Assign dynamic colorful palette
        if color_hex is None:
            color_hex = get_task_color(text)
        self.color = QColor(color_hex)
        
        # Double layering: we draw the card offset internally to create smooth lift
        self._hover_lift = 0.0
        self._opacity = 1.0
        self._max_height = 42
        self.setFixedHeight(self._max_height)
        
        self.lift_anim = QPropertyAnimation(self, b"hover_lift", self)
        self.lift_anim.setDuration(120)
        self.lift_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Opacity effect for completion fade
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        self.init_ui(text)

    @Property(float)
    def hover_lift(self):
        return self._hover_lift

    @hover_lift.setter
    def hover_lift(self, val):
        self._hover_lift = val
        self.update()

    def init_ui(self, text):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        self.checkbox = TaskCheckbox(self.color.name(), self)
        self.checkbox.toggled.connect(self.on_checkbox_toggle)
        
        self.text_label = QLabel(text, self)
        self.text_label.setObjectName("TaskText")
        
        self.play_button = PlayTaskButton(self)
        self.play_button.setToolTip("Start Task")
        self.play_button.clicked.connect(self.on_play_clicked)
        self.play_button.hide()
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.text_label)
        layout.addStretch()
        layout.addWidget(self.play_button)
        
        self.setStyleSheet(qss.get_task_card_style())
        self.update_text_style()

    def update_text_style(self):
        is_checked = self.checkbox.isChecked()
        is_hovered = self._hovered
        
        font = self.text_label.font()
        font.setStrikeOut(is_checked)
        self.text_label.setFont(font)
        
        if is_checked or is_hovered:
            color = self.color.name()
        else:
            color = theme.TEXT_PRIMARY
                
        self.text_label.setStyleSheet(f"color: {color};")

    def on_play_clicked(self):
        is_active = self.play_button._active
        self.focus_toggled.emit(not is_active)

    def set_focus_active(self, active):
        self.play_button.setActive(active)
        self.play_button.setToolTip("Stop Task" if active else "Start Task")
        self.checkbox.setEnabled(not active)
        if active:
            self.play_button.show()
        elif not self._hovered:
            self.play_button.hide()

    def enterEvent(self, event):
        self._hovered = True
        self.lift_anim.stop()
        self.lift_anim.setStartValue(self._hover_lift)
        self.lift_anim.setEndValue(3.0) # Lift up by 3px
        self.lift_anim.start()
        
        self.checkbox.set_hovered(True)
        self.play_button.show()
        self.update_text_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.lift_anim.stop()
        self.lift_anim.setStartValue(self._hover_lift)
        self.lift_anim.setEndValue(0.0) # Drop back down
        self.lift_anim.start()
        
        self.checkbox.set_hovered(False)
        if not self.play_button._active:
            self.play_button.hide()
        self.update_text_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.checkbox.isEnabled() and not self.checkbox.isChecked():
                self.checkbox.setChecked(True)
            event.accept()
        else:
            super().mousePressEvent(event)

    def on_checkbox_toggle(self, checked):
        self.update_text_style()
        if checked:
            QTimer.singleShot(400, self.animate_completion)

    def animate_completion(self):
        # 1. Opacity fade out
        fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        fade_anim.setDuration(150)
        fade_anim.setStartValue(1.0)
        fade_anim.setEndValue(0.0)
        fade_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # 2. Height collapse
        height_anim = QPropertyAnimation(self, b"minimumHeight", self)
        height_anim.setDuration(180)
        height_anim.setStartValue(self._max_height)
        height_anim.setEndValue(0)
        height_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        height_anim2 = QPropertyAnimation(self, b"maximumHeight", self)
        height_anim2.setDuration(180)
        height_anim2.setStartValue(self._max_height)
        height_anim2.setEndValue(0)
        height_anim2.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        fade_anim.start()
        height_anim.start()
        height_anim2.start()
        
        # Emit completed signal when collapse finished
        height_anim.finished.connect(self.completed.emit)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Sub-layer visual rect: shifted upwards by self._hover_lift to avoid layout jitter
        card_rect = self.rect().adjusted(1, 1 - int(self._hover_lift), -1, -1 - int(self._hover_lift))
        
        # Paint Main Card base background (with glassy translucency!)
        bg_alpha = int(115 + 64 * (self._hover_lift / 3.0)) # ranges from 45% (115) to 70% (179)
        bg_color = QColor(theme.MAIN_CARD_COLOR)
        bg_color.setAlpha(bg_alpha)
        painter.setBrush(bg_color)
        
        # Paint glowing border on hover/checked
        border_color = QColor(theme.BORDER_COLOR)
        is_checked = self.checkbox.isChecked()
        target_color = self.color if (self._hover_lift > 0.1 or is_checked) else None
        
        if target_color is not None:
            factor = (self._hover_lift / 3.0) if self._hover_lift > 0.1 else self.checkbox._check_progress
            
            # Blend target_color slightly into border color
            r = border_color.red() + int((target_color.red() - border_color.red()) * factor * 0.3)
            g = border_color.green() + int((target_color.green() - border_color.green()) * factor * 0.3)
            b = border_color.blue() + int((target_color.blue() - border_color.blue()) * factor * 0.3)
            a = border_color.alpha() + int((70 - border_color.alpha()) * factor)
            border_color = QColor(r, g, b, a)
            
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(card_rect, 12, 12)


class TaskInputFieldCard(QWidget):
    task_added = Signal(str)
    cancelled = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TaskInputFieldCardContainer")
        self.setFixedHeight(42)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        self.checkbox_placeholder = QWidget(self)
        self.checkbox_placeholder.setFixedSize(20, 20)
        self.checkbox_placeholder.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                border: 1.5px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
            }}
        """)
        
        self.input_field = TaskInputField(self)
        self.input_field.setPlaceholderText("What needs to be done?")
        self.input_field.returnPressed.connect(self.submit_task)
        self.input_field.escape_pressed.connect(self.cancelled.emit)
        
        layout.addWidget(self.checkbox_placeholder)
        layout.addWidget(self.input_field)
        
        self.setStyleSheet(f"""
            QWidget#TaskInputFieldCardContainer {{
                background-color: transparent;
                border: 1px dashed rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }}
            QLineEdit#AddTaskInput {{
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: {theme.TASK_SIZE}px;
                font-weight: {theme.TASK_WEIGHT};
                background-color: transparent;
                border: none;
                padding: 0;
            }}
        """)
        
    def submit_task(self):
        text = self.input_field.text().strip()
        if text:
            self.task_added.emit(text)
        else:
            self.cancelled.emit()
