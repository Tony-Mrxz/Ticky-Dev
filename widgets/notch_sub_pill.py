from PySide6.QtCore import Qt, QPoint, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QApplication, QBoxLayout
from widgets.toolbar import FloatingToolbar, ToolbarButton
from styles import qss, theme

NOTCH_NOTES_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8c.13 0 .26-.03.38-.08s.23-.12.33-.22l7-7c.09-.09.15-.19.2-.29l.03-.09c.03-.08.05-.17.05-.26 0-.02.01-.04.01-.06V5c0-1.1-.9-2-2-2M5 5h14v7h-6c-.55 0-1 .45-1 1v6H5z"></path>
</svg>"""

NOTCH_REMINDERS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M19 12.59V10c0-3.22-2.18-5.93-5.14-6.74C13.57 2.52 12.85 2 12 2s-1.56.52-1.86 1.26C7.18 4.08 5 6.79 5 10v2.59L3.29 14.3a1 1 0 0 0-.29.71v2c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-2c0-.27-.11-.52-.29-.71zM19 16H5v-.59l1.71-1.71a1 1 0 0 0 .29-.71v-3c0-2.76 2.24-5 5-5s5 2.24 5 5v3c0 .27.11.52.29.71L19 15.41zM5.64 3.3 4.23 1.89A10.9 10.9 0 0 0 1 9.67h2c0-2.4.94-4.66 2.64-6.36Zm12.72 0C20.06 5 21 7.26 21 9.66h2c0-2.94-1.14-5.7-3.22-7.78l-1.41 1.41ZM12 22c1.31 0 2.41-.83 2.82-2H9.18c.41 1.17 1.51 2 2.82 2"></path>
</svg>"""

CHEVRON_DOWN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m12 15.41 5.71-5.7-1.42-1.42-4.29 4.3-4.29-4.3-1.42 1.42z"></path>
</svg>"""

CHEVRON_UP_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m7.71 15.71 4.29-4.3 4.29 4.3 1.42-1.42L12 8.59l-5.71 5.7z"></path>
</svg>"""


