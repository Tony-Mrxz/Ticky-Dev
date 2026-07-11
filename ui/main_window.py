# ui/main_window.py
"""Main window layout and window behavior control."""

import ctypes
import sys
from PySide6.QtCore import Qt, QPoint, QEvent, QPropertyAnimation, QEasingCurve, Property, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton, QSizePolicy, QSpacerItem, QMenu
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor

from styles import theme, qss
from utils import config
from widgets.clock import ClockWidget
from widgets.task_card import TaskCard, TaskInputFieldCard
from widgets.toolbar import FloatingToolbar, ToolbarButton

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


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # Set window icon
        from utils.icon import create_ticky_icon
        self.setWindowIcon(create_ticky_icon())
        
        # Set frameless and tool window flags from configuration
        always_on_top = config.load_always_on_top()
        stick_on_desktop = config.load_stick_on_desktop()
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
        
        self.init_ui()
        self.load_window_position()
        self.update_tasks_view()
        self.update_inactivity_timer_settings()
        
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
        
        self.add_task_btn = AnimatedButton("New Task", self)
        self.add_task_btn.setObjectName("HeaderAddTaskButton")
        self.add_task_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_task_btn.clicked.connect(self.start_add_task)
        self.add_task_btn.refresh_colors()  # Apply initial style
        
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
        self.input_card.input_field.setFocus()

    def on_task_added(self, text):
        # Add new tasks to the top of our local tasks list
        self.tasks.insert(0, text)
        config.save_tasks(self.tasks)
        self.on_add_task_cancelled()
        self.update_tasks_view()

    def on_add_task_cancelled(self):
        if self.input_card is not None:
            self.tasks_layout.removeWidget(self.input_card)
            self.input_card.deleteLater()
            self.input_card = None
            self.update_tasks_view()

    def complete_task(self, text):
        if text in self.tasks:
            self.tasks.remove(text)
            config.save_tasks(self.tasks)
        self.update_tasks_view()

    def update_tasks_view(self):
        self.focus_card = None
        if self.widget_state == "normal":
            self.add_task_btn.show()
        else:
            self.add_task_btn.hide()
            
        # 1. Clear existing task card widgets from layout (keeping input_card if active)
        widgets_to_remove = []
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if w != self.input_card:
                    widgets_to_remove.append(w)
        for w in widgets_to_remove:
            self.tasks_layout.removeWidget(w)
            w.deleteLater()
            
        # 2. Render tasks for the current page (max 3)
        total_tasks = len(self.tasks)
        total_pages = max(1, (total_tasks + 2) // 3)
        
        # Handle page index bounds
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
            card.completed.connect(lambda t=text: self.complete_task(t))
            card.focus_toggled.connect(lambda active, c=card: self.handle_task_focus_toggle(c, active))
            if self.widget_state != "normal":
                card.hide()
            # If input_card is currently active, insert it below the input card, else add to end
            if self.input_card is not None:
                self.tasks_layout.insertWidget(self.tasks_layout.count(), card)
            else:
                self.tasks_layout.addWidget(card)
                
        # 3. Update pagination visibility and text
        if total_tasks > 3 and self.widget_state == "normal":
            self.pagination_widget.show()
            self.page_label.setText(f"{self.current_page + 1} / {total_pages}")
            self.prev_btn.setEnabled(self.current_page > 0)
            self.next_btn.setEnabled(self.current_page < total_pages - 1)
        else:
            self.pagination_widget.hide()
            
        # 4. Trigger height adjust updates on next event loop tick
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

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_tasks_view()

    def next_page(self):
        total_pages = max(1, (len(self.tasks) + 2) // 3)
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_tasks_view()

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

    def closeEvent(self, event):
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
        
        # Re-apply styles of currently visible task cards
        for i in range(self.tasks_layout.count()):
            item = self.tasks_layout.itemAt(i)
            if item and item.widget():
                w = item.widget()
                if hasattr(w, 'update_text_style'):
                    w.setStyleSheet(qss.get_task_card_style())
                    w.update_text_style()
                    
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
