# ui/main_window.py
"""Main window layout and window behavior control."""

import ctypes
import sys
from PySide6.QtCore import Qt, QPoint, QEvent, QPropertyAnimation, QEasingCurve, Property, QTimer, QRectF, Signal, QByteArray, QSize
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy, QSpacerItem, QMenu, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor, QPixmap, QIcon

from styles import theme, qss
from utils import config
from widgets.clock import ClockWidget
from widgets.task_card import TaskCard, TaskInputFieldCard
from widgets.toolbar import FloatingToolbar, ToolbarButton
from widgets.notepad_widgets import NoteSquareWidget, MaximizedNoteWidget

LEFT_ARROW_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="m14.76 6.09-6.11 5.35c-.34.3-.34.83 0 1.13l6.11 5.35c.48.42 1.24.08 1.24-.56V6.65c0-.64-.76-.99-1.24-.56"></path></svg>"""

RIGHT_ARROW_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M8 6.65v10.69c0 .64.76.99 1.24.56l6.11-5.35c.34-.3.34-.83 0-1.13L9.24 6.07C8.76 5.65 8 5.99 8 6.63Z"></path></svg>"""

def adjust_brightness(hex_color, factor):
    """Adjust the brightness of a hex color (e.g. #4CC2FF) by a factor."""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    try:
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return f"#{hex_color}"

def parse_shortcut_string(shortcut_str):
    """Parse a shortcut string like 'Alt+T' to (modifiers, vk) for Windows RegisterHotKey."""
    if not shortcut_str:
        return 0, 0
    parts = [p.strip().lower() for p in shortcut_str.split('+')]
    modifiers = 0
    vk = 0
    
    # Modifiers: Alt=0x0001, Ctrl=0x0002, Shift=0x0004, Win=0x0008
    for p in parts:
        if p in ("alt", "option"):
            modifiers |= 0x0001
        elif p in ("ctrl", "control"):
            modifiers |= 0x0002
        elif p in ("shift",):
            modifiers |= 0x0004
        elif p in ("win", "cmd", "meta", "super"):
            modifiers |= 0x0008
        else:
            # Key code mapping
            if len(p) == 1:
                vk = ord(p.upper())
            elif p.startswith("f") and p[1:].isdigit():
                f_num = int(p[1:])
                vk = 0x70 + (f_num - 1) # VK_F1 is 0x70
            elif p == "space":
                vk = 0x20
            elif p == "enter" or p == "return":
                vk = 0x0D
            elif p == "escape" or p == "esc":
                vk = 0x1B
                
    return modifiers, vk


class AnimatedButton(QPushButton):
    """3D Styled Accent Button that simulates CSS translate on hover and click."""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.refresh_colors()

    def refresh_colors(self):
        """Call after accent color changes to sync the button style."""
        accent = theme.ACCENT_COLOR
        border_color = adjust_brightness(accent, 0.75)  # border-blue-600 (darker)
        hover_bg = adjust_brightness(accent, 1.1)       # hover:brightness-110
        hover_border = adjust_brightness(accent, 0.75)
        active_bg = adjust_brightness(accent, 0.9)      # active:brightness-90
        active_border = adjust_brightness(accent, 0.7)

        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {accent};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                border-bottom: 4px solid {border_color};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.5px;
                padding: 0px 16px;
                height: 28px;
                min-height: 28px;
                max-height: 28px;
                margin-top: 2px;
                margin-bottom: 4px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border-bottom: 6px solid {hover_border};
                margin-top: 0px;
                margin-bottom: 6px;
            }}
            QPushButton:pressed {{
                background-color: {active_bg};
                border-bottom: 2px solid {active_border};
                margin-top: 4px;
                margin-bottom: 2px;
            }}
            """
        )


class NewButtonContainer(QWidget):
    task_clicked = Signal()
    note_clicked = Signal()
    
    PLUS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="COLOR" viewBox="0 0 24 24">
    <path d="M3 13h8v8h2v-8h8v-2h-8V3h-2v8H3z"></path>
    </svg>"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded = False
        self.setFixedHeight(38)
        self.setMinimumWidth(38)
        self.setMaximumWidth(38)
        
        self.btn_task = QPushButton("Task", self)
        self.btn_task.setObjectName("NewActionSubButton")
        self.btn_task.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_task.setFixedSize(42, 30)
        self.btn_task.clicked.connect(self.on_task)
        self.btn_task.hide()
        
        self.btn_note = QPushButton("Note", self)
        self.btn_note.setObjectName("NewActionSubButton")
        self.btn_note.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_note.setFixedSize(42, 30)
        self.btn_note.clicked.connect(self.on_note)
        self.btn_note.hide()
        
        self.btn_new = QPushButton(self)
        self.btn_new.setObjectName("PlusToggleButton")
        self.btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new.setFixedSize(30, 30)
        self.btn_new.clicked.connect(self.toggle_expand)
        
        self.refresh_colors()
        
        self.width_anim = QPropertyAnimation(self, b"anim_width", self)
        self.width_anim.setDuration(250)
        self.width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    @Property(int)
    def anim_width(self):
        return self.width()
        
    @anim_width.setter
    def anim_width(self, w):
        self.setFixedWidth(w)
        if self.parent() and hasattr(self.parent(), "adjust_layout_height"):
            self.parent().adjust_layout_height()
            
    def update_icons(self):
        from PySide6.QtSvg import QSvgRenderer
        
        # Color of the plus icon inside the circle
        color_hex = "#FFFFFF"
        
        svg_str = self.PLUS_SVG.replace("COLOR", color_hex)
        renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
        pixmap = QPixmap(18, 18)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        self.btn_new.setIcon(QIcon(pixmap))
        self.btn_new.setIconSize(QSize(18, 18))
        
    def refresh_colors(self):
        self.update_icons()
        
        accent = theme.ACCENT_COLOR
        
        self.btn_new.setStyleSheet(f"""
            QPushButton#PlusToggleButton {{
                background-color: {accent};
                border: none;
                border-radius: 15px;
            }}
            QPushButton#PlusToggleButton:hover {{
                background-color: {adjust_brightness(accent, 1.15)};
            }}
        """)
        
        sub_btn_style = f"""
            QPushButton#NewActionSubButton {{
                background-color: transparent;
                color: {theme.TEXT_SECONDARY};
                border: none;
                border-radius: 6px;
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton#NewActionSubButton:hover {{
                background-color: {theme.HOVER_COLOR};
                color: {accent};
            }}
            QPushButton#NewActionSubButton:pressed {{
                background-color: rgba(255, 255, 255, 0.15);
                color: {accent};
            }}
        """
        self.btn_task.setStyleSheet(sub_btn_style)
        self.btn_note.setStyleSheet(sub_btn_style)
        self.update()
        
    def toggle_expand(self):
        self.width_anim.stop()
        
        if not self.expanded:
            self.btn_task.show()
            self.btn_note.show()
            self.width_anim.setStartValue(self.width())
            self.width_anim.setEndValue(134)
            self.expanded = True
        else:
            self.width_anim.setStartValue(self.width())
            self.width_anim.setEndValue(38)
            self.expanded = False
            self.width_anim.finished.connect(self.hide_sub_buttons)
            
        self.width_anim.start()
        
    def hide_sub_buttons(self):
        try:
            self.width_anim.finished.disconnect(self.hide_sub_buttons)
        except Exception:
            pass
        if not self.expanded:
            self.btn_task.hide()
            self.btn_note.hide()
            
    def collapse(self):
        if self.expanded:
            self.width_anim.stop()
            self.width_anim.setStartValue(self.width())
            self.width_anim.setEndValue(38)
            self.expanded = False
            self.width_anim.finished.connect(self.hide_sub_buttons)
            self.width_anim.start()
            
    def on_task(self):
        self.task_clicked.emit()
        self.collapse()
        
    def on_note(self):
        self.note_clicked.emit()
        self.collapse()
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.btn_new.setGeometry(self.width() - 34, 4, 30, 30)
        self.btn_task.setGeometry(4, 4, 42, 30)
        self.btn_note.setGeometry(52, 4, 42, 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        
        # Matches the static glassy background of toolbar
        sec_color = QColor(theme.SEC_CARD_COLOR)
        bg_color = QColor(sec_color.red(), sec_color.green(), sec_color.blue(), 152)
        border_color = QColor(255, 255, 255, 24)
        
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        
        # Capsule border radius is half of height (19px)
        painter.drawRoundedRect(rect, 19, 19)


class SpotifyMenuButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        
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
        
        bg_color = QColor(0, 0, 0, 180 if self._hovered else 130)
        painter.setBrush(bg_color)
        border_color = QColor(theme.ACCENT_COLOR) if self._hovered else QColor(theme.BORDER_COLOR)
        painter.setPen(QPen(border_color, 1.2))
        painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        
        icon_color = QColor(theme.ACCENT_COLOR) if self._hovered else QColor(theme.TEXT_PRIMARY)
        dots_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="{icon_color.name()}" viewBox="0 0 24 24"><path d="M5 3a2 2 0 1 0 0 4 2 2 0 1 0 0-4m7 0a2 2 0 1 0 0 4 2 2 0 1 0 0-4m7-.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 1 0 0-5m-14 7a2.5 2.5 0 1 0 0 5 2.5 2.5 0 1 0 0-5m7 .5a2 2 0 1 0 0 4 2 2 0 1 0 0-4m7 0a2 2 0 1 0 0 4 2 2 0 1 0 0-4M5 17a2 2 0 1 0 0 4 2 2 0 1 0 0-4m7 0a2 2 0 1 0 0 4 2 2 0 1 0 0-4m7.33-.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 1 0 0-5"></path></svg>"""
        
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtCore import QByteArray, QRectF
        renderer = QSvgRenderer(QByteArray(dots_svg.encode('utf-8')))
        renderer.render(painter, QRectF(6.0, 6.0, 16.0, 16.0))
class CelebrationOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.particles = []
        self.particle_timer = QTimer(self)
        self.particle_timer.setInterval(16)
        self.particle_timer.timeout.connect(self.update_particles)
        
    def spawn_particles(self, start_rect, color):
        import math
        import random
        from styles.theme import RAINBOW_COLORS
        
        # Spawn 20 particles distributed across the card's geometry
        for _ in range(20):
            p_color = QColor(random.choice(RAINBOW_COLORS) if RAINBOW_COLORS else color.name())
            
            # Start position spread across the card's geometry
            px = random.uniform(start_rect.x() + 10, start_rect.x() + start_rect.width() - 10)
            py = random.uniform(start_rect.y() + 5, start_rect.y() + start_rect.height() - 5)
            
            # Upward/outward drift velocity
            angle = random.uniform(-1.2 * math.pi, -0.2 * math.pi)
            speed = random.uniform(0.6, 2.2)
            shape = random.choice(['rect', 'ellipse'])
            
            self.particles.append({
                'x': px,
                'y': py,
                'dx': math.cos(angle) * speed,
                'dy': math.sin(angle) * speed,
                'color': p_color,
                'size': random.uniform(3.0, 6.0),
                'alpha': 255.0,
                'life': 1.0,
                'shape': shape
            })
            
        if not self.particle_timer.isActive():
            self.particle_timer.start()
            
    def update_particles(self):
        alive = False
        for p in self.particles:
            p['x'] += p['dx']
            p['y'] += p['dy']
            # Soft float gravity and drag
            p['dy'] += 0.04
            p['dx'] *= 0.98
            p['life'] -= 0.015 # slower decay (approx 1 second lifetime)
            if p['life'] < 0:
                p['life'] = 0
            p['alpha'] = p['life'] * 255.0
            if p['life'] > 0:
                alive = True
                
        if not alive:
            self.particle_timer.stop()
            self.particles = []
            
        self.update()
        
    def paintEvent(self, event):
        if not self.particles:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        for p in self.particles:
            color = QColor(p['color'])
            color.setAlpha(int(p['alpha']))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            if p['shape'] == 'ellipse':
                painter.drawEllipse(QRectF(p['x'] - p['size']/2.0, p['y'] - p['size']/2.0, p['size'], p['size']))
            else:
                painter.drawRect(QRectF(p['x'] - p['size']/2.0, p['y'] - p['size']/2.0, p['size'], p['size']))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # Set window icon
        from utils.icon import create_ticky_icon
        self.setWindowIcon(create_ticky_icon())
        
        # Set frameless and tool window flags from configuration
        always_on_top = config.load_always_on_top()
        stick_on_desktop = config.load_stick_on_desktop()
        if sys.platform == 'darwin':
            flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window
        else:
            flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool

        if stick_on_desktop:
            flags |= Qt.WindowType.WindowStaysOnBottomHint
        elif always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        if sys.platform == 'darwin':
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)
        
        self.tasks = config.load_tasks()
        self.notes = config.load_notes()
        self.maximized_note_idx = -1
        self.current_page = 0
        self.input_card = None
        self.focus_card = None
        self.widget_state = "normal"
        self.ball_widget = None
        
        # Window drag state variables
        self.drag_start_pos = QPoint()
        self.window_start_pos = QPoint()
        self.is_dragging_possible = False
        self.has_dragged = False
        
        # Inactivity auto-minimize timer
        self.inactivity_timer = QTimer(self)
        self.inactivity_timer.timeout.connect(self.minimize_to_ball)
        self.last_cursor_pos = QCursor.pos()
        
        # Celebration overlay for particle animations
        self.celebration_overlay = CelebrationOverlay(self)
        self.celebration_overlay.setGeometry(self.rect())
        self.celebration_overlay.raise_()
        
        self.init_ui()
        self.load_window_position()
        self.update_tasks_view()
        self.update_inactivity_timer_settings()
        self.register_global_hotkeys()
        
        # Spotify Mini Mode Menu Button
        self.spotify_menu_btn = SpotifyMenuButton(self)
        self.spotify_menu_btn.setObjectName("SpotifyMiniMenuButton")
        self.spotify_menu_btn.setToolTip("Ticky Menu")
        self.spotify_menu_btn.clicked.connect(self.show_spotify_mini_menu)
        self.spotify_menu_btn.hide()
        
        # Install global drag event filter
        QApplication.instance().installEventFilter(self)

    def init_ui(self):
        # Allow height to wrap contents dynamically, fixed width 360, minimum height 150
        self.setFixedWidth(360)
        self.setMinimumHeight(150)
        
        # Central container widget to apply style and rounded corners
        self.container = QWidget(self)
        self.container.setObjectName("MainWindowContainer")
        self.container.setFixedWidth(360)
        self.container.setMinimumHeight(150)
        
        # Enable dynamic size resizing on container and main window
        self.container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum)
        
        # Main layout inside the styled container
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(0)
        
        # 1. Clock Header Layout (Horizontal)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.clock_widget = ClockWidget(self)
        
        self.add_task_btn = NewButtonContainer(self)
        self.add_task_btn.task_clicked.connect(self.start_add_task)
        self.add_task_btn.note_clicked.connect(self.add_new_note)
        
        header_layout.addWidget(self.clock_widget)
        header_layout.addStretch()
        header_layout.addWidget(self.add_task_btn)
        layout.addLayout(header_layout)
        
        # Spacing before task list
        layout.addSpacing(10)
        
        # 3. Tasks Container
        self.tasks_layout = QVBoxLayout()
        self.tasks_layout.setContentsMargins(0, 0, 0, 0)
        self.tasks_layout.setSpacing(6)
        layout.addLayout(self.tasks_layout)
        
        # Spacing before pagination
        self.tasks_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        layout.addSpacerItem(self.tasks_spacer)
        
        # 4. Pagination Widget (above the toolbar)
        self.pagination_widget = QWidget(self)
        self.pagination_widget.setObjectName("PaginationWidget")
        self.pagination_widget.setFixedHeight(36)
        self.pagination_widget.setStyleSheet(qss.get_pagination_style())
        
        pag_layout = QHBoxLayout(self.pagination_widget)
        pag_layout.setContentsMargins(0, 0, 0, 0)
        pag_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.prev_btn = ToolbarButton(LEFT_ARROW_SVG, "Previous Page", self.pagination_widget)
        self.prev_btn.clicked.connect(self.prev_page)
        
        self.page_label = QLabel("1 / 1", self.pagination_widget)
        self.page_label.setObjectName("PageIndicator")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.next_btn = ToolbarButton(RIGHT_ARROW_SVG, "Next Page", self.pagination_widget)
        self.next_btn.clicked.connect(self.next_page)
        
        pag_layout.addWidget(self.prev_btn)
        pag_layout.addSpacing(10)
        pag_layout.addWidget(self.page_label)
        pag_layout.addSpacing(10)
        pag_layout.addWidget(self.next_btn)
        
        layout.addWidget(self.pagination_widget)
        self.pagination_widget.hide()
        
        # Spacing before toolbar
        layout.addSpacing(10)
        
        # 5. Bottom Toolbar Layout (Floating Capsule aligned to Right)
        toolbar_container = QHBoxLayout()
        toolbar_container.setContentsMargins(0, 0, 0, 0)
        toolbar_container.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.toolbar = FloatingToolbar(self)
        self.toolbar.settings_clicked.connect(self.show_settings_menu)
        self.toolbar.music_clicked.connect(self.handle_spotify_button_click)
        self.toolbar.ai_clicked.connect(self.handle_ai_button_click)
        toolbar_container.addWidget(self.toolbar)
        layout.addLayout(toolbar_container)

        # Spotify collapsible panel (placed below the toolbar)
        from widgets.spotify_panel import SpotifyPanel
        self.spotify_panel = SpotifyPanel(self)
        layout.addWidget(self.spotify_panel)
        
        # AI collapsible panel (placed below the toolbar)
        from widgets.ai_panel import AIPanel
        self.ai_panel = AIPanel(self)
        layout.addWidget(self.ai_panel)
        
        # Outer layout of Main Window to place container centered
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetFixedSize)
        outer_layout.addWidget(self.container)
        
        self.container.setStyleSheet(qss.get_main_style())

    def start_add_task(self):
        if self.input_card is not None:
            return
        
        # Switch to first page when adding a task to make sure they see it
        self.current_page = 0
        self.update_tasks_view()
        
        # Instantiate and prepend the input card in the layout
        self.input_card = TaskInputFieldCard(self)
        self.input_card.task_added.connect(self.on_task_added)
        self.input_card.cancelled.connect(self.on_add_task_cancelled)
        
        self.tasks_layout.insertWidget(0, self.input_card)
        self.input_card.animate_show()
        self.input_card.input_field.setFocus()

    def on_task_added(self, text):
        if self.input_card is None:
            return
        
        self.tasks.insert(0, text)
        config.save_tasks(self.tasks)
        
        card = self.input_card
        self.input_card = None
        
        def finish():
            if card is not None:
                self.tasks_layout.removeWidget(card)
                card.deleteLater()
            self.update_tasks_view()
            
        card.animate_hide(finish)

    def on_add_task_cancelled(self):
        if self.input_card is None:
            return
            
        card = self.input_card
        self.input_card = None
        
        def finish():
            if card is not None:
                self.tasks_layout.removeWidget(card)
                card.deleteLater()
            self.update_tasks_view()
            
        card.animate_hide(finish)

    def mark_task_completed(self, text):
        if text in self.tasks:
            self.tasks.remove(text)
            config.save_tasks(self.tasks)

    def complete_task(self, text):
        self.mark_task_completed(text)
        self.update_tasks_view()

    def update_tasks_view(self):
        self.focus_card = None
        
        # If a note is maximized, we hide the header add task button
        if self.maximized_note_idx != -1:
            self.add_task_btn.hide()
            self.pagination_widget.hide()
        else:
            if self.widget_state == "normal":
                self.add_task_btn.show()
            else:
                self.add_task_btn.hide()
            
        # 1. Clear existing task card widgets and nested layouts from tasks_layout (keeping input_card)
        i = 0
        while i < self.tasks_layout.count():
            item = self.tasks_layout.itemAt(i)
            if item.widget() == self.input_card and self.input_card is not None:
                i += 1
                continue
                
            item = self.tasks_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                lay = item.layout()
                while lay.count() > 0:
                    child_item = lay.takeAt(0)
                    if child_item.widget():
                        child_item.widget().deleteLater()
                lay.deleteLater()

        # Check if a note is maximized
        if self.maximized_note_idx != -1:
            note_text = self.notes[self.maximized_note_idx]
            from styles.theme import RAINBOW_COLORS
            color_hex = RAINBOW_COLORS[self.maximized_note_idx % len(RAINBOW_COLORS)]
            
            editor = MaximizedNoteWidget(self.maximized_note_idx, note_text, color_hex, self)
            editor.back_clicked.connect(self.save_and_close_note)
            self.tasks_layout.addWidget(editor)
            editor.animate_show()
            editor.show_fade.finished.connect(self.unlock_window_height)
            self.adjustSize()
            return

        total_tasks = len(self.tasks)

        # 2. Render tasks and notes
        if len(self.notes) > 0:
            # Hybrid Layout: 1 task card at the top, 2 side-by-side squares at the bottom
            total_pages = max(1, total_tasks, (len(self.notes) + 1) // 2)
            if self.current_page >= total_pages:
                self.current_page = max(0, total_pages - 1)
                
            # Render top task (if any exists on this page)
            if self.current_page < len(self.tasks):
                text = self.tasks[self.current_page]
                from styles.theme import RAINBOW_COLORS
                color_hex = RAINBOW_COLORS[self.current_page % len(RAINBOW_COLORS)]
                card = TaskCard(text, color_hex, self)
                card.task_checked.connect(lambda t=text: self.mark_task_completed(t))
                card.completed.connect(self.update_tasks_view)
                card.focus_toggled.connect(lambda active, c=card: self.handle_task_focus_toggle(c, active))
                if self.widget_state != "normal":
                    card.hide()
                    
                if self.input_card is not None:
                    self.tasks_layout.insertWidget(self.tasks_layout.count(), card)
                else:
                    self.tasks_layout.addWidget(card)
                    
            # Render bottom squares (Notes) for the current page
            squares_layout = QHBoxLayout()
            squares_layout.setContentsMargins(0, 6, 0, 0)
            squares_layout.setSpacing(6)
            
            from styles.theme import RAINBOW_COLORS
            start_note_idx = self.current_page * 2
            page_notes = self.notes[start_note_idx : start_note_idx + 2]
            
            # Note Square 1
            if len(page_notes) >= 1:
                note_idx = start_note_idx + 0
                color_hex = RAINBOW_COLORS[note_idx % len(RAINBOW_COLORS)]
                sq1 = NoteSquareWidget(note_idx, page_notes[0], color_hex, self)
                sq1.clicked.connect(self.maximize_note)
                if self.widget_state != "normal":
                    sq1.hide()
                squares_layout.addWidget(sq1)
            else:
                # Blank spacer widget
                dummy1 = QWidget(self)
                dummy1.setFixedSize(157, 90)
                dummy1.setStyleSheet("background: transparent; border: none;")
                squares_layout.addWidget(dummy1)
                
            # Note Square 2
            if len(page_notes) >= 2:
                note_idx = start_note_idx + 1
                color_hex = RAINBOW_COLORS[note_idx % len(RAINBOW_COLORS)]
                sq2 = NoteSquareWidget(note_idx, page_notes[1], color_hex, self)
                sq2.clicked.connect(self.maximize_note)
                if self.widget_state != "normal":
                    sq2.hide()
                squares_layout.addWidget(sq2)
            else:
                # Blank spacer widget
                dummy2 = QWidget(self)
                dummy2.setFixedSize(157, 90)
                dummy2.setStyleSheet("background: transparent; border: none;")
                squares_layout.addWidget(dummy2)
                
            self.tasks_layout.addLayout(squares_layout)
        else:
            # Standard Layout: Up to 3 task cards vertically
            total_pages = max(1, (total_tasks + 2) // 3)
            if self.current_page >= total_pages:
                self.current_page = max(0, total_pages - 1)
                
            start_idx = self.current_page * 3
            end_idx = start_idx + 3
            page_tasks = self.tasks[start_idx:end_idx]
            
            for idx, text in enumerate(page_tasks):
                global_idx = start_idx + idx
                from styles.theme import RAINBOW_COLORS
                color_hex = RAINBOW_COLORS[global_idx % len(RAINBOW_COLORS)]
                card = TaskCard(text, color_hex, self)
                card.task_checked.connect(lambda t=text: self.mark_task_completed(t))
                card.completed.connect(self.update_tasks_view)
                card.focus_toggled.connect(lambda active, c=card: self.handle_task_focus_toggle(c, active))
                if self.widget_state != "normal":
                    card.hide()
                if self.input_card is not None:
                    self.tasks_layout.insertWidget(self.tasks_layout.count(), card)
                else:
                    self.tasks_layout.addWidget(card)
                    
        # 3. Update pagination visibility and text
        show_pagination = False
        if self.widget_state == "normal":
            show_pagination = total_pages > 1
                
        if show_pagination:
            self.pagination_widget.show()
            self.page_label.setText(f"{self.current_page + 1} / {total_pages}")
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)
        else:
            self.pagination_widget.hide()
            
        # 4. Trigger height adjust updates
        self.adjustSize()

    def handle_task_focus_toggle(self, card, start_focus):
        if start_focus:
            self.focus_card = card
            card.set_focus_active(True)
            self.add_task_btn.hide()
            self.pagination_widget.hide()
            for i in range(self.tasks_layout.count()):
                item = self.tasks_layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if w != self.focus_card:
                        w.hide()
            if hasattr(self, 'toolbar') and self.toolbar:
                self.toolbar.start_stopwatch_for_task()
        else:
            if hasattr(self, 'toolbar') and self.toolbar:
                self.toolbar.stop_stopwatch()
            card.checkbox.setChecked(True)

    def on_stopwatch_stopped(self):
        if self.focus_card:
            card = self.focus_card
            card.set_focus_active(False)
            self.focus_card = None
            card.checkbox.setChecked(True)

    def on_pomodoro_finished(self):
        print("Pomodoro timer finished!", file=sys.stderr)
        sys.stderr.flush()
        try:
            import winsound
            winsound.MessageBeep()
        except Exception:
            pass

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_tasks_view()

    def next_page(self):
        total_tasks = len(self.tasks)
        if len(self.notes) > 0:
            total_pages = max(1, total_tasks, (len(self.notes) + 1) // 2)
        else:
            total_pages = max(1, (total_tasks + 2) // 3)
            
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_tasks_view()

    def maximize_note(self, index):
        self.setFixedHeight(self.height())
        def on_fade_done():
            self.maximized_note_idx = index
            self.update_tasks_view()
        self.fade_out_layout_widgets(on_fade_done)
        
    def add_new_note(self):
        self.setFixedHeight(self.height())
        self.notes.append("New Note")
        config.save_notes(self.notes)
        
        def on_fade_done():
            self.maximized_note_idx = len(self.notes) - 1
            self.current_page = self.maximized_note_idx // 2
            self.update_tasks_view()
        self.fade_out_layout_widgets(on_fade_done)
        
    def save_and_close_note(self, index, new_text):
        if len(new_text.strip()) == 0:
            # Delete note if cleared
            self.notes.pop(index)
        else:
            self.notes[index] = new_text
        config.save_notes(self.notes)
        self.maximized_note_idx = -1
        
        # Adjust page index if the last page became empty
        if len(self.notes) > 0:
            max_page = (len(self.notes) - 1) // 2
            self.current_page = min(self.current_page, max_page)
        else:
            self.current_page = 0
            
        self.setFixedHeight(self.height())
        self.update_tasks_view()
        self.fade_in_layout_widgets()

    def add_task_from_ai(self, task_title, due_date=None, priority=None):
        """Programmatically add a task from AI intent detection."""
        if not task_title or not task_title.strip():
            return ""
        
        full_title = task_title.strip()
        meta_parts = []
        if due_date and due_date.strip():
            meta_parts.append(due_date.strip())
        if priority and priority.strip():
            meta_parts.append(priority.strip().capitalize())
        if meta_parts:
            full_title += f" ({', '.join(meta_parts)})"

        if full_title not in self.tasks:
            self.tasks.insert(0, full_title)
            config.save_tasks(self.tasks)
            self.current_page = 0
            self.update_tasks_view()
        return full_title

    def add_note_from_ai(self, content, title=None):
        """Programmatically add a note from AI intent detection."""
        content_str = content.strip() if content else ""
        title_str = title.strip() if title else ""
        
        if title_str and content_str:
            if not content_str.lower().startswith(title_str.lower()):
                note_text = f"{title_str}\n{content_str}"
            else:
                note_text = content_str
        elif content_str:
            note_text = content_str
        elif title_str:
            note_text = title_str
        else:
            return ""

        if note_text not in self.notes:
            self.notes.insert(0, note_text)
            config.save_notes(self.notes)
            self.update_tasks_view()
        return note_text

    def start_task_by_title(self, task_title):
        """Find a task card matching title and trigger focus session mode."""
        if not task_title or not self.tasks:
            return False

        clean_target = task_title.strip().lower()
        target_idx = -1

        # Search for exact or substring match in tasks list
        for idx, t in enumerate(self.tasks):
            if clean_target in t.lower() or t.lower() in clean_target:
                target_idx = idx
                break

        if target_idx == -1:
            target_idx = 0  # Fallback to top task

        # Calculate page index for standard/hybrid views
        if len(self.notes) > 0:
            self.current_page = min(target_idx, len(self.tasks) - 1)
        else:
            self.current_page = target_idx // 3

        self.update_tasks_view()

        # Find TaskCard widget and activate focus
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TaskCard):
                card = item.widget()
                card_text = card.text_label.text().lower()
                if clean_target in card_text or card_text in clean_target:
                    self.handle_task_focus_toggle(card, True)
                    return True

        # Fallback to first TaskCard found
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), TaskCard):
                card = item.widget()
                self.handle_task_focus_toggle(card, True)
                return True

        return False

    def unlock_window_height(self):
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.adjustSize()

    def fade_out_layout_widgets(self, callback):
        widgets = []
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item.widget() and item.widget() != self.input_card:
                widgets.append(item.widget())
            elif item.layout():
                lay = item.layout()
                for j in range(lay.count()):
                    child_item = lay.itemAt(j)
                    if child_item.widget():
                        widgets.append(child_item.widget())
                        
        if not widgets:
            callback()
            return
            
        self._transition_anims = []
        self._transition_effects = []
        
        finished_count = [0]
        def on_finished():
            finished_count[0] += 1
            if finished_count[0] == len(widgets):
                for w, eff in zip(widgets, self._transition_effects):
                    try:
                        w.setGraphicsEffect(None)
                    except Exception:
                        pass
                self._transition_anims.clear()
                self._transition_effects.clear()
                callback()
                
        for w in widgets:
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
            self._transition_effects.append(eff)
            
            anim = QPropertyAnimation(eff, b"opacity", w)
            anim.setDuration(120)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.finished.connect(on_finished)
            self._transition_anims.append(anim)
            anim.start()

    def fade_in_layout_widgets(self):
        widgets = []
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item.widget() and item.widget() != self.input_card:
                widgets.append(item.widget())
            elif item.layout():
                lay = item.layout()
                for j in range(lay.count()):
                    child_item = lay.itemAt(j)
                    if child_item.widget():
                        widgets.append(child_item.widget())
                        
        if not widgets:
            self.unlock_window_height()
            return
            
        self._transition_anims = []
        self._transition_effects = []
        
        finished_count = [0]
        def on_finished():
            finished_count[0] += 1
            if finished_count[0] == len(widgets):
                for w, eff in zip(widgets, self._transition_effects):
                    try:
                        w.setGraphicsEffect(None)
                    except Exception:
                        pass
                self._transition_anims.clear()
                self._transition_effects.clear()
                self.unlock_window_height()
                
        for w in widgets:
            eff = QGraphicsOpacityEffect(w)
            eff.setOpacity(0.0)
            w.setGraphicsEffect(eff)
            self._transition_effects.append(eff)
            
            anim = QPropertyAnimation(eff, b"opacity", w)
            anim.setDuration(150)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            anim.finished.connect(on_finished)
            self._transition_anims.append(anim)
            anim.start()

    def update_inactivity_timer_settings(self):
        enabled = config.load_minimize_on_idle()
        minutes = config.load_idle_minutes()
        aot = config.load_always_on_top()
        
        print(f"Inactivity timer settings updated: enabled={enabled}, minutes={minutes}, aot={aot}", file=sys.stderr)
        if enabled and aot:
            self.inactivity_timer.setInterval(minutes * 60 * 1000)
            self.inactivity_timer.start()
            print("Inactivity timer started/restarted.", file=sys.stderr)
        else:
            self.inactivity_timer.stop()
            print("Inactivity timer stopped.", file=sys.stderr)
        sys.stderr.flush()

    def minimize_to_ball(self):
        # Prevent automatic idle minimize if a task is active or timer/stopwatch is running
        if self.sender() == self.inactivity_timer:
            has_active_task = self.focus_card is not None
            has_running_timer = hasattr(self, 'toolbar') and self.toolbar and self.toolbar.is_timer_running
            if has_active_task or has_running_timer:
                print("Task or Timer is active, skipping auto-minimize to ball.", file=sys.stderr)
                sys.stderr.flush()
                self.inactivity_timer.start()
                return

        print("Inactivity timeout reached! Minimizing to ball.", file=sys.stderr)
        sys.stderr.flush()
        self.inactivity_timer.stop()
        self.widget_state = "minimized_ball"
        
        if hasattr(self, 'settings_window') and self.settings_window:
            self.settings_window.hide()
            
        self.hide()
        
        from widgets.ball_widget import BallWidget
        if not self.ball_widget:
            self.ball_widget = BallWidget(self)
            
        geom = self.geometry()
        cx = geom.x() + (geom.width() - 40) // 2
        cy = geom.y() + (geom.height() - 40) // 2
        self.ball_widget.move(cx, cy)
        self.ball_widget.show()

    def restore_from_ball(self):
        self.widget_state = "normal"
        
        if self.ball_widget:
            self.ball_widget.hide()
            
        # Restore original layout margins, spacing, and width
        if hasattr(self, '_orig_margins'):
            self.container.layout().setContentsMargins(*self._orig_margins)
            self.container.layout().setSpacing(self._orig_spacing)
        self.setFixedWidth(360)
        self.container.setFixedWidth(360)
        
        self.container.show()
        self.clock_widget.show()
        self.add_task_btn.show()
        if len(self.tasks) > 3:
            self.pagination_widget.show()
        else:
            self.pagination_widget.hide()
        self.toolbar.show()
        
        if hasattr(self, 'spotify_panel'):
            self.spotify_panel.set_mini_mode(False)
            self.spotify_panel.hide()
            self.spotify_panel.is_expanded = False
            self.spotify_panel.setFixedHeight(0)
            self.spotify_panel.timeline_timer.stop()
            self.spotify_panel.poll_timer.stop()
            
        if hasattr(self, 'ai_panel'):
            self.ai_panel.hide()
            self.ai_panel.is_expanded = False
            self.ai_panel.setFixedHeight(0)
            
        self.toolbar.btn_music.setActive(False)
        self.toolbar.btn_ai.setActive(False)
        self.spotify_menu_btn.hide()
        
        self.show()
        self.update_tasks_view()
        self.adjust_layout_height()
        self.update_inactivity_timer_settings()

    def enter_spotify_mini_mode(self):
        self.inactivity_timer.stop()
        self.widget_state = "minimized_spotify"
        
        if self.ball_widget:
            self.ball_widget.hide()
            
        self.clock_widget.hide()
        self.add_task_btn.hide()
        self.pagination_widget.hide()
        self.toolbar.hide()
        
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget():
                item.widget().hide()
                
        # Setup compact dimensions and layout - set width to 360px
        self.setFixedWidth(360)
        self.container.setFixedWidth(360)
        
        # Save original layout margins
        m = self.container.layout().contentsMargins()
        self._orig_margins = (m.left(), m.top(), m.right(), m.bottom())
        self._orig_spacing = self.container.layout().spacing()
        
        # Remove layouts margins and spacing
        self.container.layout().setContentsMargins(0, 0, 0, 0)
        self.container.layout().setSpacing(0)
        
        if hasattr(self, 'ai_panel'):
            self.ai_panel.hide()
            self.ai_panel.is_expanded = False
            self.ai_panel.setFixedHeight(0)
        
        self.spotify_panel.set_mini_mode(True)
        self.spotify_panel.show()
        self.spotify_panel.is_expanded = True
        self.spotify_panel.setFixedHeight(114) # Card height + top/bottom spacing (114px)
        
        # Start updates
        self.spotify_panel.update_playback()
        self.spotify_panel.timeline_timer.start()
        if not config.load_spotify_demo_mode():
            self.spotify_panel.poll_timer.start()
            
        # Position menu button in top-left of vinyl cover
        self.spotify_menu_btn.setParent(self)
        self.spotify_menu_btn.move(24, 24)
        self.spotify_menu_btn.show()
        self.spotify_menu_btn.raise_()
        
        self.show()
        self.adjust_layout_height()

    def restore_from_spotify_mini(self):
        self.spotify_menu_btn.hide()
        self.restore_from_ball()

    def minimize_to_ball_from_spotify(self):
        self.spotify_menu_btn.hide()
        self.minimize_to_ball()

    def show_spotify_mini_menu(self):
        menu = QMenu(self)
        
        expand_action = menu.addAction("Expand Ticky")
        spotify_action = menu.addAction("Spotify Player")
        settings_action = menu.addAction("Settings")
        
        expand_action.triggered.connect(self.restore_from_spotify_mini)
        spotify_action.triggered.connect(self.minimize_to_ball_from_spotify)
        settings_action.triggered.connect(self.show_settings_menu)
        
        btn_geom = self.spotify_menu_btn.geometry()
        pos = self.mapToGlobal(QPoint(btn_geom.x(), btn_geom.y() + btn_geom.height() + 4))
        menu.exec(pos)

    def is_drag_allowed(self, obj):
        # If position is pinned/locked or sticking on desktop is active, dragging is disabled
        from styles import theme
        if getattr(theme, 'PIN_POSITION', False) or getattr(theme, 'STICK_ON_DESKTOP', False):
            return False
            
        # Do not allow drag starting from the toolbar, add task button, pagination, or task cards
        if hasattr(self, 'toolbar') and self.toolbar and (obj == self.toolbar or self.toolbar.isAncestorOf(obj)):
            return False
        if hasattr(self, 'add_task_btn') and self.add_task_btn and obj == self.add_task_btn:
            return False
        if hasattr(self, 'pagination_widget') and self.pagination_widget and (obj == self.pagination_widget or self.pagination_widget.isAncestorOf(obj)):
            return False
        if hasattr(self, 'ai_panel') and self.ai_panel and (obj == self.ai_panel or self.ai_panel.isAncestorOf(obj)):
            return False
        if hasattr(self, 'spotify_panel') and self.spotify_panel and (obj == self.spotify_panel or self.spotify_panel.isAncestorOf(obj)):
            return False
        if hasattr(self, 'tasks_layout') and self.tasks_layout:
            for i in range(self.tasks_layout.count()):
                item = self.tasks_layout.itemAt(i)
                if item and item.widget():
                    w = item.widget()
                    if w == obj or w.isAncestorOf(obj):
                        return False
        return True

    # Global drag event filter implementation
    def eventFilter(self, obj, event):
        # Reset inactivity timer on user interaction anywhere
        if event.type() == QEvent.Type.MouseMove:
            current_pos = QCursor.pos()
            if current_pos != self.last_cursor_pos:
                self.last_cursor_pos = current_pos
                if self.widget_state == "normal" and self.inactivity_timer.isActive():
                    self.inactivity_timer.start()
                    # print("Timer reset (mouse move)", file=sys.stderr); sys.stderr.flush()
        elif event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease, QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            if self.widget_state == "normal" and self.inactivity_timer.isActive():
                self.inactivity_timer.start()
                # print("Timer reset (click/key)", file=sys.stderr); sys.stderr.flush()

        if isinstance(obj, QWidget) and (obj == self or self.isAncestorOf(obj)):
            if event.type() == QEvent.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    if self.is_drag_allowed(obj):
                        self.drag_start_pos = event.globalPosition().toPoint()
                        self.window_start_pos = self.pos()
                        self.is_dragging_possible = True
                        self.has_dragged = False
                    else:
                        self.is_dragging_possible = False
                        
            elif event.type() == QEvent.Type.MouseMove:
                if event.buttons() == Qt.MouseButton.LeftButton and getattr(self, 'is_dragging_possible', False):
                    delta = event.globalPosition().toPoint() - self.drag_start_pos
                    if self.has_dragged or delta.manhattanLength() > 5:
                        self.has_dragged = True
                        self.move(self.window_start_pos + delta)
                        return True
                        
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.is_dragging_possible = False
                    if getattr(self, 'has_dragged', False):
                        self.has_dragged = False
                        self.save_window_position()
                        return True
                        
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        if hasattr(self, 'celebration_overlay') and self.celebration_overlay:
            self.celebration_overlay.setGeometry(self.rect())
            self.celebration_overlay.raise_()
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.unregister_global_hotkeys()
        # When closing the window, hide it instead of quitting (system tray stays active)
        event.ignore()
        self.hide()

    # Window position memory loaders
    def load_window_position(self):
        screen_geom = QApplication.primaryScreen().geometry()
        # Default position: bottom right corner of desktop
        default_x = screen_geom.width() - self.width() - 40
        default_y = screen_geom.height() - self.height() - 80
        
        x, y = config.load_position(default_x, default_y)
        # Ensure it fits on screen bounds
        x = max(0, min(x, screen_geom.width() - self.width()))
        y = max(0, min(y, screen_geom.height() - self.height()))
        self.move(x, y)

    def save_window_position(self):
        pos = self.pos()
        config.save_position(pos.x(), pos.y())

    # Native class drop-shadow configuration
    def showEvent(self, event):
        super().showEvent(event)
        hwnd = self.winId()
        try:
            user32 = ctypes.windll.user32
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                get_class_long = user32.GetClassLongPtrW
                set_class_long = user32.SetClassLongPtrW
            else:
                get_class_long = user32.GetClassLongW
                set_class_long = user32.SetClassLongW
                
            class_style = get_class_long(hwnd, -26) # GCL_STYLE is -26
            class_style |= 0x00020000              # CS_DROPSHADOW
            set_class_long(hwnd, -26, class_style)
        except Exception:
            pass

    # Floating settings window display
    def show_settings_menu(self):
        from ui.settings_window import SettingsWindow
        if not hasattr(self, 'settings_window') or self.settings_window is None:
            self.settings_window = SettingsWindow(self)
        self.settings_window.show_centered()
        if hasattr(self, 'toolbar') and self.toolbar:
            self.toolbar.btn_settings.setActive(True)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == 'darwin':
            from utils.mac_window import configure_mac_window
            configure_mac_window(self.winId(), config.load_always_on_top())

    def set_stick_on_desktop(self, enabled):
        # Save current position to prevent position resetting on Windows
        curr_pos = self.pos()
        
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnBottomHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnBottomHint
            
        is_visible = self.isVisible()
        if sys.platform == 'darwin':
            self.hide()
            
        self.setWindowFlags(flags)
        self.move(curr_pos)
        
        if is_visible:
            self.show()

        if sys.platform == 'darwin':
            from utils.mac_window import configure_mac_window
            configure_mac_window(self.winId(), not enabled and config.load_always_on_top())

    def set_always_on_top(self, enabled):
        # Save current position to prevent position resetting on Windows
        curr_pos = self.pos()
        
        flags = self.windowFlags()
        if enabled:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~Qt.WindowType.WindowStaysOnTopHint
            
        is_visible = self.isVisible()
        if sys.platform == 'darwin':
            self.hide()
            
        self.setWindowFlags(flags)
        self.move(curr_pos)
        
        if is_visible:
            self.show()

        if sys.platform == 'darwin':
            from utils.mac_window import configure_mac_window
            configure_mac_window(self.winId(), enabled)

    def refresh_theme(self):
        # Refresh global application stylesheet for tooltips and menus
        app = QApplication.instance()
        if app:
            app.setStyleSheet(f"""
                QToolTip {{
                    background-color: {theme.MAIN_CARD_COLOR};
                    color: {theme.TEXT_PRIMARY};
                    border: 1px solid {theme.BORDER_COLOR};
                    border-radius: 6px;
                    font-family: {theme.FONT_FAMILY};
                    font-size: 10px;
                    padding: 3px 6px;
                }}
                QMenu {{
                    background-color: {theme.MAIN_CARD_COLOR};
                    color: {theme.TEXT_PRIMARY};
                    border: 1px solid {theme.BORDER_COLOR};
                    border-radius: 8px;
                    padding: 4px 0px;
                    font-family: {theme.FONT_FAMILY};
                    font-size: 11px;
                }}
                QMenu::item {{
                    background-color: transparent;
                    padding: 6px 20px;
                    border-radius: 4px;
                    margin: 2px 4px;
                }}
                QMenu::item:selected {{
                    background-color: {theme.HOVER_COLOR};
                    color: {theme.ACCENT_COLOR};
                }}
                QMenu::separator {{
                    height: 1px;
                    background-color: {theme.BORDER_COLOR};
                    margin: 4px 0px;
                }}
            """)

        # Re-apply stylesheets
        self.container.setStyleSheet(qss.get_main_style())
        self.clock_widget.setStyleSheet(qss.get_clock_style())
        self.add_task_btn.refresh_colors()  # AnimatedButton syncs to new accent color
        self.pagination_widget.setStyleSheet(qss.get_pagination_style())
        self.toolbar.setStyleSheet(qss.get_toolbar_style())
        
        if hasattr(self, 'spotify_panel') and self.spotify_panel:
            self.spotify_panel.refresh_styles()
        
        if hasattr(self, 'ai_panel') and self.ai_panel:
            self.ai_panel.refresh_styles()
        
        # Helper to refresh widget style if applicable
        def refresh_widget_theme(w):
            if hasattr(w, 'update_text_style'):
                w.setStyleSheet(qss.get_task_card_style())
                w.update_text_style()
            elif hasattr(w, 'update_style'):
                w.update_style()
                if hasattr(w, 'update_icons'):
                    w.update_icons()

        # Re-apply styles of currently visible widgets and sub-layouts
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item:
                if item.widget():
                    refresh_widget_theme(item.widget())
                elif item.layout():
                    lay = item.layout()
                    for j in range(lay.count()):
                        child_item = lay.itemAt(j)
                        if child_item and child_item.widget():
                            refresh_widget_theme(child_item.widget())
                    
        # Trigger clock time update to format clock immediately
        self.clock_widget.update_time()
        self.adjust_layout_height()
        self.update()

    def adjust_layout_height(self):
        """Force layout recalculation during height animation steps."""
        self.container.adjustSize()
        self.adjustSize()

    def handle_spotify_button_click(self):
        """Callback when the Spotify music icon is clicked in the toolbar."""
        from utils import config
        client_id, client_secret = config.load_spotify_credentials()
        is_linked = bool(client_id and client_secret) or config.load_spotify_demo_mode()
        
        if not is_linked:
            # Open settings and switch to Spotify category
            if not hasattr(self, 'settings_window') or self.settings_window is None:
                from ui.settings_window import SettingsWindow
                self.settings_window = SettingsWindow(self)
            self.settings_window.show_centered()
            self.settings_window.switch_page(4)
        else:
            # Collapse AI if it is expanded
            if hasattr(self, 'ai_panel') and self.ai_panel.is_expanded:
                self.ai_panel.collapse()
            # Expand/collapse Spotify panel height
            self.spotify_panel.toggle()
            
    def handle_ai_button_click(self):
        """Callback when the AI Sparks icon is clicked in the toolbar."""
        from utils import config
        api_key = config.load_ai_api_key()
        
        if not api_key:
            # Open settings and switch to AI category
            if not hasattr(self, 'settings_window') or self.settings_window is None:
                from ui.settings_window import SettingsWindow
                self.settings_window = SettingsWindow(self)
            self.settings_window.show_centered()
            self.settings_window.switch_page(5)
        else:
            # Collapse Spotify if it is expanded
            if hasattr(self, 'spotify_panel') and self.spotify_panel.is_expanded:
                self.spotify_panel.toggle()
            # Expand/collapse AI panel height
            self.ai_panel.toggle()

    def register_global_hotkeys(self):
        self.unregister_global_hotkeys()
        
        self.registered_hotkeys = {}
        import sys
        if sys.platform != 'win32':
            return
            
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = int(self.winId())
        
        # Load custom shortcuts from config
        from utils import config
        self.shortcuts = config.load_shortcuts()
        
        # 1. Toggle Window Shortcut
        t_mods, t_vk = parse_shortcut_string(self.shortcuts.get("toggle_window", "Alt+T"))
        if t_vk:
            if user32.RegisterHotKey(hwnd, 1, t_mods, t_vk):
                self.registered_hotkeys[1] = "toggle_window"
                
        # 2. New Task Shortcut
        n_mods, n_vk = parse_shortcut_string(self.shortcuts.get("new_task", "Alt+Q"))
        if n_vk:
            if user32.RegisterHotKey(hwnd, 2, n_mods, n_vk):
                self.registered_hotkeys[2] = "new_task"

    def unregister_global_hotkeys(self):
        import sys
        if sys.platform != 'win32':
            return
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = int(self.winId())
        if hasattr(self, 'registered_hotkeys'):
            for hid in list(self.registered_hotkeys.keys()):
                user32.UnregisterHotKey(hwnd, hid)
            self.registered_hotkeys = {}

    def handle_global_hotkey(self, action):
        if action == "toggle_window":
            if self.widget_state == "minimized_ball":
                self.restore_from_ball()
                self.activateWindow()
            else:
                if self.isVisible() and self.isActiveWindow():
                    self.minimize_to_ball()
                else:
                    self.show()
                    self.restore_from_ball()
                    self.activateWindow()
        elif action == "new_task":
            if self.widget_state == "minimized_ball":
                self.restore_from_ball()
            self.show()
            self.restore_from_ball() # Ensure fully restored
            self.activateWindow()
            self.start_add_task()

    def nativeEvent(self, eventType, message):
        import sys
        if sys.platform == 'win32' and eventType == b"windows_generic_MSG":
            import ctypes
            from ctypes import wintypes
            
            class MSG(ctypes.Structure):
                _fields_ = [
                    ("hwnd", wintypes.HWND),
                    ("message", wintypes.UINT),
                    ("wParam", wintypes.WPARAM),
                    ("lParam", wintypes.LPARAM),
                    ("time", wintypes.DWORD),
                    ("pt", wintypes.POINT),
                ]
                
            msg = MSG.from_address(int(message))
            if msg.message == 0x0312: # WM_HOTKEY
                hotkey_id = msg.wParam
                if hasattr(self, 'registered_hotkeys') and hotkey_id in self.registered_hotkeys:
                    action = self.registered_hotkeys[hotkey_id]
                    self.handle_global_hotkey(action)
                    return True, 0
        return super().nativeEvent(eventType, message)