class NotchSubPill(QWidget):
    """
    Sub-pill window that smoothly slides down below the hovered notch after 0.5s of hover,
    or rotates vertically and docks to the right side of the notch during AI chat or Notes.
    Hosts FloatingToolbar with Notes, Reminders, AI, Timer, Music, and Settings buttons.
    """
    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self.main_window = getattr(notch_widget, "main_window", None)
        self.is_hovered = False
        self.is_vertical = False
        self.is_vertical_expanded = False
        self._is_animating_hide = False

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = FloatingToolbar(self, solid_background=True)
        self.toolbar.setStyleSheet(qss.get_toolbar_style())
        layout.addWidget(self.toolbar)

        # Add Notes button specifically for NotchSubPill
        self.btn_notes = ToolbarButton(NOTCH_NOTES_SVG, "Notes", self.toolbar)
        self.btn_notes.clicked.connect(self._on_notes_clicked)
        self.toolbar.layout().insertWidget(1, self.btn_notes)

        # Add Reminders button specifically for NotchSubPill
        self.btn_reminders = ToolbarButton(NOTCH_REMINDERS_SVG, "Reminders", self.toolbar)
        self.btn_reminders.clicked.connect(self._on_reminders_clicked)
        self.toolbar.layout().insertWidget(2, self.btn_reminders)

        # Move AI button to index 3 so top 3 features are [Notes, Reminders, AI]
        self.toolbar.layout().removeWidget(self.toolbar.btn_ai)
        self.toolbar.layout().insertWidget(3, self.toolbar.btn_ai)

        # Add Expand / Minimize toggle button for vertical mode
        self.btn_toggle_expand = ToolbarButton(CHEVRON_DOWN_SVG, "Expand", self.toolbar)
        self.btn_toggle_expand.clicked.connect(self._toggle_vertical_expand)
        self.toolbar.layout().addWidget(self.btn_toggle_expand)
        self.btn_toggle_expand.hide()

        self.toolbar.setMinimumWidth(256)
        self.toolbar.setMaximumWidth(256)
        self.toolbar.adjustSize()

        # Hook into toolbar resize to keep sub-pill centered below the notch during stopwatch expand
        orig_tb_resize = self.toolbar.resizeEvent

        def on_tb_resize(event):
            orig_tb_resize(event)
            self.adjustSize()
            self.recenter_under_notch()

        self.toolbar.resizeEvent = on_tb_resize

        # Connect toolbar button signals
        self.toolbar.settings_clicked.connect(self._on_settings_clicked)
        self.toolbar.music_clicked.connect(self._on_music_clicked)
        self.toolbar.ai_clicked.connect(self._on_ai_clicked)
        try:
            self.toolbar.btn_timer.clicked.disconnect()
        except Exception:
            pass
        self.toolbar.btn_timer.clicked.connect(self._on_timer_clicked)

        # Smooth position slide animation (100% solid opacity throughout)
        self.pos_anim = QPropertyAnimation(self, b"pos", self)
        self.pos_anim.setDuration(220)
        self.pos_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.pos_anim.finished.connect(self._on_pos_anim_finished)

        self.resize(self.toolbar.size())

    def _refresh_active_highlights(self):
        """Sync sub-pill button highlights with the notch's current mode flags."""
        is_ai = getattr(self.notch, "ai_chat_in_notch", False)
        is_notes = getattr(self.notch, "notes_in_notch", False)
        is_reminders = getattr(self.notch, "reminders_in_notch", False)
        is_timer = getattr(self.notch, "timer_in_notch", False)
        # A player hidden behind a creation flow is still on: keep it highlighted
        is_media = getattr(self.notch, "media_in_notch", False) or getattr(self.notch, "media_suspended", False)
        if hasattr(self.toolbar, "btn_ai"):
            self.toolbar.btn_ai.setActive(is_ai)
        if hasattr(self, "btn_notes"):
            self.btn_notes.setActive(is_notes)
        if hasattr(self, "btn_reminders"):
            self.btn_reminders.setActive(is_reminders)
        if hasattr(self.toolbar, "btn_timer"):
            self.toolbar.btn_timer.setActive(is_timer)
        if hasattr(self.toolbar, "btn_music"):
            self.toolbar.btn_music.setActive(is_media)

    def set_vertical_mode(self, vertical: bool):
        """Toggle vertical orientation docking on the right side of the expanded notch."""
        if getattr(self, "is_vertical", False) == vertical:
            self._refresh_active_highlights()
            return
        self.is_vertical = vertical
        self.is_vertical_expanded = False

        layout = self.toolbar.layout()
        if vertical:
            if hasattr(layout, "setDirection"):
                layout.setDirection(QBoxLayout.Direction.TopToBottom)
            layout.setContentsMargins(0, 6, 0, 6)
            layout.setSpacing(6)

            # In minimized vertical view: show Notes, Reminders, AI and Expand button;
            # hide Focus timer, Media controls, and Settings
            self.toolbar.btn_timer.setVisible(False)
            self.toolbar.btn_music.setVisible(False)
            self.toolbar.btn_settings.setVisible(False)

            self.btn_toggle_expand.set_svg_template(CHEVRON_DOWN_SVG, "Expand")
            self.btn_toggle_expand.setVisible(True)

            self.toolbar.setMinimumWidth(44)
            self.toolbar.setMaximumWidth(44)
            self.toolbar.setMinimumHeight(174)
            self.toolbar.setMaximumHeight(174)
            self.setFixedSize(44, 174)
        else:
            if hasattr(layout, "setDirection"):
                layout.setDirection(QBoxLayout.Direction.LeftToRight)
            layout.setContentsMargins(6, 0, 6, 0)
            layout.setSpacing(6)

            # In horizontal view: show all normal tools and hide expand button
            self.toolbar.btn_timer.setVisible(True)
            self.toolbar.btn_music.setVisible(True)
            self.toolbar.btn_settings.setVisible(True)
            self.btn_toggle_expand.setVisible(False)

            self.toolbar.setMinimumWidth(256)
            self.toolbar.setMaximumWidth(256)
            self.toolbar.setMinimumHeight(44)
            self.toolbar.setMaximumHeight(44)
            self.setFixedSize(256, 44)

        # Highlight active button
        self._refresh_active_highlights()

        self.toolbar.adjustSize()
        self.adjustSize()
        self.recenter_under_notch()
        self.update()

    def _toggle_vertical_expand(self):
        """Toggle minimized / expanded state of sub-pill in vertical mode."""
        if not getattr(self, "is_vertical", False):
            return

        self.is_vertical_expanded = not getattr(self, "is_vertical_expanded", False)
        if self.is_vertical_expanded:
            # Show hidden buttons: Focus timer, Media controls, Settings
            self.toolbar.btn_timer.setVisible(True)
            self.toolbar.btn_music.setVisible(True)
            self.toolbar.btn_settings.setVisible(True)
            self.btn_toggle_expand.set_svg_template(CHEVRON_UP_SVG, "Minimize")
            target_h = 300
        else:
            # Hide buttons: Focus timer, Media controls, Settings
            self.toolbar.btn_timer.setVisible(False)
            self.toolbar.btn_music.setVisible(False)
            self.toolbar.btn_settings.setVisible(False)
            self.btn_toggle_expand.set_svg_template(CHEVRON_DOWN_SVG, "Expand")
            target_h = 174

        self.toolbar.setMinimumHeight(target_h)
        self.toolbar.setMaximumHeight(target_h)
        self.setFixedSize(44, target_h)
        self.toolbar.adjustSize()
        self.adjustSize()
        self.recenter_under_notch()
        self.update()

    def recenter_under_notch(self):
        """Keep the sub-pill centered horizontally under the notch or docked on the right side when vertical."""
        if not self.notch or not self.isVisible():
            return
        notch_geo = self.notch.geometry()

        if getattr(self, "is_vertical", False):
            screen = self.notch.screen() or QApplication.primaryScreen()
            screen_geo = screen.geometry() if screen else None

            target_x = notch_geo.x() + notch_geo.width() + 8
            # If target_x overflows right screen edge, fall back to the left side of notch
            if screen_geo and (target_x + self.width() > screen_geo.x() + screen_geo.width()):
                target_x = notch_geo.x() - self.width() - 8

            target_y = notch_geo.y() + 8
        else:
            notch_center_x = notch_geo.x() + (notch_geo.width() // 2)
            target_x = notch_center_x - (self.width() // 2)
            target_y = notch_geo.y() + notch_geo.height() + 8

        if self.pos_anim.state() != QPropertyAnimation.State.Running:
            self.move(target_x, target_y)
        else:
            if not self._is_animating_hide:
                self.pos_anim.stop()
                self.move(target_x, target_y)
            else:
                self.move(target_x, self.y())

    def ensure_stays_on_top(self):
        """Reinforce window topmost z-order on Windows so sub-pill never drops behind applications."""
        self.raise_()
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010
                SWP_SHOWWINDOW = 0x0040
                ctypes.windll.user32.SetWindowPos(
                    int(self.winId()),
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
                )
            except Exception:
                pass

    def showEvent(self, event):
        # The pill can appear through show() or show_animated(); sync in both cases
        self._refresh_active_highlights()
        super().showEvent(event)
        self.ensure_stays_on_top()

    def show_animated(self):
        """Smoothly slide down (or slide in from right) with 100% solid opacity."""
        if not self.notch:
            return

        # Re-showing an already visible pill never fires showEvent
        self._refresh_active_highlights()
        self._is_animating_hide = False
        self.pos_anim.stop()

        is_vert = getattr(self, "is_vertical", False)
        notch_geo = self.notch.geometry()

        if is_vert:
            target_w = self.width()
            target_h = self.height()
            target_x = notch_geo.x() + notch_geo.width() + 8
            screen = self.notch.screen() or QApplication.primaryScreen()
            if screen and (target_x + target_w > screen.geometry().x() + screen.geometry().width()):
                target_x = notch_geo.x() - target_w - 8
            target_y = notch_geo.y() + 8
            start_x = target_x - 10
            start_y = target_y

            self.resize(target_w, target_h)
            self.move(start_x, start_y)
            self.setWindowOpacity(1.0)
            self.show()
            self.ensure_stays_on_top()

            self.pos_anim.setStartValue(QPoint(start_x, start_y))
            self.pos_anim.setEndValue(QPoint(target_x, target_y))
            self.pos_anim.start()
        else:
            notch_center_x = notch_geo.x() + (notch_geo.width() // 2)
            target_w = self.toolbar.width()
            target_h = self.toolbar.height()
            target_x = notch_center_x - (target_w // 2)
            target_y = notch_geo.y() + notch_geo.height() + 8

            start_y = target_y - 12  # 12px slide down distance

            self.resize(target_w, target_h)
            self.move(target_x, start_y)
            self.setWindowOpacity(1.0)
            self.show()
            self.ensure_stays_on_top()

            self.pos_anim.setStartValue(QPoint(target_x, start_y))
            self.pos_anim.setEndValue(QPoint(target_x, target_y))
            self.pos_anim.start()

    def hide_animated(self):
        """Smoothly slide up slightly before hiding."""
        if not self.isVisible() or self._is_animating_hide:
            return

        self._is_animating_hide = True
        self.pos_anim.stop()

        curr_pos = self.pos()
        target_y = curr_pos.y() - 10

        self.pos_anim.setStartValue(curr_pos)
        self.pos_anim.setEndValue(QPoint(curr_pos.x(), target_y))
        self.pos_anim.start()

    def _on_pos_anim_finished(self):
        if self._is_animating_hide:
            self.hide()
            self._is_animating_hide = False

    def enterEvent(self, event):
        self.is_hovered = True
        if self.notch:
            self.notch.sub_pill_leave_timer.stop()
            self.notch.sub_pill_hover_timer.stop()
            self.notch._is_hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovered = False
        if self.notch and not getattr(self.notch, "ai_chat_in_notch", False):
            self.notch.sub_pill_leave_timer.start(450)
        super().leaveEvent(event)

    def _on_notes_clicked(self):
        """Expand notch to display notes 3 in a row, or show 'no notes available' if 0 notes."""
        if not self.notch:
            return
        if getattr(self.notch, "notes_in_notch", False):
            self.set_vertical_mode(False)
            self.notch.collapse_to_idle(force=True)
            return
        notes = self.notch.get_notes_list() if hasattr(self.notch, "get_notes_list") else []
        if hasattr(self.notch, "show_notes_in_notch"):
            self.notch.show_notes_in_notch()
        if len(notes) > 0:
            self.set_vertical_mode(False)
            self.show()
            self.recenter_under_notch()
        else:
            self.hide_animated()

    def _on_reminders_clicked(self):
        """Toggle reminders list view in the notch (or show 'No reminders set' if empty)."""
        if not self.notch:
            return
        if hasattr(self.notch, "sub_pill_leave_timer"):
            self.notch.sub_pill_leave_timer.stop()
        if hasattr(self.notch, "sub_pill_hover_timer"):
            self.notch.sub_pill_hover_timer.stop()
        if getattr(self.notch, "reminders_in_notch", False) and not getattr(self.notch, "empty_reminders_showing", False):
            self.set_vertical_mode(False)
            self.notch.collapse_reminders()
        else:
            if hasattr(self.notch, "show_reminders_in_notch"):
                self.notch.show_reminders_in_notch()

    def _on_timer_clicked(self):
        """Spawn and start timer in the notch widget, replacing task if present."""
        if self.is_vertical:
            self.set_vertical_mode(False)
        if self.notch and hasattr(self.notch, "toggle_notch_timer_standalone"):
            self.notch.toggle_notch_timer_standalone()
        self.hide_animated()

    def _on_settings_clicked(self):
        """Open settings window."""
        if self.main_window and hasattr(self.main_window, "show_settings_menu"):
            self.main_window.show_settings_menu()
        else:
            from ui.settings_window import SettingsWindow
            if not hasattr(self, "_settings_win") or self._settings_win is None:
                self._settings_win = SettingsWindow()
            self._settings_win.show_centered()

    def _on_music_clicked(self):
        """Toggle media player in the notch."""
        if not self.notch:
            return
        if hasattr(self.notch, "sub_pill_leave_timer"):
            self.notch.sub_pill_leave_timer.stop()
        if hasattr(self.notch, "sub_pill_hover_timer"):
            self.notch.sub_pill_hover_timer.stop()
        if getattr(self.notch, "media_in_notch", False):
            self.set_vertical_mode(False)
            self.notch.collapse_media_in_notch()
        else:
            self.notch.show_media_in_notch()

    def _on_ai_clicked(self):
        """Open or toggle mini AI chat in the notch."""
        if not self.notch:
            return
        if hasattr(self.notch, "sub_pill_leave_timer"):
            self.notch.sub_pill_leave_timer.stop()
        if hasattr(self.notch, "sub_pill_hover_timer"):
            self.notch.sub_pill_hover_timer.stop()
        if getattr(self.notch, "ai_chat_in_notch", False):
            self.set_vertical_mode(False)
            self.notch.collapse_ai_chat()
            return
        if hasattr(self.notch, "toggle_ai_chat_in_notch"):
            self.notch.toggle_ai_chat_in_notch()
        self.set_vertical_mode(True)
        self.show()
        self.recenter_under_notch()

    def refresh_theme(self):
        """Update stylesheet on theme change."""
        self.toolbar.setStyleSheet(qss.get_toolbar_style())
        if hasattr(self, "btn_notes") and self.btn_notes:
            self.btn_notes.update()
        if hasattr(self, "btn_reminders") and self.btn_reminders:
            self.btn_reminders.update()
        if hasattr(self, "btn_toggle_expand") and self.btn_toggle_expand:
            self.btn_toggle_expand.update()
        self.toolbar.update()
