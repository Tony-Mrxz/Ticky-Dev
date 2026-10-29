# widgets/notch_widget.py
"""
Plain Apple Mac-style Notch Widget for Ticky.
Anchored at the top center of the screen.
When idle: Displays cute, large theme-colored square eyes that follow mouse movements.
If mouse is idle for 3 seconds, eyes look straight ahead normally.
When hovered: As the notch smoothly expands, the eyes fade out, and once expanded,
the current time is displayed. When unhovered, reverses smoothly back to eyes.
"""

import sys
import time
import random
import math
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QPropertyAnimation, QEasingCurve, QTimer, QDateTime, QByteArray, Property, Signal, QUrl, QEvent
from PySide6.QtWidgets import QWidget, QApplication, QMenu, QLineEdit, QTextEdit
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath, QCursor, QFontMetrics, QTextCursor, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest

from styles import theme
from utils import config
from widgets.task_card import get_task_color, FOCUS_SVG, STOP_SVG
from widgets.toolbar import PLAY_SVG, RESTART_SVG, STOP_SVG as TOOLBAR_STOP_SVG
from widgets.notch_sub_pill import NotchSubPill
from widgets.notch_ai_chat import NotchMiniAIChat
from widgets.notch_reminder import NotchReminderWidget
from widgets.notch_app_search import NotchAppSearchWidget
from utils.dictation_service import DictationService, DictationState
from utils import text_inject
from utils.version import APP_VERSION

MEDIA_PREV_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M17.46 6.11a1 1 0 0 0-1.04.08l-7 5c-.26.19-.42.49-.42.81s.16.63.42.81l7 5c.17.12.38.19.58.19.16 0 .31-.04.46-.11.33-.17.54-.51.54-.89V7c0-.37-.21-.72-.54-.89M6 6h2v12H6z"></path>
</svg>"""
MEDIA_PLAY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M6.51 18.87c.15.09.32.13.49.13s.36-.05.51-.14l10-6c.3-.18.49-.51.49-.86s-.18-.68-.49-.86l-10-6a.99.99 0 0 0-1.01-.01c-.31.18-.51.51-.51.87v12c0 .36.19.69.51.87Z"></path>
</svg>"""
MEDIA_PAUSE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<rect width="5" height="12" x="6" y="6" rx="1" ry="1"></rect><rect width="5" height="12" x="13" y="6" rx="1" ry="1"></rect>
</svg>"""
MEDIA_NEXT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m14.58 11.19-7-5c-.31-.22-.71-.25-1.04-.08S6 6.62 6 7v10c0 .37.21.72.54.89.14.07.3.11.46.11.21 0 .41-.06.58-.19l7-5c.26-.19.42-.49.42-.81s-.16-.63-.42-.81M16 6h2v12h-2z"></path>
</svg>"""

TICK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m10 15.586-3.293-3.293-1.414 1.414L10 18.414l9.707-9.707-1.414-1.414z"></path>
</svg>"""

CROSS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m16.192 6.344-4.243 4.242-4.242-4.242-1.414 1.414L10.535 12l-4.242 4.242 1.414 1.414 4.242-4.242 4.243 4.242 1.414-1.414L13.364 12l4.242-4.242z"></path>
</svg>"""

DICTATION_CROSS_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="m7.76 14.83-2.83 2.83 1.41 1.41 2.83-2.83 2.12-2.12.71-.71.71.71 1.41 1.42 3.54 3.53 1.41-1.41-3.53-3.54-1.42-1.41-.71-.71 5.66-5.66-1.41-1.41L12 10.59 6.34 4.93 4.93 6.34 10.59 12l-.71.71z"></path>
</svg>"""

DICTATION_MIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M12 20c-4.41 0-8-3.59-8-8H2c0 5.51 4.49 10 10 10s10-4.49 10-10h-2c0 4.41-3.59 8-8 8"></path><path d="M12 2C8.69 2 6 4.69 6 8v4c0 3.31 2.69 6 6 6s6-2.69 6-6V8c0-3.31-2.69-6-6-6m4 10c0 2.21-1.79 4-4 4s-4-1.79-4-4V8c0-2.21 1.79-4 4-4s4 1.79 4 4z"></path>
</svg>"""

NOTE_DELETE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M17 6V4c0-1.1-.9-2-2-2H9c-1.1 0-2 .9-2 2v2H2v2h2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8h2V6zM9 4h6v2H9zM6 20V8h12v12z"></path>
<path d="M9 10h2v8H9zm4 0h2v8h-2z"></path>
</svg>"""

NOTE_COPY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M20 2H10c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m0 12H10V4h10z"></path>
<path d="M14 20H4V10h2V8H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2v-2h-2z"></path>
</svg>"""

NOTCH_NOTES_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8c.13 0 .26-.03.38-.08s.23-.12.33-.22l7-7c.09-.09.15-.19.2-.29l.03-.09c.03-.08.05-.17.05-.26 0-.02.01-.04.01-.06V5c0-1.1-.9-2-2-2M5 5h14v7h-6c-.55 0-1 .45-1 1v6H5z"></path>
</svg>"""

REMINDER_ALERT_BELL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M19 12.59V10c0-3.22-2.18-5.93-5.14-6.74C13.57 2.52 12.85 2 12 2s-1.56.52-1.86 1.26C7.18 4.08 5 6.79 5 10v2.59L3.29 14.3a1 1 0 0 0-.29.71v2c0 .55.45 1 1 1h16c.55 0 1-.45 1-1v-2c0-.27-.11-.52-.29-.71zM19 16H5v-.59l1.71-1.71a1 1 0 0 0 .29-.71v-3c0-2.76 2.24-5 5-5s5 2.24 5 5v3c0 .27.11.52.29.71L19 15.41zM5.64 3.3 4.23 1.89A10.9 10.9 0 0 0 1 9.67h2c0-2.4.94-4.66 2.64-6.36Zm12.72 0C20.06 5 21 7.26 21 9.66h2c0-2.94-1.14-5.7-3.22-7.78l-1.41 1.41ZM12 22c1.31 0 2.41-.83 2.82-2H9.18c.41 1.17 1.51 2 2.82 2"></path>
</svg>"""

UPDATE_ALERT_DOWNLOAD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M11 3h2v8h3l-4 4.5L8 11h3z"></path><path d="M4 17.5h16V20H4z"></path>
</svg>"""

# Windows API for system-wide zero-latency keystroke detection
try:
    import ctypes
    user32 = ctypes.windll.user32
except Exception:
    user32 = None

# Keys that produce text characters: Letters, Digits, Numpad digits, Punctuation/Symbols, Space, Backspace
# Excludes Enter, Up/Down/Left/Right arrows, Tab, Esc, Ctrl, Alt, Win, Function keys, etc.
LETTERS = list(range(0x41, 0x5B))          # A-Z (0x41 - 0x5A)
DIGITS = list(range(0x30, 0x3A))           # 0-9 (0x30 - 0x39)
NUMPAD_DIGITS = list(range(0x60, 0x6A))    # Numpad 0-9 (0x60 - 0x69)
NUMPAD_OPERATORS = [0x6A, 0x6B, 0x6D, 0x6E, 0x6F]  # * + - . /
OEM_SYMBOLS = (
    list(range(0xBA, 0xC1))                # ;=,-./`
    + list(range(0xDB, 0xDF))              # [\]'
)
SPACE_KEY = 0x20
BACKSPACE_KEY = 0x08

TYPING_KEYS = tuple(
    LETTERS
    + DIGITS
    + NUMPAD_DIGITS
    + NUMPAD_OPERATORS
    + OEM_SYMBOLS
    + [SPACE_KEY, BACKSPACE_KEY]
)


class TaskInputLineEdit(QLineEdit):
    """Clean borderless line edit for inline task creation in notch."""
    escape_pressed = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            return
        super().keyPressEvent(event)


class NoteInputTextEdit(QTextEdit):
    """Clean borderless multiline text edit for inline note creation in notch."""
    save_pressed = Signal()
    escape_pressed = Signal()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
            return
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.save_pressed.emit()
                return
        super().keyPressEvent(event)


class NotchWidget(QWidget):
    """
    Plain Apple Mac-style Notch Widget with interactive cute square eyes.
    Eyes track mouse cursor in real-time, reset to looking straight after 3s idle.
    When typing letters, numbers, or symbols, displays the active typed text (up to 6 chars).
    When typing stops, immediately restores the cute square eyes.
    On hover, expands smoothly to display: Time | [+] Add Button | [ ] Random Task.
    """

    update_now_requested = Signal()

    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window

        # Geometry dimensions
        self.idle_w = 160
        self.idle_h = 32
        self.hover_w = 440
        self.hover_h = 54

        self._is_hovered = False
        self.anim = None

        # Eye tracking state
        self.pupil_x = 0.0
        self.pupil_y = 0.0
        self.last_mouse_pos = QCursor.pos()
        self.last_mouse_move_time = time.time()

        # Blinking animation state
        self.is_blinking = False
        self.blink_progress = 0.0
        self.blink_direction = 1

        # Live typed text state (max 6 characters, only letters, numbers, symbols)
        self.is_typing = False
        self.typed_text = ""
        self.last_key_time = 0.0
        self.last_repeat_time = 0.0
        self.key_states = {}
        self.key_down_time = {}

        # Silky smooth typing animation states
        self.typing_blend = 0.0        # 0.0 = eyes, 1.0 = typed text (smooth crossfade)
        self.scroll_x = 0.0            # Smooth horizontal ribbon scrolling
        self.smooth_cursor_x = 80.0    # Smooth gliding caret interpolation

        # Expanded state: Time+Date, Add Button, Task Card & Focus interaction
        self.current_random_task = None
        self.hover_add_btn = False
        self.hover_card = False
        self.hover_cb = False
        self.hover_play = False
        self.is_active_focus = False
        self.task_completed_anim = False

        self.time_box_rect = QRect()
        self.add_btn_rect = QRect()
        self.task_card_rect = QRect()
        self.task_cb_rect = QRect()
        self.task_play_rect = QRect()

        # Add button capsule and task creation states
        self.add_expanded = False
        self._add_expand_progress = 0.0
        self.is_creating_task = False
        self.hover_sub_task = False
        self.hover_sub_note = False
        self.hover_sub_reminder = False
        self.sub_task_rect = QRect()
        self.sub_note_rect = QRect()
        self.sub_reminder_rect = QRect()
        self.add_toggle_rect = QRect()

        # Tasks list expanded state (clicking task card in notch expands to show all tasks)
        self.tasks_in_notch = False
        self.notch_task_scroll = 0.0        # pixel offset into the tasks list
        self.notch_task_rects = []           # list of (QRect, idx, task_text)
        self.notch_task_cb_rects = []        # list of (QRect, idx, task_text) for checkboxes only
        self.notch_task_play_rects = []      # list of (QRect, idx, task_text) for play buttons
        self.hovered_task_idx = None
        self.hovered_task_cb_idx = None
        self.hovered_task_play_idx = None

        # Mini AI chat in notch
        self.ai_chat_in_notch = False
        self.ai_is_thinking = False
        self.ai_is_listening = False
        self.notch_ai_close_rect = QRect()
        self.notch_ai_task_cb_rect = QRect()
        self.hover_ai_close = False
        self.hover_ai_task_cb = False
        self._ai_thinking_wander_dir = -1.0

        # Media player in notch
        self.media_in_notch = False
        self.media_manager = None
        self._active_media_workers = []
        self.media_title = "Not Playing"
        self.media_artist = "Windows Media"
        self.media_album = ""
        self.media_is_playing = False
        self.media_progress_ms = 0
        self.media_duration_ms = 0
        self.media_can_prev = True
        self.media_can_next = True
        self.media_can_play = True
        self.media_album_pixmap = None
        self.media_current_track_id = None
        self.hover_media_prev = False
        self.hover_media_play = False
        self.hover_media_next = False
        self.hover_media_close = False
        self.media_prev_rect = QRect()
        self.media_play_rect = QRect()
        self.media_next_rect = QRect()
        self.media_close_rect = QRect()
        self.media_block_rect = QRect()
        self._media_row_left_x = 0.0
        self.media_suspended = False

        self.media_poll_timer = QTimer(self)
        self.media_poll_timer.setInterval(2500)
        self.media_poll_timer.timeout.connect(self.poll_notch_media)

        self.media_timeline_timer = QTimer(self)
        self.media_timeline_timer.setInterval(1000)
        self.media_timeline_timer.timeout.connect(self._on_notch_media_timeline_tick)

        self.media_network_manager = QNetworkAccessManager(self)
        self.media_network_manager.finished.connect(self._on_notch_media_image_downloaded)

        # System-wide smart voice dictation in notch
        self.dictation_in_notch = False
        self.dictation_levels = []
        self.dictation_partial = ""
        self.dictation_cancel_rect = QRect()
        self.hover_dictation_cancel = False
        self.dictation_service = DictationService(self)
        self.dictation_service.state_changed.connect(self._on_dictation_state_changed)
        self.dictation_service.levels_updated.connect(self._on_dictation_levels)
        self.dictation_service.partial_updated.connect(self._on_dictation_partial)
        self.dictation_service.error_occurred.connect(self._on_dictation_error)
        self.dictation_service.session_ended.connect(self._on_dictation_session_ended)

        # Voice dictation silence abort timer (reverts to ground state if no input for a few seconds)
        self.dictation_abort_timer = QTimer(self)
        self.dictation_abort_timer.setSingleShot(True)
        self.dictation_abort_timer.setInterval(3500)
        self.dictation_abort_timer.timeout.connect(self._on_dictation_timeout_abort)

        self.add_expand_anim = QPropertyAnimation(self, b"add_expand_progress", self)
        self.add_expand_anim.setDuration(220)
        self.add_expand_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Tick-off animation for a row in the expanded tasks list
        self.completing_task_text = None
        self._complete_row_progress = 0.0
        self.complete_row_anim = QPropertyAnimation(self, b"complete_row_progress", self)
        self.complete_row_anim.setDuration(320)
        self.complete_row_anim.setStartValue(0.0)
        self.complete_row_anim.setEndValue(1.0)
        self.complete_row_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Unhover 5-second grace period timer after clicking Add button
        self.unhover_collapse_timer = QTimer(self)
        self.unhover_collapse_timer.setSingleShot(True)
        self.unhover_collapse_timer.setInterval(5000)
        self.unhover_collapse_timer.timeout.connect(self._on_unhover_timeout)

        # Sub-pill (secondary state showing Toolbar buttons below hovered notch after 0.5s)
        self.sub_pill = NotchSubPill(self)
        self.sub_pill_hover_timer = QTimer(self)
        self.sub_pill_hover_timer.setSingleShot(True)
        self.sub_pill_hover_timer.setInterval(500)   # 0.5s hover delay
        self.sub_pill_hover_timer.timeout.connect(self._on_sub_pill_hover_trigger)

        self.sub_pill_leave_timer = QTimer(self)
        self.sub_pill_leave_timer.setSingleShot(True)
        self.sub_pill_leave_timer.setInterval(450)   # 450ms grace period between notch and sub-pill
        self.sub_pill_leave_timer.timeout.connect(self._on_sub_pill_leave_timeout)

        # Notch Timer State (Stopwatch / Focus timer in the notch)
        self.timer_in_notch = False
        self.timer_is_running = False
        self.timer_ms = 0
        self.timer_task_title = None
        self.timer_time_peek_active = False
        self.timer_hover_play = False
        self.timer_hover_restart = False
        self.timer_play_rect = QRect()
        self.timer_restart_rect = QRect()
        self.timer_display_rect = QRect()
        self.timer_card_rect = QRect()

        self.notch_stopwatch_timer = QTimer(self)
        self.notch_stopwatch_timer.setInterval(1000)
        self.notch_stopwatch_timer.timeout.connect(self._on_notch_stopwatch_tick)

        self.timer_peek_scheduler = QTimer(self)
        self.timer_peek_scheduler.timeout.connect(self._on_timer_time_peek_trigger)

        self.timer_peek_restore_timer = QTimer(self)
        self.timer_peek_restore_timer.setSingleShot(True)
        self.timer_peek_restore_timer.setInterval(3500)
        self.timer_peek_restore_timer.timeout.connect(self._on_timer_time_peek_end)

        self.timer_stopped_collapse_timer = QTimer(self)
        self.timer_stopped_collapse_timer.setSingleShot(True)
        self.timer_stopped_collapse_timer.timeout.connect(self._on_timer_stopped_collapse_timeout)
        self._cursor_outside_start_time = None

        # Embedded QLineEdit for task creation in the extended notch area
        self.task_input_edit = TaskInputLineEdit(self)
        self.task_input_edit.setPlaceholderText("What needs to be done?")
        self.task_input_edit.returnPressed.connect(self.submit_notch_task)
        self.task_input_edit.escape_pressed.connect(self.cancel_notch_task)
        font_family = config.load_font_family("DM Sans")
        self.task_input_edit.setStyleSheet(f"""
            QLineEdit {{
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
                padding: 0px;
                selection-background-color: {theme.ACCENT_COLOR};
            }}
        """)
        self.task_input_edit.hide()

        # Note creation & editing state & embedded QTextEdit in notch
        self.is_creating_note = False
        self.editing_note_index = None
        self.hover_note_tick = False
        self.hover_note_cross = False
        self.hover_note_delete = False
        self.note_tick_rect = QRect()
        self.note_cross_rect = QRect()
        self.note_delete_rect = QRect()
        self.note_input_edit = NoteInputTextEdit(self)
        self.note_input_edit.setPlaceholderText("Write your note here... (Ctrl+Enter to save)")
        self.note_input_edit.save_pressed.connect(self.submit_notch_note)
        self.note_input_edit.escape_pressed.connect(self.cancel_notch_note)
        self.note_input_edit.setStyleSheet(f"""
            QTextEdit {{
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
                selection-background-color: {theme.ACCENT_COLOR};
            }}
        """)
        self.note_input_edit.hide()

        # Mini AI chat widget embedded in notch
        self.ai_chat_widget = NotchMiniAIChat(self, parent=self)
        self.ai_chat_widget.hide()

        # Reminders widget embedded in notch
        self.reminders_in_notch = False
        self.is_creating_reminder = False
        self.empty_reminders_showing = False
        self.empty_reminders_restore_timer = QTimer(self)
        self.empty_reminders_restore_timer.setSingleShot(True)
        self.empty_reminders_restore_timer.timeout.connect(self._restore_from_empty_reminders)
        self.reminder_widget = NotchReminderWidget(self, parent=self)
        self.reminder_widget.hide()
        self.reminder_widget.closed.connect(self.collapse_reminders)

        # Embedded QLineEdit for reminder title beside time in the top header
        self.reminder_title_edit = QLineEdit(self)
        self.reminder_title_edit.setFixedHeight(36)
        self.reminder_title_edit.setPlaceholderText("What would you like to be reminded of?")
        self.reminder_title_edit.returnPressed.connect(self._on_reminder_title_return)
        accent_hex = config.load_accent_color(theme.ACCENT_COLOR)
        self.reminder_title_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 10px;
                color: #FFFFFF;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 11.5px;
                padding: 4px 10px;
                selection-background-color: {accent_hex};
            }}
            QLineEdit:focus {{
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid {accent_hex};
            }}
        """)
        self.reminder_title_edit.hide()

        # System-Wide App & Software Search in Notch (Alt + W)
        self.app_search_in_notch = False
        self.app_search_widget = NotchAppSearchWidget(self, parent=self)
        self.app_search_widget.hide()
        self.app_search_widget.request_geometry_update.connect(self._on_app_search_geometry_requested)
        self.app_search_widget.app_launched.connect(self._on_app_search_launched)
        self.app_search_widget.closed.connect(self.collapse_app_search)

        # Reminder due alert HUD state
        self.active_reminder_alert = None
        self.reminder_dismiss_rect = QRect()
        self.reminder_snooze_rect = QRect()
        self.reminder_done_rect = QRect()
        self.hover_reminder_dismiss = False
        self.hover_reminder_snooze = False
        self.hover_reminder_done = False

        # Software update alert HUD state
        self.active_update_alert = None
        self.update_alert_status = "available"
        self.update_alert_detail = ""
        self.update_now_rect = QRect()
        self.update_later_rect = QRect()
        self.hover_update_now = False
        self.hover_update_later = False

        # Periodic check for due reminders (every 3 seconds for timely alerts)
        self.reminder_check_timer = QTimer(self)
        self.reminder_check_timer.setInterval(3000)
        self.reminder_check_timer.timeout.connect(self._check_due_reminders)
        self.reminder_check_timer.start()

        # Notes Grid display state in notch (3 in a row)
        self.notes_in_notch = False
        self.empty_notes_showing = False
        self.empty_notes_restore_timer = QTimer(self)
        self.empty_notes_restore_timer.setSingleShot(True)
        self.empty_notes_restore_timer.timeout.connect(self._restore_from_empty_notes)
        self.notch_notes_page = 0
        self.copied_note_idx = None
        self.hovered_note_card_idx = None
        self.hovered_note_copy_idx = None
        self.notch_note_rects = []
        self.notch_note_copy_rects = []

        self.pick_random_task()

        # Frameless, stays on top, tool window with transparent background
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        # Avoid stealing keyboard focus from the app the user is dictating into
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setMouseTracking(True)

        self.resize(self.idle_w, self.idle_h)
        self.reposition_notch()

        # Timer 1: Eye tracking & mouse idle check (~60 fps)
        self.eye_timer = QTimer(self)
        self.eye_timer.timeout.connect(self.update_eye_tracking)
        self.eye_timer.start(16)

        # Timer 2: Occasional cute blink trigger (every 4-7 seconds)
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(4500)
        self.blink_timer.timeout.connect(self.trigger_blink)
        self.blink_timer.start()

        # Timer 3: Blink squash animation step
        self.blink_anim_timer = QTimer(self)
        self.blink_anim_timer.setInterval(16)
        self.blink_anim_timer.timeout.connect(self.animate_blink)

        # -------------------------------------------------------------
        # Living Idle Animations (Time peek, Expressions, Task peek)
        # -------------------------------------------------------------
        self.target_left_eye_scale_x = 1.0
        self.target_left_eye_scale_y = 1.0
        self.current_left_eye_scale_x = 1.0
        self.current_left_eye_scale_y = 1.0

        self.target_right_eye_scale_x = 1.0
        self.target_right_eye_scale_y = 1.0
        self.current_right_eye_scale_x = 1.0
        self.current_right_eye_scale_y = 1.0

        self.target_flat_eyes = 0.0      # 0.0 = square eyes, 1.0 = flat slit line "- -"
        self.current_flat_eyes = 0.0

        self.target_half_closed = 0.0    # 0.0 = normal open eyes, 1.0 = half closed eyes
        self.current_half_closed = 0.0

        self.override_pupil = False
        self.override_pupil_x = 0.0
        self.override_pupil_y = 0.0

        self.target_eyes_offset_x = 0.0  # Horizontal shift for task peek
        self.eyes_offset_x = 0.0

        self.target_eyes_scroll_y = 0.0  # Vertical scroll for time peek
        self.eyes_scroll_y = 0.0

        # Mode 1: Random Time & Date display peek
        self.time_peek_active = False
        self.time_peek_val = 0.0         # 0.0 = eyes, 1.0 = time & date visible
        self.time_peek_restore_timer = QTimer(self)
        self.time_peek_restore_timer.setSingleShot(True)
        self.time_peek_restore_timer.timeout.connect(self.end_time_peek)

        # Mode 2: Random Expression reset timer
        self.expression_active = False
        self.idle_expression_triggered = False
        self.expression_restore_timer = QTimer(self)
        self.expression_restore_timer.setSingleShot(True)
        self.expression_restore_timer.timeout.connect(self.reset_expression)

        # Mode 3: Random Task Peek (Smooth 60fps Synchronized State)
        self.task_peek_active = False
        self.task_collapsing = False
        self.task_peek_title = ""
        self.task_peek_side = "right"     # "right" or "left"
        self.task_peek_opacity = 0.0
        self.task_peek_target_w = 380
        self.task_peek_card_w = 200
        self.task_peek_elided_title = ""
        self.task_focus_renderer = None
        self.cached_font_task = None
        self.cached_fm_task = None
        self.task_peek_restore_timer = QTimer(self)
        self.task_peek_restore_timer.setSingleShot(True)
        self.task_peek_restore_timer.timeout.connect(self.end_task_peek)

        # Idle scheduler timer (triggers random idle behaviors)
        self.last_idle_mode = None
        self.idle_cycle_timer = QTimer(self)
        self.idle_cycle_timer.setInterval(5000)
        self.idle_cycle_timer.timeout.connect(self.trigger_random_idle_behavior)
        self.idle_cycle_timer.start()

    @Property(float)
    def add_expand_progress(self):
        return self._add_expand_progress

    @add_expand_progress.setter
    def add_expand_progress(self, val):
        self._add_expand_progress = val
        self.update()

    @Property(float)
    def complete_row_progress(self):
        return self._complete_row_progress

    @complete_row_progress.setter
    def complete_row_progress(self, val):
        self._complete_row_progress = val
        self.update()

    def apply_notch_style(self):
        """Called by main window when themes or settings refresh."""
        self.hover_w = self.calc_expanded_width()
        font_family = config.load_font_family("DM Sans")
        self.task_input_edit.setStyleSheet(f"""
            QLineEdit {{
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
                padding: 0px;
                selection-background-color: {theme.ACCENT_COLOR};
            }}
        """)
        self.note_input_edit.setStyleSheet(f"""
            QTextEdit {{
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 11px;
                background: transparent;
                border: none;
                padding: 0px;
                selection-background-color: {theme.ACCENT_COLOR};
            }}
        """)
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.refresh_theme()
        if self._is_hovered and not self.is_creating_task and not self.is_creating_note and not self.notes_in_notch:
            if self.timer_in_notch:
                self.update_notch_timer_geometry()
            elif self.add_expanded:
                self.animate_to(self.calc_add_expanded_width(), self.hover_h)
            else:
                self.animate_to(self.hover_w, self.hover_h)
        self.update()

    def ensure_stays_on_top(self):
        """Reinforce window topmost z-order on Windows so notch never drops behind applications or onto desktop."""
        self.raise_()
        if user32 and sys.platform == "win32":
            try:
                HWND_TOPMOST = -1
                SWP_NOSIZE = 0x0001
                SWP_NOMOVE = 0x0002
                SWP_NOACTIVATE = 0x0010
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(
                    int(self.winId()),
                    HWND_TOPMOST,
                    0, 0, 0, 0,
                    SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW,
                )
            except Exception:
                pass

    def event(self, event):
        if (
            event.type() == QEvent.Type.WindowDeactivate
            and getattr(self, "app_search_in_notch", False)
        ):
            self.collapse_app_search()
        return super().event(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.ensure_stays_on_top()
        if sys.platform == "win32":
            from utils.window_capture import set_window_capture_exclusion
            set_window_capture_exclusion(int(self.winId()), config.load_hide_while_streaming())

    def reposition_notch(self):
        """Center the notch horizontally at the very top edge of the primary screen."""
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.geometry()
        target_x = screen_geo.x() + (screen_geo.width() - self.width()) // 2
        target_y = screen_geo.y()
        self.move(target_x, target_y)
        self.ensure_stays_on_top()
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.recenter_under_notch()

    def trigger_blink(self):
        if not self.is_blinking:
            self.is_blinking = True
            self.blink_progress = 0.0
            self.blink_direction = 1
            self.blink_anim_timer.start()
            self.blink_timer.setInterval(random.randint(3500, 6500))

    def animate_blink(self):
        if self.blink_direction == 1:
            self.blink_progress += 0.28
            if self.blink_progress >= 1.0:
                self.blink_progress = 1.0
                self.blink_direction = -1
        else:
            self.blink_progress -= 0.28
            if self.blink_progress <= 0.0:
                self.blink_progress = 0.0
                self.is_blinking = False
                self.blink_anim_timer.stop()
        self.update()

    def get_char_for_vk(self, vk):
        """Translate virtual key code into character taking Shift and CapsLock into account."""
        if not user32:
            return None
        if vk == 0x20:
            return " "
        if 0x60 <= vk <= 0x69:
            return str(vk - 0x60)
        if vk == 0x6A: return "*"
        if vk == 0x6B: return "+"
        if vk == 0x6D: return "-"
        if vk == 0x6E: return "."
        if vk == 0x6F: return "/"

        kb = (ctypes.c_ubyte * 256)()
        shift_down = bool(user32.GetKeyState(0x10) & 0x8000)
        caps_lock = bool(user32.GetKeyState(0x14) & 1)
        if shift_down:
            kb[0x10] = 0x80
        if caps_lock:
            kb[0x14] = 0x01

        buf = (ctypes.c_wchar * 4)()
        res = user32.ToUnicode(vk, 0, kb, buf, 4, 0)
        if res > 0 and buf.value:
            return buf.value
        return None

    def update_eye_tracking(self):
        current_pos = QCursor.pos()
        now = time.time()

        # Safety unhover watchdog: recover if cursor left notch/sub-pill but leaveEvent was dropped or missed
        notch_contains = self.geometry().contains(current_pos)
        sub_pill_contains = self.sub_pill.geometry().contains(current_pos) if (hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible()) else False

        if notch_contains or sub_pill_contains:
            self._cursor_outside_start_time = None
        else:
            if self._cursor_outside_start_time is None:
                self._cursor_outside_start_time = now
            elif (now - self._cursor_outside_start_time) > 0.45:
                # Cursor has been outside for >450ms
                if (self._is_hovered or (self.height() > 44 and not getattr(self, "task_peek_active", False))) and not (
                    getattr(self, "is_creating_task", False)
                    or getattr(self, "is_creating_note", False)
                    or getattr(self, "ai_chat_in_notch", False)
                    or getattr(self, "media_in_notch", False)
                    or getattr(self, "dictation_in_notch", False)
                    or getattr(self, "app_search_in_notch", False)
                    or getattr(self, "empty_notes_showing", False)
                    or getattr(self, "timer_is_running", False)
                    or getattr(self, "add_expanded", False)
                    or getattr(self, "task_peek_active", False)
                    or getattr(self, "time_peek_active", False)
                    or getattr(self, "task_collapsing", False)
                    or getattr(self, "active_reminder_alert", None) is not None
                    or getattr(self, "active_update_alert", None) is not None
                    or (hasattr(self, "task_peek_restore_timer") and self.task_peek_restore_timer.isActive())
                    or (hasattr(self, "time_peek_restore_timer") and self.time_peek_restore_timer.isActive())
                    or (hasattr(self, "sub_pill_leave_timer") and self.sub_pill_leave_timer.isActive())
                    or (hasattr(self, "unhover_collapse_timer") and self.unhover_collapse_timer.isActive())
                    or (hasattr(self, "timer_stopped_collapse_timer") and self.timer_stopped_collapse_timer.isActive())
                ):
                    self._cursor_outside_start_time = None
                    self.collapse_to_idle()

        # Keystroke polling for live typed character capture (only letters, numbers, symbols)
        if user32:
            ctrl_down = bool(user32.GetAsyncKeyState(0x11) & 0x8000)
            alt_down = bool(user32.GetAsyncKeyState(0x12) & 0x8000)
            win_down = bool((user32.GetAsyncKeyState(0x5B) & 0x8000) or (user32.GetAsyncKeyState(0x5C) & 0x8000))

            any_key_down = False

            if not self._is_hovered and not self.is_creating_task and not self.timer_in_notch and not getattr(self, "ai_chat_in_notch", False) and not getattr(self, "media_in_notch", False) and not getattr(self, "dictation_in_notch", False) and not getattr(self, "app_search_in_notch", False) and not (ctrl_down or alt_down or win_down):
                for vk in TYPING_KEYS:
                    is_down = bool(user32.GetAsyncKeyState(vk) & 0x8000)
                    was_down = self.key_states.get(vk, False)

                    if is_down:
                        any_key_down = True
                        is_new_press = not was_down
                        is_repeat = (
                            was_down
                            and (now - self.key_down_time.get(vk, now) > 0.45)
                            and (now - self.last_repeat_time > 0.08)
                        )

                        if is_new_press or is_repeat:
                            if (self.time_peek_active or self.task_peek_active or 
                                self.expression_active or self.target_flat_eyes > 0 or 
                                self.target_half_closed > 0 or self.override_pupil or 
                                abs(self.target_eyes_offset_x) > 0.1):
                                self.cancel_idle_animations()
                                if (self.width() != self.idle_w or self.height() != self.idle_h) and not self._is_hovered:
                                    self.animate_to(self.idle_w, self.idle_h)

                            self.last_key_time = now
                            self.is_typing = True
                            if is_new_press:
                                self.key_down_time[vk] = now
                            if is_repeat:
                                self.last_repeat_time = now

                            # Process key effect: Backspace or Character
                            if vk == 0x08:  # Backspace
                                self.typed_text = self.typed_text[:-1]
                            else:
                                ch = self.get_char_for_vk(vk)
                                if ch:
                                    self.typed_text = (self.typed_text + ch)[-16:]
                    else:
                        if vk in self.key_down_time:
                            del self.key_down_time[vk]

                    self.key_states[vk] = is_down

            if any_key_down:
                self.last_key_time = now
            elif self.is_typing:
                # Stop typing after brief typing pause (>0.40s)
                if now - self.last_key_time > 0.40:
                    self.is_typing = False
                    self.key_states.clear()
                    self.key_down_time.clear()

        # Smoothly update typing transition blend
        if self.is_typing:
            self.typing_blend = min(1.0, self.typing_blend + 0.18)
        else:
            self.typing_blend = max(0.0, self.typing_blend - 0.14)
            if self.typing_blend <= 0.0:
                self.typed_text = ""
                self.scroll_x = 0.0

        # Update smooth idle animation transitions (tuned for 60 fps)
        if self.time_peek_active:
            self.time_peek_val = min(1.0, self.time_peek_val + 0.08)
        else:
            self.time_peek_val = max(0.0, self.time_peek_val - 0.08)

        # Smooth lerp interpolation of eye expression and position parameters (tuned for 60 fps)
        self.current_left_eye_scale_x += (self.target_left_eye_scale_x - self.current_left_eye_scale_x) * 0.14
        self.current_left_eye_scale_y += (self.target_left_eye_scale_y - self.current_left_eye_scale_y) * 0.14
        self.current_right_eye_scale_x += (self.target_right_eye_scale_x - self.current_right_eye_scale_x) * 0.14
        self.current_right_eye_scale_y += (self.target_right_eye_scale_y - self.current_right_eye_scale_y) * 0.14
        self.current_flat_eyes += (self.target_flat_eyes - self.current_flat_eyes) * 0.16
        self.current_half_closed += (self.target_half_closed - self.current_half_closed) * 0.14
        if not self.task_peek_active:
            self.eyes_offset_x += (self.target_eyes_offset_x - self.eyes_offset_x) * 0.14
            self.task_peek_opacity = max(0.0, self.task_peek_opacity - 0.12)
        self.eyes_scroll_y += (self.target_eyes_scroll_y - self.eyes_scroll_y) * 0.14

        # Check mouse motion
        dx_mouse = current_pos.x() - self.last_mouse_pos.x()
        dy_mouse = current_pos.y() - self.last_mouse_pos.y()
        mouse_moved = (dx_mouse * dx_mouse + dy_mouse * dy_mouse) >= 4  # >= 2px threshold

        if mouse_moved:
            self.last_mouse_pos = current_pos
            self.last_mouse_move_time = now
            self.idle_expression_triggered = False

            # Eye movement with mouse movement animation takes priority over eye expressions!
            # If an eye expression was active (semi-closed, looking here and there, etc.),
            # immediately cancel it so the eyes follow the cursor without interruption.
            if self.expression_active:
                self.expression_restore_timer.stop()
                self.reset_expression()

        idle_duration = now - self.last_mouse_move_time

        # Prioritize eye expressions AFTER the eye movement with mouse movement animation:
        # When mouse has settled (idle >= 1.8s) and notch is in ground state, trigger eye expressions!
        if idle_duration >= 1.8 and not getattr(self, "idle_expression_triggered", False):
            self.idle_expression_triggered = True
            if not (self._is_hovered or self.is_typing or self.is_creating_task or 
                    self.time_peek_active or self.task_peek_active or self.expression_active or
                    self.timer_in_notch or self.timer_is_running):
                self.trigger_random_expression()

        # Target pupil position
        if self.override_pupil:
            target_x = self.override_pupil_x
            target_y = self.override_pupil_y
        elif idle_duration >= 3.0:
            target_x = 0.0
            target_y = 0.0
        else:
            # Target direction towards mouse cursor
            notch_center = self.mapToGlobal(QPoint(self.width() // 2, self.height() // 2))
            dx = current_pos.x() - notch_center.x()
            dy = current_pos.y() - notch_center.y()
            dist = (dx * dx + dy * dy) ** 0.5

            if dist < 2.0:
                target_x = 0.0
                target_y = 0.0
            else:
                max_shift = 3.2
                factor = min(1.0, dist / 350.0)
                target_x = (dx / dist) * max_shift * factor
                target_y = (dy / dist) * max_shift * factor

        # Smooth lerp interpolation towards target (tuned for 60 fps)
        self.pupil_x += (target_x - self.pupil_x) * 0.16
        self.pupil_y += (target_y - self.pupil_y) * 0.16

        self.update()

    def get_formatted_timer_time(self) -> str:
        """Format timer_ms into HH:MM:SS string."""
        hours = self.timer_ms // 3600000
        mins = (self.timer_ms % 3600000) // 60000
        secs = (self.timer_ms % 60000) // 1000
        return f"{hours:02d}:{mins:02d}:{secs:02d}"

    def _on_notch_stopwatch_tick(self):
        """Called every second while timer is running."""
        if self.timer_is_running:
            self.timer_ms += 1000
            self.ensure_stays_on_top()
            self.update()

    def _on_timer_time_peek_trigger(self):
        """Periodically triggers a brief peek of current time/date alongside the running timer."""
        if not self.timer_is_running or self.timer_time_peek_active:
            return
        if getattr(self, "is_creating_reminder", False):
            return
        self.timer_time_peek_active = True
        self.update_notch_timer_geometry()
        self.timer_peek_restore_timer.start(3500)

    def _on_timer_time_peek_end(self):
        """Hides the time/date peek again to restore pure focus on the timer."""
        self.timer_time_peek_active = False
        if not getattr(self, "is_creating_reminder", False):
            self.update_notch_timer_geometry()
        if self.timer_is_running and not getattr(self, "is_creating_reminder", False):
            self.timer_peek_scheduler.setInterval(random.randint(12000, 20000))
            self.timer_peek_scheduler.start()

    def _on_timer_stopped_collapse_timeout(self):
        """Called after timer was stopped to return back to ground stage and reset."""
        if not self.timer_is_running:
            cursor_pos = QCursor.pos()
            notch_contains = self.geometry().contains(cursor_pos)
            sub_pill_contains = self.sub_pill.geometry().contains(cursor_pos) if (hasattr(self, "sub_pill") and self.sub_pill.isVisible()) else False
            if not (notch_contains or sub_pill_contains):
                if getattr(self, "media_in_notch", False):
                    # The player stays open; only the timer row folds away
                    self.drop_timer_row()
                else:
                    self.collapse_to_idle()

    def _suspend_media_for_creation(self):
        """Hide the media row while the user creates a task/note/reminder; it returns after."""
        if not getattr(self, "media_in_notch", False):
            return
        self._clear_media_in_notch()
        self.media_suspended = True
        if hasattr(self, "sub_pill") and self.sub_pill and hasattr(self.sub_pill.toolbar, "btn_music"):
            # Highlight stays on so the player reads as paused-behind, not closed
            self.sub_pill.toolbar.btn_music.setActive(True)

    def _resume_suspended_media(self):
        """Called when a creation flow ends: re-open the media player if it was open before."""
        if not getattr(self, "media_suspended", False):
            return
        if self.is_creating_task or self.is_creating_note or getattr(self, "is_creating_reminder", False):
            return
        self.media_suspended = False
        QTimer.singleShot(0, self._reopen_suspended_media)

    def _reopen_suspended_media(self):
        if getattr(self, "active_reminder_alert", None) is not None:
            return
        if getattr(self, "active_update_alert", None) is not None:
            return
        self.show_media_in_notch()

    def _clear_media_in_notch(self):
        """Stop the media player row: polling, timeline, hit rects and sub-pill highlight."""
        self.media_in_notch = False
        self.media_suspended = False
        self._media_row_left_x = 0.0
        if hasattr(self, "media_poll_timer"):
            self.media_poll_timer.stop()
        if hasattr(self, "media_timeline_timer"):
            self.media_timeline_timer.stop()
        self.hover_media_prev = False
        self.hover_media_play = False
        self.hover_media_next = False
        self.hover_media_close = False
        self.media_prev_rect = QRect()
        self.media_play_rect = QRect()
        self.media_next_rect = QRect()
        self.media_close_rect = QRect()
        self.media_block_rect = QRect()
        if hasattr(self, "sub_pill") and self.sub_pill and hasattr(self.sub_pill.toolbar, "btn_music"):
            self.sub_pill.toolbar.btn_music.setActive(False)

    def _exit_conflicting_modes(self, entering_mode: str):
        """
        Cleanly exits any currently active conflicting notch mode
        before transitioning into entering_mode
        ('ai_chat', 'notes', 'timer', 'tasks', 'creation', 'dictation', 'idle').
        """
        # 0. Exit voice dictation mode
        if getattr(self, "dictation_in_notch", False) and entering_mode != "dictation":
            self.dictation_in_notch = False
            self.dictation_levels = []
            self.dictation_partial = ""
            self.hover_dictation_cancel = False
            self.dictation_cancel_rect = QRect()
            if hasattr(self, "dictation_service") and self.dictation_service.is_active:
                self.dictation_service.cancel()

        # 1. Exit AI chat mode
        if getattr(self, "ai_chat_in_notch", False) and entering_mode != "ai_chat":
            self.ai_chat_in_notch = False
            self.ai_is_thinking = False
            self.ai_is_listening = False
            self.hover_ai_close = False
            self.hover_ai_task_cb = False
            self.notch_ai_close_rect = QRect()
            self.notch_ai_task_cb_rect = QRect()
            if hasattr(self, "_ai_thinking_timer"):
                self._ai_thinking_timer.stop()
            if hasattr(self, "_ai_response_reset_timer"):
                self._ai_response_reset_timer.stop()
            self.override_pupil = False
            self.override_pupil_x = 0.0
            self.override_pupil_y = 0.0
            self.target_half_closed = 0.0
            self.target_flat_eyes = 0.0
            self.target_left_eye_scale_x = 1.0
            self.target_left_eye_scale_y = 1.0
            self.target_right_eye_scale_x = 1.0
            self.target_right_eye_scale_y = 1.0
            if hasattr(self, "ai_chat_widget") and self.ai_chat_widget:
                if hasattr(self.ai_chat_widget, "is_recording") and self.ai_chat_widget.is_recording:
                    self.ai_chat_widget.stop_voice_recording()
                self.ai_chat_widget.hide()

        # 2. Exit Notes Grid mode
        if getattr(self, "notes_in_notch", False) and entering_mode != "notes":
            self.notes_in_notch = False
            self.empty_notes_showing = False
            if hasattr(self, "empty_notes_restore_timer"):
                self.empty_notes_restore_timer.stop()
            self.notch_note_rects = []
            self.notch_note_copy_rects = []
            self.copied_note_idx = None
            self.hovered_note_card_idx = None
            self.hovered_note_copy_idx = None

        # 3. Exit Tasks List mode
        if getattr(self, "tasks_in_notch", False) and entering_mode != "tasks":
            self.tasks_in_notch = False
            self.notch_task_scroll = 0.0
            self.notch_task_rects = []
            self.notch_task_cb_rects = []
            self.notch_task_play_rects = []
            self.hovered_task_idx = None
            self.hovered_task_cb_idx = None
            self.hovered_task_play_idx = None

        # 4. Exit Creation mode
        if (getattr(self, "is_creating_task", False) or getattr(self, "is_creating_note", False)) and entering_mode != "creation":
            self.is_creating_task = False
            self.is_creating_note = False
            if hasattr(self, "task_input_edit"):
                self.task_input_edit.hide()
                self.task_input_edit.clear()
            if hasattr(self, "note_input_edit"):
                self.note_input_edit.hide()
                self.note_input_edit.clear()

        # 5. Exit Timer mode (if not running) — the media player keeps a timer row open
        if getattr(self, "timer_in_notch", False) and entering_mode not in ("timer", "media"):
            if not self.timer_is_running:
                self.timer_in_notch = False
                self.timer_task_title = None
                self.timer_ms = 0
                if hasattr(self, "timer_stopped_collapse_timer"):
                    self.timer_stopped_collapse_timer.stop()

        # 6. Exit Media Player mode — coexists with the timer row, exits every other mode
        if getattr(self, "media_in_notch", False) and entering_mode not in ("media", "timer"):
            self._clear_media_in_notch()

        # 7. Exit Reminders mode
        if getattr(self, "reminders_in_notch", False) and entering_mode != "reminders":
            self.reminders_in_notch = False
            self.is_creating_reminder = False
            self.empty_reminders_showing = False
            if hasattr(self, "empty_reminders_restore_timer"):
                self.empty_reminders_restore_timer.stop()
            if hasattr(self, "reminder_title_edit"):
                self.reminder_title_edit.hide()
                self.reminder_title_edit.clear()
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.hide()
            if hasattr(self, "sub_pill") and self.sub_pill and hasattr(self.sub_pill, "btn_reminders"):
                self.sub_pill.btn_reminders.setActive(False)

        # 8. Exit App Search mode
        if getattr(self, "app_search_in_notch", False) and entering_mode != "app_search":
            self.app_search_in_notch = False
            if hasattr(self, "app_search_widget") and self.app_search_widget:
                self.app_search_widget.hide()
                self.app_search_widget.reset_state()

        # 0. High priority exit for reminder alert (takes priority over everything)
        if entering_mode == "reminder_alert":
            if getattr(self, "timer_in_notch", False):
                self.timer_in_notch = False
                self.timer_is_running = False
                if hasattr(self, "notch_stopwatch_timer"):
                    self.notch_stopwatch_timer.stop()
                if hasattr(self, "timer_stopped_collapse_timer"):
                    self.timer_stopped_collapse_timer.stop()
            if getattr(self, "dictation_in_notch", False):
                self.dictation_in_notch = False
                if hasattr(self, "dictation_abort_timer"):
                    self.dictation_abort_timer.stop()

        # 8. Exit Reminder Alert mode
        if getattr(self, "active_reminder_alert", None) is not None and entering_mode != "reminder_alert":
            self.active_reminder_alert = None
            self.reminder_dismiss_rect = QRect()
            self.reminder_snooze_rect = QRect()
            self.reminder_done_rect = QRect()
            self.hover_reminder_dismiss = False
            self.hover_reminder_snooze = False
            self.hover_reminder_done = False

        # 9. Exit Update Alert mode (a due reminder outranks an available update)
        if getattr(self, "active_update_alert", None) is not None and entering_mode != "update_alert":
            self._clear_update_alert_state()

    def _clear_update_alert_state(self):
        """Resets update alert presentation without touching geometry."""
        self.active_update_alert = None
        self.update_alert_status = "available"
        self.update_alert_detail = ""
        self.update_now_rect = QRect()
        self.update_later_rect = QRect()
        self.hover_update_now = False
        self.hover_update_later = False

    def toggle_notch_timer_standalone(self):
        """Spawns standalone timer in the notch (replacing task if present). Does NOT auto-start."""
        self._exit_conflicting_modes("timer")
        if self.timer_in_notch and self.timer_task_title is None and not self.timer_is_running:
            if getattr(self, "media_in_notch", False):
                self.drop_timer_row()
                return
            self.collapse_to_idle(force=True)
            return

        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)

        self.timer_in_notch = True
        self.timer_task_title = None
        self.timer_is_running = False
        self.timer_ms = 0
        self.timer_time_peek_active = False
        self.notch_stopwatch_timer.stop()
        self.timer_peek_scheduler.stop()
        self.timer_peek_restore_timer.stop()
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.start(5000)
        self._is_hovered = True
        self.cancel_idle_animations()
        self.update_notch_timer_geometry()
        self.ensure_stays_on_top()
        self.update()

    def toggle_notch_timer_playback(self):
        """Toggle play/pause for active timer in notch."""
        self.timer_is_running = not self.timer_is_running
        if self.timer_is_running:
            if hasattr(self, "timer_stopped_collapse_timer"):
                self.timer_stopped_collapse_timer.stop()
            self.notch_stopwatch_timer.start(1000)
            self.timer_peek_scheduler.start(random.randint(12000, 20000))
        else:
            self.notch_stopwatch_timer.stop()
            self.timer_peek_scheduler.stop()
            self.timer_peek_restore_timer.stop()
            self.timer_time_peek_active = False
            # When stopped, return back to ground stage after 2.5s delay resetting the timer
            if hasattr(self, "timer_stopped_collapse_timer"):
                self.timer_stopped_collapse_timer.start(2500)

        if self.timer_task_title:
            self.is_active_focus = self.timer_is_running
            if self.main_window and hasattr(self.main_window, "toolbar") and self.main_window.toolbar:
                if self.timer_is_running:
                    self.main_window.toolbar.start_stopwatch_for_task()
                else:
                    self.main_window.toolbar.stop_stopwatch()

        self.update_notch_timer_geometry()
        self.ensure_stays_on_top()
        self.update()

    def restart_notch_timer(self):
        """Restart timer back to 00:00:00."""
        self.timer_ms = 0
        if not self.timer_is_running:
            if hasattr(self, "timer_stopped_collapse_timer"):
                self.timer_stopped_collapse_timer.start(2500)
        self.ensure_stays_on_top()
        self.update()

    def update_notch_timer_geometry(self):
        """Resize notch to fit active timer and controls smoothly."""
        if getattr(self, "is_creating_reminder", False) and getattr(self, "reminders_in_notch", False):
            # Reminder creation owns the geometry while it is open
            self.ensure_stays_on_top()
            return
        target_w = self.calc_notch_timer_width()
        target_h = self.expanded_row_height()
        if self.is_creating_task:
            target_h = max(104, target_h)
        self.animate_to(target_w, target_h)
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill._refresh_active_highlights()
        self.ensure_stays_on_top()

    # ------------------------------------------------------------------
    # Clock style (classic / casio / minimal / neon)
    # ------------------------------------------------------------------
    CLOCK_STYLE_SPECS = {
        "classic": {},
        "casio":   {"time_family": "DSEG7 Classic", "time_weight": QFont.Weight.Normal,
                    "time_scale": 0.78, "accent": True, "date_spacing": 2.0,
                    "date_format": "ddd  MMM d"},
        "minimal": {"show_date": False},
        "neon":    {"accent": True},
    }

    def clock_style_spec(self):
        """Resolve the selected clock style into drawing attributes."""
        spec = {
            "time_family": config.load_font_family("DM Sans"),
            "time_weight": QFont.Weight.Bold,
            "time_scale": 1.0,
            "accent": False,
            "show_date": True,
            "date_format": "ddd, MMM d",
            "date_spacing": 0.5,
        }
        spec.update(self.CLOCK_STYLE_SPECS.get(theme.CLOCK_STYLE, {}))
        return spec

    def make_clock_fonts(self, time_pt, date_pt):
        """Time and date fonts for the current clock style."""
        spec = self.clock_style_spec()
        family = config.load_font_family("DM Sans")

        font_time = QFont()
        font_time.setFamilies([spec["time_family"], family, "Segoe UI", "Arial", "sans-serif"])
        font_time.setPointSizeF(time_pt * spec["time_scale"])
        font_time.setWeight(spec["time_weight"])

        font_date = QFont()
        font_date.setFamilies([family, "Segoe UI", "Arial", "sans-serif"])
        font_date.setPointSizeF(date_pt)
        font_date.setWeight(QFont.Weight.Medium)
        font_date.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spec["date_spacing"])
        return font_time, font_date

    def clock_time_string(self, now, use_24h, show_sec):
        if show_sec:
            return now.toString("HH:mm:ss" if use_24h else "hh:mm:ss AP")
        return now.toString("HH:mm" if use_24h else "hh:mm AP")

    def clock_date_visible(self, spec=None):
        return (spec or self.clock_style_spec())["show_date"] and config.load_show_date(True)

    def clock_date_string(self, now, spec=None):
        return now.toString((spec or self.clock_style_spec())["date_format"]).upper()

    def clock_time_color(self, accent_color, opacity=None, spec=None):
        color = QColor(accent_color) if (spec or self.clock_style_spec())["accent"] else QColor(theme.TEXT_PRIMARY)
        if opacity is not None:
            color.setAlphaF(opacity)
        return color

    def calc_time_box_width(self):
        """Calculates width of the [Time + Date Box] widget."""
        font_time, font_date = self.make_clock_fonts(10, 8)
        spec = self.clock_style_spec()

        now = QDateTime.currentDateTime()
        use_24h = config.load_use_24h(True)
        show_sec = config.load_show_seconds(True)
        show_date = self.clock_date_visible(spec)

        time_str = self.clock_time_string(now, use_24h, show_sec)
        full_date = self.clock_date_string(now, spec)

        fm_time = QFontMetrics(font_time)
        w_time = float(fm_time.horizontalAdvance(time_str))
        fm_date = QFontMetrics(font_date)
        w_date = float(fm_date.horizontalAdvance(full_date)) if show_date else 0.0

        show_box = theme.CLOCK_BOX_BG
        time_content_w = max(w_time, w_date)
        return (time_content_w + 20.0) if show_box else time_content_w

    def calc_notch_timer_width(self):
        """Calculate dynamic width for notch when timer is displayed."""
        show_time = ((not self.timer_is_running) or self.timer_time_peek_active) and not getattr(self, "is_creating_reminder", False)
        time_box_w = self.calc_time_box_width() if show_time else 0.0

        gap_elements = 12.0
        margin_x = 22.0

        font_family = config.load_font_family("DM Sans")
        font_time, _ = self.make_clock_fonts(10, 8)
        fm_timer = QFontMetrics(font_time)
        timer_time_str = self.get_formatted_timer_time()
        w_timer_text = float(fm_timer.horizontalAdvance(timer_time_str))

        if self.timer_task_title:
            font_task = QFont()
            font_task.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
            font_task.setPointSize(9)
            font_task.setWeight(QFont.Weight.Medium)
            fm_task = QFontMetrics(font_task)
            max_task_text_w = 180.0
            elided = fm_task.elidedText(self.timer_task_title, Qt.TextElideMode.ElideRight, int(max_task_text_w))
            w_task_text = float(fm_task.horizontalAdvance(elided))

            cb_size = 18.0
            cb_gap = 10.0
            play_size = 20.0
            restart_size = 18.0
            card_pad_h = 14.0
            card_w = card_pad_h + cb_size + cb_gap + w_task_text + 10.0 + w_timer_text + 8.0 + restart_size + 8.0 + play_size + card_pad_h
        else:
            play_size = 20.0
            restart_size = 18.0
            card_pad_h = 14.0
            card_w = 12.0 + play_size + 8.0 + restart_size + 10.0 + w_timer_text + card_pad_h

        capsule_w = 184.0
        add_btn_size = 28.0

        add_w = capsule_w if self.add_expanded else add_btn_size
        total_content_w = (time_box_w + gap_elements if show_time else 0.0) + card_w + gap_elements + add_w
        total_w = int(total_content_w + (margin_x * 2.0))

        if self.notes_in_notch and not getattr(self, "empty_notes_showing", False):
            return int(max(570, total_w + 40))
        if self.is_creating_note:
            return int(max(480, total_w + 50))

        min_w = 390 if self.add_expanded else 240
        if getattr(self, "media_in_notch", False):
            # [22] timer row [16] media block [20] — mirrors the combined row painting
            return int(total_content_w + margin_x + self.MEDIA_TIMER_GAP + self.media_block_width() + self.MEDIA_EDGE_MARGIN)
        return int(max(min_w, total_w))

    def calc_expanded_width(self):
        """Calculates dynamic notch width based on the active task title and clock style."""
        if self.notes_in_notch and not getattr(self, "empty_notes_showing", False):
            return 570
        if self.is_creating_note:
            return 480
        if self.timer_in_notch:
            return self.calc_notch_timer_width()

        font_family = config.load_font_family("DM Sans")

        font_time, font_date = self.make_clock_fonts(10, 8)

        font_task = QFont()
        font_task.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
        font_task.setPointSize(9)
        font_task.setWeight(QFont.Weight.Medium)

        now = QDateTime.currentDateTime()
        use_24h = config.load_use_24h(True)
        show_sec = config.load_show_seconds(True)
        show_date = self.clock_date_visible()

        time_str = self.clock_time_string(now, use_24h, show_sec)
        full_date = self.clock_date_string(now)

        fm_time = QFontMetrics(font_time)
        w_time = float(fm_time.horizontalAdvance(time_str))

        fm_date = QFontMetrics(font_date)
        w_date = float(fm_date.horizontalAdvance(full_date)) if show_date else 0.0

        show_box = theme.CLOCK_BOX_BG
        time_content_w = max(w_time, w_date)
        time_box_w = (time_content_w + 20.0) if show_box else time_content_w

        add_btn_size = 28.0
        margin_x = 22.0
        gap_elements = 12.0

        if self.current_random_task:
            fm_task = QFontMetrics(font_task)
            display_task = self.current_random_task
            max_task_text_w = 220.0
            elided_task = fm_task.elidedText(display_task, Qt.TextElideMode.ElideRight, int(max_task_text_w))
            w_task_text = float(fm_task.horizontalAdvance(elided_task))

            cb_size = 18.0
            cb_gap = 10.0
            play_size = 20.0
            play_gap = 10.0
            card_pad_h = 14.0

            task_card_w = card_pad_h + cb_size + cb_gap + w_task_text + play_gap + play_size + card_pad_h
            total_content_w = time_box_w + gap_elements + task_card_w + gap_elements + add_btn_size
            target_w = int(total_content_w + (margin_x * 2.0))
            return max(320, target_w)
        else:
            total_content_w = time_box_w + gap_elements + add_btn_size
            target_w = int(total_content_w + (margin_x * 2.0))
            return max(180, target_w)

    def _on_reminder_title_return(self):
        if hasattr(self, "reminder_widget") and self.reminder_widget and hasattr(self.reminder_widget, "creator"):
            self.reminder_widget.creator._on_confirm()

    def calc_add_expanded_width(self):
        """Calculates notch width when Add button is expanded into capsule [Task] [Note] [Reminder] [x]."""
        if getattr(self, "empty_reminders_showing", False):
            return max(260, self.calc_expanded_width())
        if self.notes_in_notch:
            if getattr(self, "empty_notes_showing", False):
                return max(260, self.calc_expanded_width())
            return 570
        if self.is_creating_note:
            return 480
        if self.timer_in_notch:
            return self.calc_notch_timer_width()

        font_time, font_date = self.make_clock_fonts(10, 8)

        now = QDateTime.currentDateTime()
        use_24h = config.load_use_24h(True)
        show_sec = config.load_show_seconds(True)
        show_date = self.clock_date_visible()

        time_str = self.clock_time_string(now, use_24h, show_sec)
        full_date = self.clock_date_string(now)

        fm_time = QFontMetrics(font_time)
        w_time = float(fm_time.horizontalAdvance(time_str))
        fm_date = QFontMetrics(font_date)
        w_date = float(fm_date.horizontalAdvance(full_date)) if show_date else 0.0

        show_box = theme.CLOCK_BOX_BG
        time_content_w = max(w_time, w_date)
        time_box_w = (time_content_w + 20.0) if show_box else time_content_w

        capsule_w = 184.0
        gap_elements = 14.0
        margin_x = 22.0

        total_content_w = time_box_w + gap_elements + capsule_w
        target_w = int(total_content_w + (margin_x * 2.0))
        return max(340, target_w)

    def update_task_input_geometry(self):
        margin_x = 22
        input_card_w = self.width() - (margin_x * 2)
        cb_x = margin_x + 14
        edit_x = cb_x + 18 + 10
        edit_w = input_card_w - (edit_x - margin_x) - 14
        self.task_input_edit.setGeometry(edit_x, 60, max(50, edit_w), 28)

    def update_note_input_geometry(self):
        margin_x = 22
        card_w = self.width() - (margin_x * 2)
        edit_x = margin_x + 12
        edit_w = card_w - 24
        edit_y = 56
        edit_h = max(30, self.height() - edit_y - 16)
        self.note_input_edit.setGeometry(edit_x, edit_y, max(50, edit_w), edit_h)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.is_creating_task:
            self.update_task_input_geometry()
        if self.is_creating_note:
            self.update_note_input_geometry()
        if getattr(self, "ai_chat_in_notch", False):
            self.update_ai_chat_geometry()
        if getattr(self, "reminders_in_notch", False):
            self.update_reminder_geometry()

    def _suspend_reminders_list_for_creation(self):
        """Hide the reminders list child while a task/note editor owns the extended area."""
        if getattr(self, "reminders_in_notch", False) and not getattr(self, "is_creating_reminder", False) \
                and not getattr(self, "empty_reminders_showing", False):
            self._reminders_list_suspended = True
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.hide()

    def _restore_reminders_list(self):
        """Put the reminders list back after a creation flow opened over it."""
        if not getattr(self, "_reminders_list_suspended", False):
            return
        self._reminders_list_suspended = False
        if not getattr(self, "reminders_in_notch", False) or getattr(self, "is_creating_reminder", False) \
                or getattr(self, "empty_reminders_showing", False):
            return
        if hasattr(self, "reminder_widget") and self.reminder_widget:
            self.reminder_widget.show()
            self.reminder_widget.show_list()
        self.update_reminder_geometry()

    def _open_list_stage_size(self):
        """Size of an open tasks/reminders list when the add capsule overlays the header row.

        Returns None when no list stage needs its height preserved.
        """
        if getattr(self, "reminders_in_notch", False) and not getattr(self, "is_creating_reminder", False):
            if getattr(self, "empty_reminders_showing", False):
                # Keep the "No reminders available" line visible under the capsule
                return (max(self.calc_add_expanded_width(), self.calc_expanded_width()), 84)
            return (max(self.calc_add_expanded_width(), self.calc_expanded_width(), 380),
                    self._calc_reminders_notch_height())
        if self.tasks_in_notch and not (self.is_creating_task or self.is_creating_note):
            return (max(self.calc_add_expanded_width(), self.calc_expanded_width(), 380),
                    self._calc_tasks_notch_height())
        return None

    def _route_add_click(self, pos):
        """Handle a click on the add button or the expanded capsule. True when consumed."""
        if self.add_expanded:
            if self.add_toggle_rect.contains(pos):
                self.collapse_add_mode()
                return True
            if self.sub_task_rect.contains(pos):
                self.start_notch_task_creation()
                return True
            if self.sub_note_rect.contains(pos):
                self.start_notch_note_creation()
                return True
            if self.sub_reminder_rect.contains(pos):
                self.start_notch_reminder_creation()
                return True
            return False
        if self.add_btn_rect.contains(pos):
            self.expand_add_mode()
            return True
        return False

    def _add_capsule_hover(self, pos):
        """Hover flags for the add button and its capsule; True when a control is under the cursor."""
        if not self.add_expanded:
            in_add = self.add_btn_rect.contains(pos)
            if in_add != self.hover_add_btn:
                self.hover_add_btn = in_add
                self.update()
            return in_add

        new_sub_task = self.sub_task_rect.contains(pos)
        new_sub_note = self.sub_note_rect.contains(pos)
        new_sub_reminder = self.sub_reminder_rect.contains(pos)
        new_toggle = self.add_toggle_rect.contains(pos)
        if (new_sub_task != self.hover_sub_task or new_sub_note != self.hover_sub_note or
                new_sub_reminder != self.hover_sub_reminder or new_toggle != self.hover_add_btn):
            self.hover_sub_task = new_sub_task
            self.hover_sub_note = new_sub_note
            self.hover_sub_reminder = new_sub_reminder
            self.hover_add_btn = new_toggle
            self.update()
        return new_sub_task or new_sub_note or new_sub_reminder or new_toggle

    def expand_add_mode(self):
        self.unhover_collapse_timer.stop()
        self.add_expanded = True
        self.add_expand_anim.stop()
        self.add_expand_anim.setStartValue(self._add_expand_progress)
        self.add_expand_anim.setEndValue(1.0)
        self.add_expand_anim.start()
        stage = None if self.timer_in_notch else self._open_list_stage_size()
        if stage:
            self.animate_to(stage[0], stage[1])
            return
        target_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_add_expanded_width()
        self.animate_to(target_w, self.expanded_row_height())

    def collapse_add_mode(self):
        self.unhover_collapse_timer.stop()
        self.add_expanded = False
        self.is_creating_task = False
        self.is_creating_note = False
        self.hover_sub_reminder = False
        self.sub_reminder_rect = QRect()
        self.editing_note_index = None
        self.hover_note_tick = False
        self.hover_note_cross = False
        self.hover_note_delete = False
        self.note_tick_rect = QRect()
        self.note_cross_rect = QRect()
        self.note_delete_rect = QRect()
        self.task_input_edit.hide()
        self.task_input_edit.clear()
        self.note_input_edit.hide()
        self.note_input_edit.clear()
        self.add_expand_anim.stop()
        self.add_expand_anim.setStartValue(self._add_expand_progress)
        self.add_expand_anim.setEndValue(0.0)
        self.add_expand_anim.start()
        self._restore_reminders_list()
        stage = None if self.timer_in_notch else self._open_list_stage_size()
        if stage:
            # Back to the list the capsule was opened over; show the newest rows first
            self.notch_task_scroll = 0.0
            self.animate_to(stage[0], stage[1])
        else:
            target_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_expanded_width()
            self.animate_to(target_w, self.expanded_row_height())
        self._resume_suspended_media()

    def start_notch_task_creation(self):
        self.unhover_collapse_timer.stop()
        self._suspend_media_for_creation()
        self._suspend_reminders_list_for_creation()
        self.is_creating_task = True
        self.is_creating_note = False
        self.notes_in_notch = False
        self.note_input_edit.hide()
        target_h = 104
        base_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_add_expanded_width()
        target_w = max(420, base_w)
        self.animate_to(target_w, target_h)
        self.update_task_input_geometry()
        self.task_input_edit.show()
        self.task_input_edit.setFocus()

    def submit_notch_task(self):
        self.unhover_collapse_timer.stop()
        text = self.task_input_edit.text().strip()
        if text:
            if self.main_window and hasattr(self.main_window, "tasks"):
                if text not in self.main_window.tasks:
                    self.main_window.tasks.insert(0, text)
                    config.save_tasks(self.main_window.tasks)
                    self.main_window.update_tasks_view()
            else:
                tasks = config.load_tasks()
                if text not in tasks:
                    tasks.insert(0, text)
                    config.save_tasks(tasks)
            self.current_random_task = text
        self.collapse_add_mode()

    def cancel_notch_task(self):
        self.collapse_add_mode()

    def start_notch_note_creation(self):
        """Expand notch vertically and horizontally for inline note creation with combined tick/cross pill."""
        self.unhover_collapse_timer.stop()
        self._suspend_media_for_creation()
        self._suspend_reminders_list_for_creation()
        self.is_creating_task = False
        self.is_creating_note = True
        self.editing_note_index = None
        self.notes_in_notch = False
        self.task_input_edit.hide()
        self.note_input_edit.clear()
        self.note_input_edit.setPlaceholderText("Write your note here... (Ctrl+Enter to save)")
        target_h = 154
        base_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_add_expanded_width()
        target_w = max(480, base_w + 50)
        self.animate_to(target_w, target_h)
        self.update_note_input_geometry()
        self.note_input_edit.show()
        self.note_input_edit.setFocus()

    def start_notch_note_editing(self, index, text):
        """Expand notch vertically and horizontally to edit existing note inline with combined tick/cross pill."""
        self.unhover_collapse_timer.stop()
        self.is_creating_task = False
        self.is_creating_note = True
        self.editing_note_index = index
        self.notes_in_notch = False
        self.task_input_edit.hide()
        self.note_input_edit.setPlaceholderText("Edit your note... (Ctrl+Enter to save)")
        self.note_input_edit.setPlainText(text)
        cursor = self.note_input_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.note_input_edit.setTextCursor(cursor)
        target_h = 154
        base_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_add_expanded_width()
        target_w = max(480, base_w + 50)
        self.animate_to(target_w, target_h)
        self.update_note_input_geometry()
        self.note_input_edit.show()
        self.note_input_edit.setFocus()

    def submit_notch_note(self):
        """Save active note from notch inline editor (new or edited) to config/main_window."""
        self.unhover_collapse_timer.stop()
        text = self.note_input_edit.toPlainText().strip()
        editing_idx = getattr(self, "editing_note_index", None)

        if text:
            if editing_idx is not None:
                # Update existing note at editing_idx
                if self.main_window and hasattr(self.main_window, "notes"):
                    if 0 <= editing_idx < len(self.main_window.notes):
                        self.main_window.notes[editing_idx] = text
                        config.save_notes(self.main_window.notes)
                        if hasattr(self.main_window, "update_tasks_view"):
                            self.main_window.update_tasks_view()
                        elif hasattr(self.main_window, "update_pagination"):
                            self.main_window.update_pagination()
                else:
                    notes = config.load_notes()
                    if 0 <= editing_idx < len(notes):
                        notes[editing_idx] = text
                        config.save_notes(notes)
            else:
                # Add new note
                if self.main_window and hasattr(self.main_window, "notes"):
                    if text not in self.main_window.notes:
                        self.main_window.notes.insert(0, text)
                        config.save_notes(self.main_window.notes)
                        if hasattr(self.main_window, "update_tasks_view"):
                            self.main_window.update_tasks_view()
                        elif hasattr(self.main_window, "update_pagination"):
                            self.main_window.update_pagination()
                else:
                    notes = config.load_notes()
                    if text not in notes:
                        notes.insert(0, text)
                        config.save_notes(notes)

        self.editing_note_index = None
        self.hover_note_tick = False
        self.hover_note_cross = False
        self.hover_note_delete = False
        self.note_tick_rect = QRect()
        self.note_cross_rect = QRect()
        self.note_delete_rect = QRect()
        self.note_input_edit.hide()
        self.note_input_edit.clear()

        if editing_idx is not None:
            self.show_notes_in_notch()
        else:
            self.collapse_add_mode()

    def cancel_notch_note(self):
        """Cancel inline note creation or editing without saving."""
        editing_idx = getattr(self, "editing_note_index", None)
        self.editing_note_index = None
        self.hover_note_tick = False
        self.hover_note_cross = False
        self.hover_note_delete = False
        self.note_tick_rect = QRect()
        self.note_cross_rect = QRect()
        self.note_delete_rect = QRect()
        self.note_input_edit.hide()
        self.note_input_edit.clear()

        if editing_idx is not None:
            self.show_notes_in_notch()
        else:
            self.collapse_add_mode()

    def delete_notch_note(self):
        """Delete currently edited note from storage and return to notes view in notch."""
        self.unhover_collapse_timer.stop()
        editing_idx = getattr(self, "editing_note_index", None)
        if editing_idx is not None:
            if self.main_window and hasattr(self.main_window, "notes"):
                if 0 <= editing_idx < len(self.main_window.notes):
                    self.main_window.notes.pop(editing_idx)
                    config.save_notes(self.main_window.notes)
                    if hasattr(self.main_window, "update_tasks_view"):
                        self.main_window.update_tasks_view()
                    elif hasattr(self.main_window, "update_pagination"):
                        self.main_window.update_pagination()
            else:
                notes = config.load_notes()
                if 0 <= editing_idx < len(notes):
                    notes.pop(editing_idx)
                    config.save_notes(notes)

        self.editing_note_index = None
        self.hover_note_tick = False
        self.hover_note_cross = False
        self.hover_note_delete = False
        self.note_tick_rect = QRect()
        self.note_cross_rect = QRect()
        self.note_delete_rect = QRect()
        self.note_input_edit.hide()
        self.note_input_edit.clear()
        self.show_notes_in_notch()

    # Fixed layout constants for tasks-in-notch
    TASK_VISIBLE_ROWS = 3
    TASK_ITEM_H = 38.0
    TASK_GAP = 6.0
    TASK_EXT_TOP = 58.0
    TASK_ROW_TOP = TASK_EXT_TOP + 5.0

    def _tasks_pitch(self):
        return self.TASK_ITEM_H + self.TASK_GAP

    def _tasks_viewport_height(self):
        """Height of the always-visible scroll window — exactly TASK_VISIBLE_ROWS rows."""
        n = self.TASK_VISIBLE_ROWS
        return n * self.TASK_ITEM_H + (n - 1) * self.TASK_GAP

    def _tasks_content_height(self, count):
        if count <= 0:
            return 0.0
        return count * self.TASK_ITEM_H + (count - 1) * self.TASK_GAP

    def _tasks_max_scroll(self, all_tasks=None):
        if all_tasks is None:
            all_tasks = self._get_tasks_list()
        return max(0.0, self._tasks_content_height(len(all_tasks)) - self._tasks_viewport_height())

    def _calc_tasks_notch_height(self, all_tasks=None):
        """Notch height for the tasks stage — fixed at three visible rows, extras scroll."""
        if all_tasks is None:
            all_tasks = self._get_tasks_list()
        if not all_tasks:
            return int(self.TASK_EXT_TOP + 42.0)
        return int(self.TASK_ROW_TOP + self._tasks_viewport_height() + 14.0)

    def _update_tasks_notch_geometry(self, all_tasks=None):
        target_h = self._calc_tasks_notch_height(all_tasks)
        target_w = max(self.calc_expanded_width(), 380)
        self.animate_to(target_w, target_h)

    def _scroll_tasks_notch(self, delta_px):
        """Slide the tasks list by delta_px; positive scrolls toward the older tasks below."""
        max_scroll = self._tasks_max_scroll()
        new_scroll = max(0.0, min(max_scroll, self.notch_task_scroll + delta_px))
        if abs(new_scroll - self.notch_task_scroll) < 0.01:
            return
        self.notch_task_scroll = new_scroll
        self.update()

    def show_tasks_in_notch(self):
        """Expands notch to show tasks below the header in a fixed three-row window; extra tasks scroll."""
        self._exit_conflicting_modes("tasks")
        self.unhover_collapse_timer.stop()
        self.is_creating_task = False
        self.is_creating_note = False
        self.task_input_edit.hide()
        self.note_input_edit.hide()
        self._is_hovered = True
        self.cancel_idle_animations()
        self.tasks_in_notch = True
        self.notch_task_scroll = 0.0
        self.notch_task_rects = []
        self.notch_task_cb_rects = []
        self.hovered_task_idx = None
        self.hovered_task_cb_idx = None

        all_tasks = self._get_tasks_list()
        self._update_tasks_notch_geometry(all_tasks)
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            self.sub_pill.show()
            self.sub_pill.recenter_under_notch()
        self.update()

    def _get_tasks_list(self):
        if self.main_window and hasattr(self.main_window, "tasks"):
            return list(self.main_window.tasks)
        return config.load_tasks()

    def show_notes_in_notch(self):
        """Expands notch to show notes 3 in a row below the header elements, or a slight vertical extension if no notes."""
        self._exit_conflicting_modes("notes")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "empty_notes_restore_timer"):
            self.empty_notes_restore_timer.stop()

        all_notes = self.get_notes_list()
        self.is_creating_task = False
        self.is_creating_note = False
        self.task_input_edit.hide()
        self.note_input_edit.hide()
        self.notch_notes_page = 0
        self.copied_note_idx = None
        self._is_hovered = True
        self.cancel_idle_animations()

        base_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_expanded_width()
        self.notes_in_notch = True

        if len(all_notes) == 0:
            # If no saved notes: don't expand completely! Just extend vertically a little (h=84)
            # and show plain "No notes available", then return back to hover state after 2.2 seconds.
            self.empty_notes_showing = True
            target_h = 84
            target_w = max(260, base_w)
            self.animate_to(target_w, target_h)
            self.empty_notes_restore_timer.start(2200)
        else:
            self.empty_notes_showing = False
            target_h = 176
            target_w = max(570, base_w + 40)
            self.animate_to(target_w, target_h)
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
                self.sub_pill.show()
                self.sub_pill.recenter_under_notch()

        self.update()

    def _restore_from_empty_notes(self):
        """Restores notch back to hover state (if cursor is still hovering) or idle ground state (if cursor is outside)."""
        self.empty_notes_showing = False
        self.notes_in_notch = False
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
        cursor_pos = QCursor.pos()
        notch_contains = self.geometry().contains(cursor_pos)
        sub_pill_contains = self.sub_pill.geometry().contains(cursor_pos) if (hasattr(self, "sub_pill") and self.sub_pill.isVisible()) else False
        if notch_contains or sub_pill_contains:
            self._is_hovered = True
            target_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_expanded_width()
            self.animate_to(target_w, self.hover_h)
            self.update()
        else:
            self._is_hovered = False
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill.hide_animated()
            self.collapse_to_idle(force=True)

    def show_ai_chat_in_notch(self):
        """Expands notch to show mini AI chat interface with eyes at center top and vertical sub-pill on right."""
        self._exit_conflicting_modes("ai_chat")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        self.cancel_idle_animations()
        self.is_creating_task = False
        self.is_creating_note = False
        self.task_input_edit.hide()
        self.note_input_edit.hide()
        self.tasks_in_notch = False
        self.notes_in_notch = False
        self.add_expanded = False
        self.ai_chat_in_notch = True
        self._is_hovered = True

        target_w = 480
        target_h = 240
        self.animate_to(target_w, target_h)
        self.update_ai_chat_geometry()
        if hasattr(self, "ai_chat_widget") and self.ai_chat_widget:
            self.ai_chat_widget.show()
            self.ai_chat_widget.input_field.setFocus()
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(True)
            self.sub_pill.show()
            self.sub_pill.recenter_under_notch()
        self.update()

    def toggle_ai_chat_in_notch(self):
        """Toggle mini AI chat expansion."""
        if getattr(self, "ai_chat_in_notch", False):
            self.collapse_ai_chat()
        else:
            self.show_ai_chat_in_notch()

    def collapse_ai_chat(self):
        """Collapse mini AI chat and restore idle state."""
        self._exit_conflicting_modes("idle")
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            self.sub_pill.hide_animated()
        self.collapse_to_idle(force=True)

    def start_notch_reminder_creation(self):
        """Called when user clicks [Reminder] in the add expanded capsule."""
        self._suspend_media_for_creation()
        self._exit_conflicting_modes("reminders")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        if hasattr(self, "empty_reminders_restore_timer"):
            self.empty_reminders_restore_timer.stop()
        # Freeze timer peek/collapse relayouts so the notch stays fully open
        # at the creation size until the user saves or cancels
        if hasattr(self, "timer_peek_scheduler"):
            self.timer_peek_scheduler.stop()
        if hasattr(self, "timer_peek_restore_timer"):
            self.timer_peek_restore_timer.stop()
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        self.timer_time_peek_active = False
        self.cancel_idle_animations()
        self.empty_reminders_showing = False
        self.is_creating_task = False
        self.is_creating_note = False
        self.is_creating_reminder = True
        self.tasks_in_notch = False
        self.notes_in_notch = False
        self.task_input_edit.hide()
        self.note_input_edit.hide()
        self.add_expanded = False
        self._reminders_list_suspended = False

        self.reminders_in_notch = True
        self._is_hovered = True

        target_w = 380
        target_h = 148
        self.animate_to(target_w, target_h)
        if hasattr(self, "reminder_widget") and self.reminder_widget:
            self.reminder_widget.show()
            self.reminder_widget.show_creator()
        # Synchronous repaint so reminder_title_area_x (set in paintEvent when a
        # timer is in the notch) is fresh before sizing/positioning the title input
        self.repaint()
        if getattr(self, "timer_in_notch", False):
            area_x = getattr(self, "reminder_title_area_x", 0)
            if area_x > 0:
                # Wide enough for the timer card on the left plus a usable title input
                target_w = max(380, int(area_x) + 220)
                self.animate_to(target_w, target_h)
        self.update_reminder_geometry()
        if hasattr(self, "reminder_title_edit"):
            self.reminder_title_edit.show()
            self.reminder_title_edit.setFocus()
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            self.sub_pill.show()
            self.sub_pill.recenter_under_notch()
            if hasattr(self.sub_pill, "btn_reminders"):
                self.sub_pill.btn_reminders.setActive(True)
        self.update()

    def _calc_reminders_notch_height(self, active_reminders=None):
        """Calculates dynamic height of the notch based on the number of active reminders."""
        if active_reminders is None:
            active_reminders = [r for r in config.load_reminders() if not r.get("completed", False)]
        if not active_reminders:
            return 84
        k = min(4, len(active_reminders))
        header_h = 58.0
        title_h = 24.0   # "Upcoming reminders" title
        items_h = (k * 34.0) + max(0, (k - 1) * 6.0)
        bottom_pad = 14.0
        return int(header_h + title_h + items_h + bottom_pad)

    def _update_reminders_notch_geometry(self):
        """Dynamically adjusts notch height as reminders are completed or deleted."""
        if not getattr(self, "reminders_in_notch", False) or getattr(self, "is_creating_reminder", False):
            return
        active_reminders = [r for r in config.load_reminders() if not r.get("completed", False)]
        base_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_expanded_width()
        if not active_reminders:
            self.empty_reminders_showing = True
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.hide()
            target_h = 84
            target_w = base_w
            self.animate_to(target_w, target_h)
            self.empty_reminders_restore_timer.start(2200)
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
                self.sub_pill.show()
                self.sub_pill.recenter_under_notch()
                if hasattr(self.sub_pill, "btn_reminders"):
                    self.sub_pill.btn_reminders.setActive(True)
        else:
            target_h = self._calc_reminders_notch_height(active_reminders)
            target_w = max(base_w, 380)
            self.animate_to(target_w, target_h)
            self.update_reminder_geometry()

    def show_reminders_in_notch(self):
        """Expands notch to show active reminders list below second hover header, or slightly increases height if none."""
        self._exit_conflicting_modes("reminders")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        if hasattr(self, "empty_reminders_restore_timer"):
            self.empty_reminders_restore_timer.stop()
        self.cancel_idle_animations()
        self.is_creating_task = False
        self.is_creating_note = False
        self.is_creating_reminder = False
        self.tasks_in_notch = False
        self.notes_in_notch = False
        self.task_input_edit.hide()
        self.note_input_edit.hide()
        self.add_expanded = False
        if hasattr(self, "reminder_title_edit"):
            self.reminder_title_edit.hide()

        base_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_expanded_width()
        self.reminders_in_notch = True
        self._reminders_list_suspended = False
        self._is_hovered = True

        all_reminders = config.load_reminders()
        active_reminders = [r for r in all_reminders if not r.get("completed", False)]

        if len(active_reminders) == 0:
            # From second hovered state: slightly increase notch height (h=84), keep same width, show "No reminders available"
            self.empty_reminders_showing = True
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.hide()
            target_h = 84
            target_w = base_w
            self.animate_to(target_w, target_h)
            self.empty_reminders_restore_timer.start(2200)
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
                self.sub_pill.show()
                self.sub_pill.recenter_under_notch()
                if hasattr(self.sub_pill, "btn_reminders"):
                    self.sub_pill.btn_reminders.setActive(True)
        else:
            self.empty_reminders_showing = False
            target_h = self._calc_reminders_notch_height(active_reminders)
            target_w = max(base_w, 380)
            self.animate_to(target_w, target_h)
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.show()
                self.reminder_widget.show_list()
            self.update_reminder_geometry()
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
                self.sub_pill.show()
                self.sub_pill.recenter_under_notch()
                if hasattr(self.sub_pill, "btn_reminders"):
                    self.sub_pill.btn_reminders.setActive(True)

        self.update()

    def _restore_from_empty_reminders(self):
        """Restores notch after showing 'No reminders available'."""
        if getattr(self, "active_reminder_alert", None) is not None:
            return
        self.empty_reminders_showing = False
        self.reminders_in_notch = False
        self.is_creating_reminder = False
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            if hasattr(self.sub_pill, "btn_reminders"):
                self.sub_pill.btn_reminders.setActive(False)
        cursor_pos = QCursor.pos()
        notch_contains = self.geometry().contains(cursor_pos)
        sub_pill_contains = self.sub_pill.geometry().contains(cursor_pos) if (hasattr(self, "sub_pill") and self.sub_pill.isVisible()) else False
        if notch_contains or sub_pill_contains:
            self._is_hovered = True
            target_w = self.calc_notch_timer_width() if self.timer_in_notch else self.calc_expanded_width()
            self.animate_to(target_w, self.hover_h)
            self.update()
        else:
            self._is_hovered = False
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill.hide_animated()
            self.collapse_to_idle(force=True)

    def toggle_reminders_in_notch(self):
        if getattr(self, "reminders_in_notch", False):
            self.collapse_reminders()
        else:
            self.show_reminders_in_notch()

    def collapse_reminders(self):
        self.reminders_in_notch = False
        self.is_creating_reminder = False
        self.empty_reminders_showing = False
        if hasattr(self, "empty_reminders_restore_timer"):
            self.empty_reminders_restore_timer.stop()
        if hasattr(self, "reminder_title_edit"):
            self.reminder_title_edit.hide()
            self.reminder_title_edit.clear()
        if hasattr(self, "reminder_widget") and self.reminder_widget:
            self.reminder_widget.hide()
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            if hasattr(self.sub_pill, "btn_reminders"):
                self.sub_pill.btn_reminders.setActive(False)
        self.collapse_to_idle(force=True)

        # Reminder creation is over: let a still-running timer resume its peek cycle
        if getattr(self, "timer_is_running", False) and self.timer_in_notch:
            if hasattr(self, "timer_peek_scheduler") and not self.timer_peek_scheduler.isActive():
                self.timer_peek_scheduler.start(random.randint(12000, 20000))

        self._resume_suspended_media()

    def finish_reminder_creation(self):
        """Called after a reminder is saved: exit reminders mode and return to
        ground state (hover state if the cursor is still over the notch/sub-pill)."""
        self.collapse_reminders()
        if getattr(self, "timer_in_notch", False):
            # A timer survives reminder creation: settle back into the timer layout
            self.update_notch_timer_geometry()
            return
        cursor_pos = QCursor.pos()
        notch_contains = self.geometry().contains(cursor_pos)
        sub_pill_contains = self.sub_pill.geometry().contains(cursor_pos) if (hasattr(self, "sub_pill") and self.sub_pill.isVisible()) else False
        if notch_contains or sub_pill_contains:
            self._is_hovered = True
            self.animate_to(self.calc_expanded_width(), self.hover_h)
            self.update()

    def update_reminder_geometry(self):
        is_creating = getattr(self, "is_creating_reminder", False) and not getattr(self, "empty_reminders_showing", False)

        if getattr(self, "reminders_in_notch", False) and is_creating:
            margin_x = 20
            area_x = getattr(self, "reminder_title_area_x", 0)
            if getattr(self, "timer_in_notch", False) and area_x > 0:
                title_x = int(area_x)
            else:
                time_w = float(self.time_box_rect.width()) if (hasattr(self, "time_box_rect") and self.time_box_rect.isValid() and self.time_box_rect.width() > 0) else 75.0
                title_x = int(margin_x + time_w + 10)
            top_cy = 27.0 if self.height() >= 54.0 else (self.height() / 2.0)
            title_y = int(top_cy - 18.0)
            title_w = max(100, int(self.width() - title_x - margin_x))
            title_h = 36
            if hasattr(self, "reminder_title_edit"):
                self.reminder_title_edit.setGeometry(title_x, title_y, title_w, title_h)
                self.reminder_title_edit.show()
            top_y = 52
            w = max(100, int(self.width() - (margin_x * 2)))
            h = max(30, int(self.height() - top_y - 10))
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.setGeometry(margin_x, top_y, w, h)
        else:
            if hasattr(self, "reminder_title_edit"):
                self.reminder_title_edit.hide()
            margin_x = 18
            top_y = 58
            w = max(100, int(self.width() - (margin_x * 2)))
            h = max(30, int(self.height() - top_y - 12))
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.setGeometry(margin_x, top_y, w, h)

    def _check_due_reminders(self):
        import datetime
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_hour = now.hour
        current_minute = now.minute

        reminders = config.load_reminders()
        due_reminder = None
        for r in reminders:
            if not r.get("completed", False) and not r.get("notified", False):
                r_date = r.get("date", "")
                r_hr = r.get("hour", 0)
                r_min = r.get("minute", 0)
                if (r_date < current_date) or (r_date == current_date and (r_hr < current_hour or (r_hr == current_hour and r_min <= current_minute))):
                    due_reminder = r
                    break
        if due_reminder and getattr(self, "active_reminder_alert", None) is None:
            due_reminder["notified"] = True
            config.save_reminders(reminders)
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.reminder_list.reload_reminders()
            self._trigger_reminder_alert(due_reminder)

    def _trigger_reminder_alert(self, reminder_data):
        """Displays attention-grabbing alert in notch when a reminder is due with cover icon, time, title, and Snooze/Done buttons."""
        self._exit_conflicting_modes("reminder_alert")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        if hasattr(self, "empty_reminders_restore_timer"):
            self.empty_reminders_restore_timer.stop()
        if hasattr(self, "empty_notes_restore_timer"):
            self.empty_notes_restore_timer.stop()
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        self.empty_reminders_showing = False
        self.cancel_idle_animations()

        self.active_reminder_alert = reminder_data
        self._is_hovered = True

        # Attention blink animation
        self.blink_progress = 0.8
        QTimer.singleShot(250, lambda: setattr(self, "blink_progress", 0.0))

        # Alert sound
        import sys
        if sys.platform == "win32":
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass

        font_family = config.load_font_family("DM Sans")
        f = QFont(font_family, 12, QFont.Weight.Bold)
        rem_title = reminder_data.get("title", "").strip()
        fm = QFontMetrics(f)
        text_w = fm.horizontalAdvance(rem_title)

        needed_w = int(18 + 58 + 14 + text_w + 14 + 84 + 18)
        target_w = max(410, min(560, needed_w))
        target_h = 94
        self.animate_to(target_w, target_h)
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.hide_animated()
        self.ensure_stays_on_top()
        self.update()

    def dismiss_reminder_alert(self):
        """Dismisses the active reminder alert from notch."""
        if self.active_reminder_alert:
            rid = self.active_reminder_alert.get("id")
            reminders = config.load_reminders()
            for r in reminders:
                if r.get("id") == rid:
                    r["notified"] = True
                    break
            config.save_reminders(reminders)
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.reminder_list.reload_reminders()
        self.active_reminder_alert = None
        self.reminder_dismiss_rect = QRect()
        self.reminder_snooze_rect = QRect()
        self.reminder_done_rect = QRect()
        self.hover_reminder_dismiss = False
        self.hover_reminder_snooze = False
        self.hover_reminder_done = False
        self.collapse_to_idle(force=True)

    def snooze_reminder_alert(self, minutes=5):
        """Snoozes the active reminder by 5 minutes and collapses notch to idle."""
        if self.active_reminder_alert:
            import datetime
            now = datetime.datetime.now()
            snooze_time = now + datetime.timedelta(minutes=minutes)
            rid = self.active_reminder_alert.get("id")
            reminders = config.load_reminders()
            for r in reminders:
                if r.get("id") == rid:
                    r["date"] = snooze_time.strftime("%Y-%m-%d")
                    r["date_display"] = "Today" if snooze_time.date() == now.date() else "Tomorrow"
                    r["hour"] = snooze_time.hour
                    r["minute"] = snooze_time.minute
                    r["notified"] = False
                    r["completed"] = False
                    break
            config.save_reminders(reminders)
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.reminder_list.reload_reminders()
        self.active_reminder_alert = None
        self.reminder_dismiss_rect = QRect()
        self.reminder_snooze_rect = QRect()
        self.reminder_done_rect = QRect()
        self.hover_reminder_dismiss = False
        self.hover_reminder_snooze = False
        self.hover_reminder_done = False
        self.collapse_to_idle(force=True)

    def complete_reminder_alert(self):
        """Marks the active reminder as Done, removes it from reminders storage, and collapses notch."""
        if self.active_reminder_alert:
            rid = self.active_reminder_alert.get("id")
            reminders = config.load_reminders()
            reminders = [r for r in reminders if r.get("id") != rid]
            config.save_reminders(reminders)
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                self.reminder_widget.reminder_list.reload_reminders()
        self.active_reminder_alert = None
        self.reminder_dismiss_rect = QRect()
        self.reminder_snooze_rect = QRect()
        self.reminder_done_rect = QRect()
        self.hover_reminder_dismiss = False
        self.hover_reminder_snooze = False
        self.hover_reminder_done = False
        self.collapse_to_idle(force=True)

    # -------------------------------------------------------------
    # Software Update Alert Controls
    # -------------------------------------------------------------
    def show_update_alert(self, release):
        """Expands the notch with the newer release and Update now / Remind later actions."""
        if release is None:
            return False
        if getattr(self, "active_reminder_alert", None) is not None:
            return False

        # The player is put behind the pill, not closed, and returns when it retires
        self._suspend_media_for_creation()
        self._exit_conflicting_modes("update_alert")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        if hasattr(self, "empty_reminders_restore_timer"):
            self.empty_reminders_restore_timer.stop()
        if hasattr(self, "empty_notes_restore_timer"):
            self.empty_notes_restore_timer.stop()
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        self.empty_reminders_showing = False
        self.cancel_idle_animations()

        self.active_update_alert = release
        self.update_alert_status = "available"
        self.update_alert_detail = f"You're on {APP_VERSION}"
        self._is_hovered = True

        font_family = config.load_font_family("DM Sans")
        f = QFont(font_family, 12, QFont.Weight.Bold)
        fm = QFontMetrics(f)
        text_w = fm.horizontalAdvance(f"Ticky {getattr(release, 'version', '')}")

        needed_w = int(18 + 58 + 14 + text_w + 14 + 92 + 18)
        target_w = max(410, min(560, needed_w))
        target_h = 94
        self.animate_to(target_w, target_h)
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.hide_animated()
        self.ensure_stays_on_top()
        self.update()
        return True

    def set_update_state(self, status, detail=""):
        """Mirrors download/installer progress onto the visible update alert."""
        if getattr(self, "active_update_alert", None) is None:
            return
        self.update_alert_status = status
        self.update_alert_detail = detail
        if status == "ready":
            # The installer is about to take over; drop the pill away again.
            self._retire_update_alert()
            return
        self.update()

    def dismiss_update_alert(self):
        """Hides the update alert. Suppression lasts only for this run."""
        self._retire_update_alert()

    def _retire_update_alert(self):
        """Clears the pill and hands the notch back to whatever stage it replaced."""
        self._clear_update_alert_state()
        self._resume_suspended_media()
        if not getattr(self, "media_in_notch", False) and not getattr(self, "timer_is_running", False):
            self.collapse_to_idle(force=True)

    def start_update_from_alert(self):
        """Hands the alert's release to the update service and shows progress."""
        if getattr(self, "active_update_alert", None) is None:
            return
        if self.update_alert_status not in ("available", "failed"):
            return
        self.update_alert_status = "downloading"
        self.update_alert_detail = "Downloading the new setup…"
        self.update()
        self.update_now_requested.emit()

    # -------------------------------------------------------------
    # Media Player in Notch Controls & Backend
    # -------------------------------------------------------------
    def get_media_manager(self):
        if not hasattr(self, "media_manager") or self.media_manager is None:
            if self.main_window and hasattr(self.main_window, "spotify_panel") and self.main_window.spotify_panel and hasattr(self.main_window.spotify_panel, "media_manager"):
                self.media_manager = self.main_window.spotify_panel.media_manager
            else:
                from utils.media_backend import MediaManager
                self.media_manager = MediaManager()
        return self.media_manager

    def spawn_notch_worker(self, worker):
        if not hasattr(self, "_active_media_workers"):
            self._active_media_workers = []
        self._active_media_workers.append(worker)
        worker.finished.connect(lambda: self._cleanup_notch_worker(worker))
        worker.start()

    def _cleanup_notch_worker(self, worker):
        if hasattr(self, "_active_media_workers") and worker in self._active_media_workers:
            self._active_media_workers.remove(worker)
            worker.deleteLater()

    # Media row geometry: standalone fills the notch, combined sits right of an active timer row
    MEDIA_EDGE_MARGIN = 20.0
    MEDIA_ART_SIZE = 56.0
    MEDIA_ART_GAP = 10.0
    MEDIA_STANDALONE_W = 300.0
    MEDIA_STANDALONE_H = 78.0
    MEDIA_TIMER_GAP = 16.0

    def expanded_row_height(self):
        """Height of the expanded row — the album art block needs the taller media stage."""
        if getattr(self, "media_in_notch", False):
            return int(self.MEDIA_STANDALONE_H)
        return self.hover_h

    def media_block_width(self):
        """Width of the [album art + info box] block reserved next to the timer row."""
        return self.MEDIA_STANDALONE_W - 2 * self.MEDIA_EDGE_MARGIN

    def media_timer_combined(self):
        """True when the media player and a timer share the expanded notch."""
        return getattr(self, "media_in_notch", False) and self.timer_in_notch

    def show_media_in_notch(self):
        """Expands notch into media player controls with album art, song title, and playback buttons."""
        self._exit_conflicting_modes("media")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        self.cancel_idle_animations()
        self.is_creating_task = False
        self.is_creating_note = False
        self.task_input_edit.hide()
        self.note_input_edit.hide()
        self.tasks_in_notch = False
        self.notes_in_notch = False
        self.add_expanded = False
        self.media_in_notch = True
        self._is_hovered = True

        if self.timer_in_notch:
            # Keep the paused timer open instead of letting it fold the notch away
            if hasattr(self, "timer_stopped_collapse_timer"):
                self.timer_stopped_collapse_timer.stop()
            self.update_notch_timer_geometry()
        else:
            self.animate_to(int(self.MEDIA_STANDALONE_W), int(self.MEDIA_STANDALONE_H))

        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            if hasattr(self.sub_pill.toolbar, "btn_music"):
                self.sub_pill.toolbar.btn_music.setActive(True)
            self.sub_pill.hide_animated()

        self.poll_notch_media()
        self.media_poll_timer.start()
        self.media_timeline_timer.start()
        self.update()

    def toggle_media_in_notch(self):
        if getattr(self, "media_in_notch", False):
            self.collapse_media_in_notch()
        else:
            self.show_media_in_notch()

    def update_media_geometry(self):
        """Resize the notch for the media row, alone or beside an active timer."""
        if self.timer_in_notch:
            self.update_notch_timer_geometry()
            return
        self.animate_to(int(self.MEDIA_STANDALONE_W), int(self.MEDIA_STANDALONE_H))
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill._refresh_active_highlights()
        self.ensure_stays_on_top()

    def drop_timer_row(self):
        """Stop the timer and leave the notch showing the media player alone."""
        self.timer_in_notch = False
        self.timer_is_running = False
        self.timer_task_title = None
        self.timer_ms = 0
        self.timer_time_peek_active = False
        self.is_active_focus = False
        if hasattr(self, "notch_stopwatch_timer"):
            self.notch_stopwatch_timer.stop()
        if hasattr(self, "timer_peek_scheduler"):
            self.timer_peek_scheduler.stop()
        if hasattr(self, "timer_peek_restore_timer"):
            self.timer_peek_restore_timer.stop()
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        if self.main_window and hasattr(self.main_window, "toolbar") and self.main_window.toolbar:
            if hasattr(self.main_window.toolbar, "stop_stopwatch"):
                self.main_window.toolbar.stop_stopwatch()
        self.update_media_geometry()
        self.update()

    def collapse_media_in_notch(self):
        if self.media_timer_combined():
            self._clear_media_in_notch()
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
                self.sub_pill.hide_animated()
            self.update_notch_timer_geometry()
            self.ensure_stays_on_top()
            self.update()
            return
        self._exit_conflicting_modes("idle")
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            if hasattr(self.sub_pill.toolbar, "btn_music"):
                self.sub_pill.toolbar.btn_music.setActive(False)
            self.sub_pill.hide_animated()
        self.collapse_to_idle(force=True)

    def poll_notch_media(self):
        if not getattr(self, "media_in_notch", False):
            return
        from utils.spotify import SpotifyWorker
        worker = SpotifyWorker("poll", self.get_media_manager(), self)
        worker.data_fetched.connect(self.on_notch_media_data)
        self.spawn_notch_worker(worker)

    def on_notch_media_data(self, data):
        if not getattr(self, "media_in_notch", False):
            return
        if not data:
            self.media_title = "No active playback"
            self.media_artist = "Play audio on Windows or Spotify"
            self.media_album = ""
            self.media_is_playing = False
            self.media_progress_ms = 0
            self.media_duration_ms = 0
            self.media_album_pixmap = None
            self.media_current_track_id = None
            self.update()
            return

        self.media_title = data.get("title", "No active playback") or "No active playback"
        self.media_artist = data.get("artist", "Windows Media") or "Windows Media"
        self.media_album = data.get("album", "")
        self.media_is_playing = data.get("is_playing", False)
        self.media_progress_ms = data.get("progress_ms", 0)
        self.media_duration_ms = data.get("duration_ms", 0)
        self.media_can_prev = data.get("can_prev", True)
        self.media_can_next = data.get("can_next", True)
        self.media_can_play = data.get("can_play", True) or data.get("can_pause", True)

        art_bytes = data.get("album_art_bytes")
        art_url = data.get("album_art_url")
        track_id = data.get("id")

        if art_bytes:
            if track_id != self.media_current_track_id or self.media_album_pixmap is None:
                self.media_current_track_id = track_id
                pm = QPixmap()
                if pm.loadFromData(art_bytes):
                    self.media_album_pixmap = pm
                else:
                    self.media_album_pixmap = None
        elif art_url:
            if art_url != self.media_current_track_id or self.media_album_pixmap is None:
                self.media_current_track_id = art_url
                if hasattr(self, "media_network_manager"):
                    self.media_network_manager.get(QNetworkRequest(QUrl(art_url)))
        else:
            self.media_current_track_id = None
            self.media_album_pixmap = None

        self.update()

    def _on_notch_media_image_downloaded(self, reply):
        if reply.error() == reply.NetworkError.NoError:
            data = reply.readAll()
            pm = QPixmap()
            if pm.loadFromData(data):
                self.media_album_pixmap = pm
                self.update()
        reply.deleteLater()

    def _on_notch_media_timeline_tick(self):
        if not getattr(self, "media_in_notch", False) or not self.media_is_playing:
            return
        self.media_progress_ms += 1000
        if self.media_duration_ms > 0 and self.media_progress_ms >= self.media_duration_ms:
            self.media_progress_ms = 0
            self.poll_notch_media()
        self.update()

    def _media_button_hover_flags(self, pos):
        """Refresh prev/play/next hover state; returns (any media button hovered, state changed)."""
        new_prev = hasattr(self, "media_prev_rect") and self.media_prev_rect.contains(pos)
        new_play = hasattr(self, "media_play_rect") and self.media_play_rect.contains(pos)
        new_next = hasattr(self, "media_next_rect") and self.media_next_rect.contains(pos)
        changed = (new_prev != self.hover_media_prev or
                   new_play != self.hover_media_play or
                   new_next != self.hover_media_next)
        self.hover_media_prev = new_prev
        self.hover_media_play = new_play
        self.hover_media_next = new_next
        return (new_prev or new_play or new_next), changed

    def notch_media_play_pause(self):
        from utils.spotify import SpotifyWorker
        self.media_is_playing = not self.media_is_playing
        self.update()
        worker = SpotifyWorker("toggle", self.get_media_manager(), self)
        worker.finished.connect(lambda: QTimer.singleShot(350, self.poll_notch_media))
        self.spawn_notch_worker(worker)

    def notch_media_prev(self):
        from utils.spotify import SpotifyWorker
        worker = SpotifyWorker("prev", self.get_media_manager(), self)
        worker.finished.connect(lambda: QTimer.singleShot(400, self.poll_notch_media))
        self.spawn_notch_worker(worker)

    def notch_media_next(self):
        from utils.spotify import SpotifyWorker
        worker = SpotifyWorker("next", self.get_media_manager(), self)
        worker.finished.connect(lambda: QTimer.singleShot(400, self.poll_notch_media))
        self.spawn_notch_worker(worker)

    def draw_media_in_notch(self, painter, w, h, opacity, accent_color, left_x=None):
        """Draws square album art on left, and styled container box on right with title, author, timeline, media controls."""
        if opacity <= 0.001:
            return

        font_family = config.load_font_family("DM Sans")

        # 1. Square Album Cover (static / non-moving, 56x56 with 8px rounded corners)
        art_size = self.MEDIA_ART_SIZE
        art_x = self.MEDIA_EDGE_MARGIN if left_x is None else float(left_x)
        art_y = max(8.0, (h - art_size) / 2.0)
        art_rect = QRectF(art_x, art_y, art_size, art_size)

        if self.media_album_pixmap and not self.media_album_pixmap.isNull():
            painter.save()
            art_path = QPainterPath()
            art_path.addRoundedRect(art_rect, 8.0, 8.0)
            painter.setClipPath(art_path)

            scaled_pm = self.media_album_pixmap.scaled(
                int(art_size), int(art_size),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            src_x = max(0, (scaled_pm.width() - int(art_size)) // 2)
            src_y = max(0, (scaled_pm.height() - int(art_size)) // 2)
            painter.drawPixmap(int(art_x), int(art_y), scaled_pm, src_x, src_y, int(art_size), int(art_size))
            painter.restore()

            # Specular rim around artwork
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, int(35 * opacity)), 1.0))
            painter.drawRoundedRect(art_rect, 8.0, 8.0)
        else:
            # Sleek placeholder card
            painter.setBrush(QBrush(QColor(theme.SEC_CARD_COLOR)))
            b_pen = QColor(theme.BORDER_COLOR)
            if not b_pen.isValid():
                b_pen = QColor(255, 255, 255, int(24 * opacity))
            painter.setPen(QPen(b_pen, 1.0))
            painter.drawRoundedRect(art_rect, 8.0, 8.0)

            font_icon = QFont()
            font_icon.setFamilies([font_family, "Segoe UI Emoji", "sans-serif"])
            font_icon.setPointSize(18)
            painter.setFont(font_icon)
            painter.setPen(QColor(accent_color))
            painter.drawText(art_rect, Qt.AlignmentFlag.AlignCenter, "🎵")

        # 2. Styled Container Box for Right Stack (matches album cover height exactly)
        box_x = art_x + art_size + self.MEDIA_ART_GAP
        box_y = art_y
        box_h = art_size  # Same height as album cover!
        box_w = max(130.0, w - box_x - self.MEDIA_EDGE_MARGIN)  # Symmetrical right gap matching left gap
        box_rect = QRectF(box_x, box_y, box_w, box_h)
        self.media_block_rect = QRect(int(art_x), int(art_y), int(box_x + box_w - art_x), int(art_size))

        # Draw subtle styled card background for the box
        box_bg = QColor(theme.SEC_CARD_COLOR)
        box_bg.setAlpha(int(140 * opacity))
        painter.setBrush(QBrush(box_bg))

        box_border = QColor(theme.BORDER_COLOR)
        if not box_border.isValid():
            box_border = QColor(255, 255, 255, int(30 * opacity))
        else:
            box_border.setAlpha(int(min(255, int(box_border.alpha() * opacity))))
        painter.setPen(QPen(box_border, 1.0))
        painter.drawRoundedRect(box_rect, 8.0, 8.0)

        # Inner dimensions
        pad_x = 10.0
        inner_x = box_x + pad_x
        inner_w = box_w - (2.0 * pad_x)
        inner_cx = box_x + (box_w / 2.0)

        # Title: 10 chars is enough and rest ...
        raw_title = (self.media_title or "Not Playing").strip()
        if len(raw_title) > 10:
            display_title = raw_title[:10] + "..."
        else:
            display_title = raw_title

        font_title = QFont()
        font_title.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
        font_title.setPointSize(9.5)
        font_title.setWeight(QFont.Weight.Bold)
        painter.setFont(font_title)
        title_col = QColor(theme.TEXT_PRIMARY)
        title_col.setAlphaF(opacity)
        painter.setPen(title_col)
        painter.drawText(QPointF(inner_x, box_y + 15.0), display_title)

        # Author / Artist (readable crisp subtitle)
        raw_artist = (self.media_artist or "Unknown").strip()
        font_artist = QFont()
        font_artist.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
        font_artist.setPointSize(8.8)
        font_artist.setWeight(QFont.Weight.Medium)
        painter.setFont(font_artist)
        fm_artist = QFontMetrics(font_artist)
        display_artist = fm_artist.elidedText(raw_artist, Qt.TextElideMode.ElideRight, int(inner_w))
        artist_col = QColor(theme.TEXT_SECONDARY)
        artist_col.setAlphaF(opacity)
        painter.setPen(artist_col)
        painter.drawText(QPointF(inner_x, box_y + 26.5), display_artist)

        # Media Controls centered horizontally, larger icons, no background, brighter white on hover
        controls_cy = box_y + 41.0

        play_size = 23.0
        prev_size = 21.0
        next_size = 21.0

        prev_cx = inner_cx - 36.0
        next_cx = inner_cx + 36.0

        play_rect = QRectF(inner_cx - (play_size / 2.0), controls_cy - (play_size / 2.0), play_size, play_size)
        prev_rect = QRectF(prev_cx - (prev_size / 2.0), controls_cy - (prev_size / 2.0), prev_size, prev_size)
        next_rect = QRectF(next_cx - (next_size / 2.0), controls_cy - (next_size / 2.0), next_size, next_size)

        self.media_prev_rect = QRect(int(prev_cx - 16), int(controls_cy - 14), 32, 28)
        self.media_play_rect = QRect(int(inner_cx - 16), int(controls_cy - 14), 32, 28)
        self.media_next_rect = QRect(int(next_cx - 16), int(controls_cy - 14), 32, 28)
        self.media_close_rect = QRect()

        # Brighter white on hover, no background
        prev_col = QColor(255, 255, 255, int(255 * opacity)) if self.hover_media_prev else QColor(200, 205, 215, int(210 * opacity))
        play_col = QColor(255, 255, 255, int(255 * opacity)) if self.hover_media_play else QColor(220, 225, 235, int(225 * opacity))
        next_col = QColor(255, 255, 255, int(255 * opacity)) if self.hover_media_next else QColor(200, 205, 215, int(210 * opacity))

        # Render Previous
        colored_prev = MEDIA_PREV_SVG.replace("COLOR_PLACEHOLDER", prev_col.name())
        renderer_prev = QSvgRenderer(QByteArray(colored_prev.encode("utf-8")))
        renderer_prev.render(painter, prev_rect)

        # Render Play / Pause
        icon_svg = MEDIA_PAUSE_SVG if self.media_is_playing else MEDIA_PLAY_SVG
        colored_play = icon_svg.replace("COLOR_PLACEHOLDER", play_col.name())
        renderer_play = QSvgRenderer(QByteArray(colored_play.encode("utf-8")))
        renderer_play.render(painter, play_rect)

        # Render Next
        colored_next = MEDIA_NEXT_SVG.replace("COLOR_PLACEHOLDER", next_col.name())
        renderer_next = QSvgRenderer(QByteArray(colored_next.encode("utf-8")))
        renderer_next.render(painter, next_rect)

    def set_ai_thinking_state(self, thinking: bool):
        """Dynamic eye animation when AI is thinking."""
        self.ai_is_thinking = thinking
        if not hasattr(self, "_ai_thinking_timer"):
            self._ai_thinking_timer = QTimer(self)
            self._ai_thinking_timer.setInterval(950)
            self._ai_thinking_timer.timeout.connect(self._ai_thinking_wander_step)

        if thinking:
            self._ai_thinking_wander_dir = -1.0
            self.override_pupil = True
            self.override_pupil_y = -2.6  # Look up thoughtfully
            self.override_pupil_x = -2.0  # Slightly left
            self.target_left_eye_scale_y = 1.15
            self.target_right_eye_scale_y = 0.95
            self.target_half_closed = 0.15
            self._ai_thinking_timer.start()
        else:
            self._ai_thinking_timer.stop()
            self.target_left_eye_scale_x = 1.0
            self.target_left_eye_scale_y = 1.0
            self.target_right_eye_scale_x = 1.0
            self.target_right_eye_scale_y = 1.0
            self.target_half_closed = 0.0
            self.target_flat_eyes = 0.0
            self.override_pupil = False
            self.override_pupil_x = 0.0
            self.override_pupil_y = 0.0
        self.update()

    def _ai_thinking_wander_step(self):
        """Wanders pupils thoughtfully while AI thinking."""
        if not getattr(self, "ai_is_thinking", False):
            return
        self._ai_thinking_wander_dir = -getattr(self, "_ai_thinking_wander_dir", 1.0)
        self.override_pupil = True
        self.override_pupil_x = self._ai_thinking_wander_dir * 2.2
        self.override_pupil_y = -2.4 + random.uniform(-0.3, 0.3)
        if self._ai_thinking_wander_dir > 0:
            self.target_left_eye_scale_y = 0.95
            self.target_right_eye_scale_y = 1.15
        else:
            self.target_left_eye_scale_y = 1.15
            self.target_right_eye_scale_y = 0.95
        self.update()

    def trigger_ai_response_expression(self, success: bool = True):
        """Happy satisfied expression (^ ^) when AI gives response, or puzzled if error."""
        if hasattr(self, "_ai_thinking_timer"):
            self._ai_thinking_timer.stop()
        if not hasattr(self, "_ai_response_reset_timer"):
            self._ai_response_reset_timer = QTimer(self)
            self._ai_response_reset_timer.setSingleShot(True)
            self._ai_response_reset_timer.timeout.connect(self._reset_ai_response_expression)

        if success:
            # Cute happy smiling eyes (^ ^)
            self.target_half_closed = 0.72
            self.target_left_eye_scale_x = 1.2
            self.target_right_eye_scale_x = 1.2
            self.target_left_eye_scale_y = 0.78
            self.target_right_eye_scale_y = 0.78
            self.override_pupil = True
            self.override_pupil_x = 0.0
            self.override_pupil_y = 0.4
        else:
            # Puzzled / flat eyes
            self.target_flat_eyes = 0.8
            self.override_pupil = True
            self.override_pupil_x = 0.0
            self.override_pupil_y = 1.5

        self.update()
        self._ai_response_reset_timer.start(2200)

    def _reset_ai_response_expression(self):
        """Restore normal eyes after AI response expression."""
        if getattr(self, "ai_is_thinking", False):
            return
        self.target_half_closed = 0.0
        self.target_flat_eyes = 0.0
        self.target_left_eye_scale_x = 1.0
        self.target_right_eye_scale_x = 1.0
        self.target_left_eye_scale_y = 1.0
        self.target_right_eye_scale_y = 1.0
        self.override_pupil = False
        self.override_pupil_x = 0.0
        self.override_pupil_y = 0.0
        self.update()

    def set_ai_listening_state(self, listening: bool):
        self.ai_is_listening = listening
        self.update()

    def update_ai_chat_geometry(self):
        if hasattr(self, "ai_chat_widget") and self.ai_chat_widget:
            margin_x = 16
            top_y = 36
            w = max(100, self.width() - (margin_x * 2))
            h = max(50, self.height() - top_y - 10)
            self.ai_chat_widget.setGeometry(margin_x, top_y, w, h)

    # ------------------------------------------------------------------
    # System-wide smart voice dictation
    # ------------------------------------------------------------------
    def toggle_dictation(self):
        """Global-hotkey entry: start a new session or cancel the active one."""
        if self.dictation_in_notch or (hasattr(self, "dictation_service") and self.dictation_service.is_active):
            self.cancel_dictation()
        else:
            self.start_dictation()

    def start_dictation(self):
        """Capture the focused text field target, start STT, expand listening HUD."""
        if hasattr(self, "dictation_service") and self.dictation_service.is_active:
            return
        # Capture foreground HWND + launch recognizer BEFORE showing/expanding UI
        # so we don't accidentally bind to Ticky itself.
        self.dictation_service.start()
        if not self.isVisible():
            self.show()
        self.show_dictation_in_notch()

    def cancel_dictation(self):
        """Immediate manual abort via × or second hotkey press."""
        if hasattr(self, "dictation_service") and self.dictation_service.is_active:
            self.dictation_service.cancel()
        self.collapse_dictation()

    def show_dictation_in_notch(self):
        """Expand the notch into the live listening / waveform interface."""
        self._exit_conflicting_modes("dictation")
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
            self.sub_pill.hide_animated()

        self.cancel_idle_animations()
        self.is_creating_task = False
        self.is_creating_note = False
        if hasattr(self, "task_input_edit"):
            self.task_input_edit.hide()
        if hasattr(self, "note_input_edit"):
            self.note_input_edit.hide()
        self.tasks_in_notch = False
        self.notes_in_notch = False
        self.add_expanded = False
        self.dictation_in_notch = True
        self.dictation_partial = ""
        self.hover_dictation_cancel = False
        self._is_hovered = True
        self.ai_is_listening = True

        # Spacious Dynamic Island listening HUD with increased width (220px x 36px)
        w = 220.0
        h = 36.0
        BAR_N = 7
        gap = 3.6
        bar_w = 4.2
        strip_w = BAR_N * bar_w + (BAR_N - 1) * gap
        bars_right = (w / 2.0) + (strip_w / 2.0)
        element_gap = 14.0
        cancel_size = 22.0
        cancel_x = bars_right + element_gap
        cancel_y = (h - cancel_size) / 2.0
        self.dictation_cancel_rect = QRect(int(cancel_x - 5), int(cancel_y - 5), int(cancel_size + 10), int(cancel_size + 10))

        self.animate_to(220, 36, duration=220)
        self.update()
        if hasattr(self, "dictation_abort_timer"):
            self.dictation_abort_timer.start(3500)
        # Give focus back to the app the user was typing into
        QTimer.singleShot(40, self._restore_dictation_focus)

    def collapse_dictation(self):
        """Return the notch to its ground state after dictation ends."""
        if hasattr(self, "dictation_abort_timer"):
            self.dictation_abort_timer.stop()
        was_dictating = getattr(self, "dictation_in_notch", False)
        self.dictation_in_notch = False
        self.dictation_levels = []
        self.dictation_partial = ""
        self.hover_dictation_cancel = False
        self.dictation_cancel_rect = QRect()
        self.ai_is_listening = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if was_dictating or self.height() > self.idle_h + 4:
            # Don't force-kill a running timer; just leave dictation UI
            if self.timer_is_running:
                self._is_hovered = False
                self.animate_to(self.calc_notch_timer_width() if hasattr(self, "calc_notch_timer_width") else self.hover_w, self.hover_h)
                self.update()
            else:
                self.collapse_to_idle(force=True)
                # If the user is on Classic UI, hide the temporary Notch HUD again.
                ui_style = config.load_ui_style("classic")
                if ui_style != "notch":
                    QTimer.singleShot(320, self.hide)

    def _on_dictation_timeout_abort(self):
        """Automatically abort dictation and collapse notch if no voice input for a few seconds."""
        if getattr(self, "dictation_in_notch", False):
            self.cancel_dictation()

    def _restore_dictation_focus(self):
        hwnd = getattr(self.dictation_service, "_target_hwnd", None)
        if hwnd:
            text_inject.focus_hwnd(hwnd)

    def _on_dictation_state_changed(self, state: str):
        if state in (DictationState.LISTENING.value, DictationState.TRANSCRIBING.value, DictationState.STARTING.value):
            self.ai_is_listening = True
        self.update()

    def _on_dictation_levels(self, levels):
        if not getattr(self, "dictation_in_notch", False):
            return
        self.dictation_levels = levels or []
        # Reset the silence abort countdown if active voice input is sensed
        if levels and max(levels) > 0.08 and hasattr(self, "dictation_abort_timer"):
            self.dictation_abort_timer.start(3500)
        self.update()

    def _on_dictation_partial(self, text: str):
        self.dictation_partial = text or ""
        self.update()

    def _on_dictation_error(self, message: str):
        # Surface briefly via partial label area; session_ended will collapse
        self.dictation_partial = message or "Dictation unavailable"
        self.update()

    def _on_dictation_session_ended(self, reason: str):
        # Preserve committed text always; collapse HUD only if still in dictation mode
        if getattr(self, "dictation_in_notch", False):
            QTimer.singleShot(40, self.collapse_dictation)

    def _paint_dictation_hud(self, painter, w: float, h: float, accent_color: QColor):
        """Draw live bidirectional waveform + mic icon + cancel button inside the listening notch."""
        center_x = w / 2.0
        center_y = h / 2.0

        # Larger visualizer bars centered in the listening notch
        BAR_N = 7
        gap = 3.6
        bar_w = 4.2
        strip_w = BAR_N * bar_w + (BAR_N - 1) * gap
        bars_left = center_x - strip_w / 2.0
        bars_right = center_x + strip_w / 2.0
        max_half = min(12.5, (h - 8.0) / 2.0)

        # Bring mic and close button closer to the visualizer
        element_gap = 14.0

        # Microphone icon on the left
        mic_size = 17.0
        mic_x = bars_left - element_gap - mic_size
        mic_y = (h - mic_size) / 2.0

        # Subtle glow ring around mic icon
        mic_glow = QColor(accent_color)
        mic_glow.setAlpha(35)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(mic_glow))
        painter.drawEllipse(QRectF(mic_x - 3.0, mic_y - 3.0, mic_size + 6.0, mic_size + 6.0))

        mic_col = QColor(accent_color)
        svg_mic = DICTATION_MIC_SVG.replace("COLOR_PLACEHOLDER", mic_col.name())
        renderer_mic = QSvgRenderer(QByteArray(svg_mic.encode("utf-8")))
        renderer_mic.render(painter, QRectF(mic_x, mic_y, mic_size, mic_size))

        # Audio visualizer bars (larger, thicker, and dynamic)
        levels = list(getattr(self, "dictation_levels", []) or [])
        if levels:
            step = max(1, len(levels) // BAR_N)
            samples = [levels[min(len(levels) - 1, i * step)] for i in range(BAR_N)]
        else:
            samples = [0.08] * BAR_N

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 255)))
        for i, amp in enumerate(samples):
            amp = max(0.08, min(1.0, float(amp)))
            bar_h = max(4.5, amp * max_half * 2.0)
            x = bars_left + i * (bar_w + gap)
            painter.drawRoundedRect(
                QRectF(x, center_y - bar_h / 2.0, bar_w, bar_h),
                bar_w / 2.0,
                bar_w / 2.0
            )

        # Cancel / close button on the right of the visualizer
        cancel_size = 22.0
        cancel_x = bars_right + element_gap
        cancel_y = (h - cancel_size) / 2.0
        # Generous hitbox for effortless clickability
        self.dictation_cancel_rect = QRect(int(cancel_x - 5), int(cancel_y - 5), int(cancel_size + 10), int(cancel_size + 10))

        hover = getattr(self, "hover_dictation_cancel", False)
        btn_rect = QRectF(cancel_x, cancel_y, cancel_size, cancel_size)

        btn_bg = QColor(255, 255, 255, 60 if hover else 28)
        btn_border = QColor(255, 255, 255, 95 if hover else 48)
        painter.setPen(QPen(btn_border, 1.0))
        painter.setBrush(QBrush(btn_bg))
        painter.drawEllipse(btn_rect)

        # Crisp cross icon centered inside button
        cross_pen = QColor(255, 255, 255, 255 if hover else 205)
        painter.setPen(QPen(cross_pen, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        cx = cancel_x + cancel_size / 2.0
        cy = cancel_y + cancel_size / 2.0
        arm = 3.6
        painter.drawLine(QPointF(cx - arm, cy - arm), QPointF(cx + arm, cy + arm))
        painter.drawLine(QPointF(cx + arm, cy - arm), QPointF(cx - arm, cy + arm))

    # ------------------------------------------------------------------
    # System-Wide App & Software Search (Alt + W)
    # ------------------------------------------------------------------
    def toggle_app_search(self):
        """Toggle system-wide app search HUD in notch."""
        if getattr(self, "app_search_in_notch", False):
            self.collapse_app_search()
        else:
            self.open_app_search()

    def open_app_search(self):
        """
        Expand notch horizontally first, spawn search input, and focus.
        As user enters text, notch expands vertically showing top 4 results + scroll.
        """
        self._exit_conflicting_modes("app_search")
        self.app_search_in_notch = True
        self._is_hovered = False

        if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
            self.sub_pill.hide_animated()

        self.show()
        self.raise_()
        self.activateWindow()
        self.ensure_stays_on_top()

        # Step 1: Expand horizontally first (single row capsule)
        target_w = 480
        target_h = 48
        self.animate_to(target_w, target_h, duration=220, easing=QEasingCurve.Type.OutCubic)

        if hasattr(self, "app_search_widget") and self.app_search_widget:
            self.app_search_widget.reset_state()
            self.app_search_widget.show()
            self.update_app_search_geometry()
            QTimer.singleShot(60, self.app_search_widget.focus_input)

        if sys.platform == "win32" and user32:
            try:
                user32.SetForegroundWindow(int(self.winId()))
            except Exception:
                pass

    def collapse_app_search(self):
        """Collapse app search HUD back to idle ground state."""
        if not getattr(self, "app_search_in_notch", False):
            return
        self.app_search_in_notch = False
        if hasattr(self, "app_search_widget") and self.app_search_widget:
            self.app_search_widget.hide()
            self.app_search_widget.reset_state()

        self.collapse_to_idle(force=True)

        ui_style = config.load_ui_style("classic")
        if ui_style != "notch":
            QTimer.singleShot(280, self.hide)

    def _on_app_search_geometry_requested(self, target_h: int):
        """Simultaneously adjust vertical expansion when characters are entered/cleared."""
        if not getattr(self, "app_search_in_notch", False):
            return
        self.animate_to(480, target_h, duration=200, easing=QEasingCurve.Type.OutCubic)
        self.update_app_search_geometry()

    def _on_app_search_launched(self, app_item):
        """App launched by user click or Enter key -> collapse notch."""
        self.collapse_app_search()

    def update_app_search_geometry(self):
        """Keep child search widget bounds aligned within notch."""
        if hasattr(self, "app_search_widget") and self.app_search_widget:
            margin_x = 12
            top_y = 2
            w = max(100, int(self.width() - (margin_x * 2)))
            h = max(30, int(self.height() - top_y - 4))
            self.app_search_widget.setGeometry(margin_x, top_y, w, h)

    def get_notes_list(self):
        if self.main_window and hasattr(self.main_window, "notes"):
            return list(self.main_window.notes)
        return config.load_notes()

    def next_notes_page(self):
        all_notes = self.get_notes_list()
        num_pages = max(1, (len(all_notes) + 2) // 3)
        if self.notch_notes_page < num_pages - 1:
            self.notch_notes_page += 1
            self.update()

    def prev_notes_page(self):
        if self.notch_notes_page > 0:
            self.notch_notes_page -= 1
            self.update()

    def _clear_copied_note_feedback(self):
        self.copied_note_idx = None
        self.update()

    def collapse_to_idle(self, force=False):
        """Collapse notch all the way back to idle pill (ground stage)."""
        if getattr(self, "active_reminder_alert", None) is not None:
            return
        if getattr(self, "active_update_alert", None) is not None:
            return
        if not force and getattr(self, "ai_chat_in_notch", False):
            return
        if not force and getattr(self, "is_creating_reminder", False):
            return
        if not force and getattr(self, "media_in_notch", False):
            return
        if not force and getattr(self, "dictation_in_notch", False):
            return
        if self.timer_is_running:
            return
        self._exit_conflicting_modes("idle")
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        self.timer_in_notch = False
        self.timer_is_running = False
        self.timer_task_title = None
        self.timer_ms = 0
        self.is_active_focus = False
        self.timer_time_peek_active = False
        if hasattr(self, "notch_stopwatch_timer"):
            self.notch_stopwatch_timer.stop()
        if hasattr(self, "timer_peek_scheduler"):
            self.timer_peek_scheduler.stop()
        if hasattr(self, "timer_peek_restore_timer"):
            self.timer_peek_restore_timer.stop()
        if self.main_window and hasattr(self.main_window, "toolbar") and self.main_window.toolbar:
            if hasattr(self.main_window.toolbar, "stop_stopwatch"):
                self.main_window.toolbar.stop_stopwatch()
        self.unhover_collapse_timer.stop()
        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            if self.width() <= self.idle_w + 5 and self.height() <= self.idle_h + 5:
                if self.sub_pill.isVisible():
                    self.sub_pill.hide_animated()
        self.cancel_idle_animations()
        self._is_hovered = False
        self.add_expanded = False
        self._add_expand_progress = 0.0
        self.is_creating_task = False
        self.is_creating_note = False
        self.editing_note_index = None
        if hasattr(self, "empty_notes_restore_timer"):
            self.empty_notes_restore_timer.stop()
        self.empty_notes_showing = False
        self.notes_in_notch = False
        self.notch_notes_page = 0
        self.copied_note_idx = None
        self.hovered_note_card_idx = None
        self.hovered_note_copy_idx = None
        self.hover_note_tick = False
        self.hover_note_cross = False
        self.hover_note_delete = False
        self.note_delete_rect = QRect()
        # Reset tasks-in-notch state
        self.tasks_in_notch = False
        self.notch_task_scroll = 0.0
        self.notch_task_rects = []
        self.notch_task_cb_rects = []
        self.notch_task_play_rects = []
        self.hovered_task_idx = None
        self.hovered_task_cb_idx = None
        self.hovered_task_play_idx = None
        self.completing_task_text = None
        self.complete_row_anim.stop()
        self._complete_row_progress = 0.0
        # Reset mini AI chat in notch
        self.ai_chat_in_notch = False
        self.ai_is_thinking = False
        self.ai_is_listening = False
        self.hover_ai_close = False
        self.notch_ai_close_rect = QRect()
        if hasattr(self, "ai_chat_widget") and self.ai_chat_widget:
            if hasattr(self.ai_chat_widget, "is_recording") and self.ai_chat_widget.is_recording:
                self.ai_chat_widget.stop_voice_recording()
            self.ai_chat_widget.hide()
        # Reset media player in notch. A player only suspended for a creation flow
        # keeps its pending reopen — collapsing must not swallow it.
        if not getattr(self, "media_suspended", False):
            self._clear_media_in_notch()
        # Reset reminders in notch
        self.reminders_in_notch = False
        self.is_creating_reminder = False
        self.empty_reminders_showing = False
        self._reminders_list_suspended = False
        if hasattr(self, "empty_reminders_restore_timer"):
            self.empty_reminders_restore_timer.stop()
        if hasattr(self, "reminder_title_edit"):
            self.reminder_title_edit.hide()
            self.reminder_title_edit.clear()
        if hasattr(self, "reminder_widget") and self.reminder_widget:
            self.reminder_widget.hide()
        if hasattr(self, "sub_pill") and self.sub_pill and hasattr(self.sub_pill, "btn_reminders"):
            self.sub_pill.btn_reminders.setActive(False)
        self.active_reminder_alert = None
        self.reminder_dismiss_rect = QRect()
        self.reminder_snooze_rect = QRect()
        self.reminder_done_rect = QRect()
        self.hover_reminder_dismiss = False
        self.hover_reminder_snooze = False
        self.hover_reminder_done = False
        self._clear_update_alert_state()
        # Reset voice dictation HUD
        self.dictation_in_notch = False
        self.dictation_levels = []
        self.dictation_partial = ""
        self.hover_dictation_cancel = False
        self.dictation_cancel_rect = QRect()
        self.task_input_edit.hide()
        self.task_input_edit.clear()
        self.note_input_edit.hide()
        self.note_input_edit.clear()
        self.hover_add_btn = False
        self.hover_card = False
        self.hover_cb = False
        self.hover_play = False
        self.hover_sub_task = False
        self.hover_sub_note = False
        self.hover_sub_reminder = False
        self.sub_reminder_rect = QRect()
        self.timer_hover_play = False
        self.timer_hover_restart = False
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.animate_to(self.idle_w, self.idle_h)

    def _on_unhover_timeout(self):
        """Called when 5 seconds pass after mouse leaves while in add_expanded state."""
        if getattr(self, "active_reminder_alert", None) is not None:
            return
        if getattr(self, "active_update_alert", None) is not None:
            return
        if self.is_creating_task or getattr(self, "ai_chat_in_notch", False) or getattr(self, "dictation_in_notch", False):
            return
        current_pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(current_pos):
            self.collapse_to_idle()

    # -------------------------------------------------------------
    # Idle Ground Animations (Time peek, Expressions, Task peek)
    # -------------------------------------------------------------
    def trigger_random_idle_behavior(self):
        """Randomly triggers time peek, rich eye expressions, or task peek during idle."""
        if (self._is_hovered or self.is_typing or self.is_creating_task or 
            self.add_expanded or self.time_peek_active or self.task_peek_active or 
            self.expression_active or self.height() > 44 or getattr(self, "active_reminder_alert", None) is not None or getattr(self, "active_update_alert", None) is not None):
            self.idle_cycle_timer.setInterval(random.randint(4000, 6000))
            return

        now = time.time()
        mouse_idle_duration = now - self.last_mouse_move_time

        tasks = []
        if self.main_window and hasattr(self.main_window, "tasks"):
            tasks = list(self.main_window.tasks)
        else:
            tasks = config.load_tasks()

        # If mouse is actively moving (< 1.8s idle), eye expressions do NOT interrupt mouse movement!
        # However, time displaying and task displaying CAN overtake mouse movement animation!
        if mouse_idle_duration < 1.8:
            overtake_choices = ["time_peek"]
            if tasks:
                overtake_choices.append("task_peek")
            mode = random.choice(overtake_choices)
            if mode == "time_peek":
                self.start_time_peek()
            elif mode == "task_peek":
                self.start_task_peek(random.choice(tasks))
            self.idle_cycle_timer.setInterval(random.randint(6000, 9000))
            return

        # When mouse has settled (after mouse movement animation), eye expressions are prioritized!
        # Pool gives majority weight (~65%) to eye expressions (semi-closed eyes, looking here and there, etc.)
        behavior_pool = ["expression", "expression", "expression"]
        behavior_pool.append("time_peek")
        if tasks:
            behavior_pool.append("task_peek")

        last_mode = getattr(self, "last_idle_mode", None)
        valid_pool = [c for c in behavior_pool if c != last_mode] if len(behavior_pool) > 1 and last_mode in behavior_pool else behavior_pool
        mode = random.choice(valid_pool)
        self.last_idle_mode = mode

        if mode == "time_peek":
            self.start_time_peek()
        elif mode == "task_peek" and tasks:
            self.start_task_peek(random.choice(tasks))
        else:
            self.trigger_random_expression()

        self.idle_cycle_timer.setInterval(random.randint(4500, 7000))

    def start_time_peek(self):
        """Eyes scroll down, time & date roll in, notch slightly enlarges (200x38), stays for ~3.8s, then rolls back."""
        if self._is_hovered or self.is_typing or self.time_peek_active or self.task_peek_active:
            return
        if self.expression_active:
            self.expression_restore_timer.stop()
            self.reset_expression()
        self.time_peek_active = True
        self.target_eyes_scroll_y = 32.0  # Eyes scroll down and exit bottom
        self.animate_to(200, 38, duration=280, easing=QEasingCurve.Type.OutQuad)
        self.time_peek_restore_timer.start(3800)

    def end_time_peek(self):
        """Time rolls out, eyes scroll back into default position, and notch smoothly returns to 160x32."""
        if not self.time_peek_active:
            return
        self.time_peek_active = False
        self.target_eyes_scroll_y = 0.0
        if not self._is_hovered and not self.is_creating_task:
            self.animate_to(self.idle_w, self.idle_h, duration=260, easing=QEasingCurve.Type.OutQuad)

    def trigger_random_expression(self):
        """
        Triggers organic eye expressions:
        - Semi-closed eyes (sleepy / relaxed glance or straight)
        - Looking here and there (wandering glances in multiple directions)
        - Curious asymmetric eyes (one big, one small eye)
        - Flat line eyes '- -'
        """
        if self._is_hovered or self.is_typing or self.time_peek_active or self.task_peek_active:
            return

        self.expression_active = True

        def get_random_gaze():
            angle = random.uniform(0, 2 * math.pi)
            dist = random.uniform(2.2, 3.4)
            return math.cos(angle) * dist, math.sin(angle) * dist

        expr_type = random.choice([
            "semi_closed_straight",
            "semi_closed_glance",
            "looking_here_and_there",
            "looking_here_and_there",
            "semi_closed_wander",
            "asym_left_any_dir",
            "asym_right_any_dir",
            "flat_eyes",
            "glance_any_dir"
        ])

        if expr_type == "semi_closed_straight":
            self.target_half_closed = 0.85
            self.override_pupil = True
            self.override_pupil_x = 0.0
            self.override_pupil_y = 0.0
        elif expr_type == "semi_closed_glance":
            self.target_half_closed = 0.85
            self.override_pupil = True
            self.override_pupil_x, self.override_pupil_y = get_random_gaze()
        elif expr_type == "looking_here_and_there":
            # Glances one direction, then after 1.1s smoothly looks the other direction
            first_dir = random.choice([-1.0, 1.0])
            self.override_pupil = True
            self.override_pupil_x = first_dir * 3.2
            self.override_pupil_y = random.uniform(-0.5, 0.5)

            def switch_gaze():
                if self.expression_active and not (self._is_hovered or self.is_typing):
                    self.override_pupil_x = -first_dir * 3.2
                    self.override_pupil_y = random.uniform(-0.5, 0.5)

            QTimer.singleShot(1100, switch_gaze)
        elif expr_type == "semi_closed_wander":
            # Semi-closed eyes that wander from one side to the other
            self.target_half_closed = 0.85
            first_dir = random.choice([-1.0, 1.0])
            self.override_pupil = True
            self.override_pupil_x = first_dir * 2.8
            self.override_pupil_y = 0.4

            def switch_semi_gaze():
                if self.expression_active and not (self._is_hovered or self.is_typing):
                    self.override_pupil_x = -first_dir * 2.8
                    self.override_pupil_y = 0.4

            QTimer.singleShot(1100, switch_semi_gaze)
        elif expr_type == "asym_left_any_dir":
            self.target_left_eye_scale_x = 1.25
            self.target_left_eye_scale_y = 1.25
            self.target_right_eye_scale_x = 0.65
            self.target_right_eye_scale_y = 0.65
            self.override_pupil = True
            self.override_pupil_x, self.override_pupil_y = get_random_gaze()
        elif expr_type == "asym_right_any_dir":
            self.target_left_eye_scale_x = 0.65
            self.target_left_eye_scale_y = 0.65
            self.target_right_eye_scale_x = 1.25
            self.target_right_eye_scale_y = 1.25
            self.override_pupil = True
            self.override_pupil_x, self.override_pupil_y = get_random_gaze()
        elif expr_type == "flat_eyes":
            self.target_flat_eyes = 1.0
        elif expr_type == "glance_any_dir":
            self.override_pupil = True
            self.override_pupil_x, self.override_pupil_y = get_random_gaze()

        self.expression_restore_timer.start(2400)

    def reset_expression(self):
        """Smoothly restores eyes back to default symmetrical shape and mouse tracking."""
        self.expression_active = False
        self.target_left_eye_scale_x = 1.0
        self.target_left_eye_scale_y = 1.0
        self.target_right_eye_scale_x = 1.0
        self.target_right_eye_scale_y = 1.0
        self.target_flat_eyes = 0.0
        self.target_half_closed = 0.0
        self.override_pupil = False
        self.override_pupil_x = 0.0
        self.override_pupil_y = 0.0

    def start_task_peek(self, task_title):
        """Expands notch into a spacious pill (width up to 430px, height 42px), shows random task with original task style, and shifts eyes opposite with half-closed or curious expression."""
        if self._is_hovered or self.is_typing or self.task_peek_active or self.time_peek_active:
            return
        if self.expression_active:
            self.expression_restore_timer.stop()
            self.reset_expression()

        self.task_peek_active = True
        self.task_collapsing = False
        self.task_peek_title = task_title
        self.task_peek_side = random.choice(["right", "left"])

        font_family = config.load_font_family("DM Sans")
        font_task = QFont()
        font_task.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
        font_task.setPointSize(9)
        font_task.setWeight(QFont.Weight.Medium)
        fm = QFontMetrics(font_task)
        text_w = fm.horizontalAdvance(task_title)
        capped_text_w = min(220, max(60, text_w))

        # Size calculated using the original task components: Checkbox + Text + Focus Button
        cb_size = 16.0
        cb_gap = 9.0
        play_size = 16.0
        play_gap = 10.0
        card_pad_left = 10.0
        card_pad_right = 10.0

        card_w = card_pad_left + cb_size + cb_gap + capped_text_w + play_gap + play_size + card_pad_right
        margin_x = 18.0
        total_eyes_w = 49.0
        gap = 14.0
        target_w = int(margin_x + total_eyes_w + gap + card_w + margin_x)
        target_h = 42

        # Cache fixed card width and pre-computed elided text for maximum 60fps render performance
        self.task_peek_target_w = target_w
        self.task_peek_card_w = card_w
        avail_text_w = card_w - (card_pad_left + cb_size + cb_gap) - (play_gap + play_size + card_pad_right)
        self.task_peek_elided_title = fm.elidedText(task_title, Qt.TextElideMode.ElideRight, int(avail_text_w))

        if self.task_peek_side == "right":
            target_eyes_center = margin_x + (total_eyes_w / 2.0)
            self.target_eyes_offset_x = target_eyes_center - (target_w / 2.0)
            self.override_pupil = True
            self.override_pupil_x = 3.2
            self.override_pupil_y = 0.4
        else:
            target_eyes_center = target_w - margin_x - (total_eyes_w / 2.0)
            self.target_eyes_offset_x = target_eyes_center - (target_w / 2.0)
            self.override_pupil = True
            self.override_pupil_x = -3.2
            self.override_pupil_y = 0.4

        # Expressions for task peek: uses half-closed, curious, or wide (NO flat "- -" here)
        expr_choice = random.choice(["half_closed", "half_closed", "curious", "wide"])
        if expr_choice == "half_closed":
            self.target_half_closed = 1.0
        elif expr_choice == "curious":
            if self.task_peek_side == "right":
                self.target_left_eye_scale_x = 1.22
                self.target_left_eye_scale_y = 1.22
                self.target_right_eye_scale_x = 0.70
                self.target_right_eye_scale_y = 0.70
            else:
                self.target_left_eye_scale_x = 0.70
                self.target_left_eye_scale_y = 0.70
                self.target_right_eye_scale_x = 1.22
                self.target_right_eye_scale_y = 1.22
        elif expr_choice == "wide":
            self.target_left_eye_scale_x = 1.15
            self.target_left_eye_scale_y = 1.15
            self.target_right_eye_scale_x = 1.15
            self.target_right_eye_scale_y = 1.15

        self.animate_to(target_w, target_h, duration=320, easing=QEasingCurve.Type.OutQuad)
        self.task_peek_restore_timer.start(4500)

    def end_task_peek(self):
        """Collapses task peek back to ground stage and centers eyes with smooth easing."""
        if not self.task_peek_active:
            return

        self.task_collapsing = True
        self.target_eyes_offset_x = 0.0

        def on_collapse_done():
            if not self._is_hovered and not self.is_creating_task:
                self.task_peek_active = False
                self.task_collapsing = False
                self.task_peek_opacity = 0.0
                self.eyes_offset_x = 0.0
                self.reset_expression()
                self.update()

        self.animate_to(self.idle_w, self.idle_h, duration=260, easing=QEasingCurve.Type.OutQuad)
        if self.anim:
            self.anim.finished.connect(on_collapse_done)
        QTimer.singleShot(280, on_collapse_done)

    def cancel_idle_animations(self):
        """Immediately and cleanly interrupts any active idle animation."""
        if self.time_peek_active:
            self.time_peek_restore_timer.stop()
            self.time_peek_active = False
            self.time_peek_val = 0.0
            self.target_eyes_scroll_y = 0.0
            self.eyes_scroll_y = 0.0

        if self.task_peek_active:
            self.task_peek_restore_timer.stop()
            self.task_peek_active = False
            self.task_collapsing = False
            self.task_peek_opacity = 0.0
            self.target_eyes_offset_x = 0.0
            self.eyes_offset_x = 0.0

        if (self.expression_active or self.target_flat_eyes > 0 or 
            self.target_half_closed > 0 or self.override_pupil or 
            self.target_left_eye_scale_x != 1.0 or self.target_right_eye_scale_x != 1.0):
            self.expression_restore_timer.stop()
            self.reset_expression()

    def pick_random_task(self):
        """Picks a random task from the user's tasks list."""
        tasks = []
        if self.main_window and hasattr(self.main_window, "tasks"):
            tasks = list(self.main_window.tasks)
        else:
            tasks = config.load_tasks()

        if tasks:
            # If multiple tasks, prefer picking a different one on subsequent hovers
            if len(tasks) > 1 and self.current_random_task in tasks:
                remaining = [t for t in tasks if t != self.current_random_task]
                self.current_random_task = random.choice(remaining)
            else:
                self.current_random_task = random.choice(tasks)
        else:
            self.current_random_task = None

        self.hover_w = self.calc_expanded_width()

    def wheelEvent(self, event):
        if getattr(self, "app_search_in_notch", False):
            widget = getattr(self, "app_search_widget", None)
            if widget and hasattr(widget, "scroll"):
                bar = widget.scroll.verticalScrollBar()
                if bar:
                    delta = event.angleDelta().y() or event.pixelDelta().y()
                    if delta:
                        bar.setValue(bar.value() - delta)
            event.accept()
            return

        if getattr(self, "ai_chat_in_notch", False):
            if hasattr(self, "ai_chat_widget") and self.ai_chat_widget and hasattr(self.ai_chat_widget, "scroll"):
                bar = self.ai_chat_widget.scroll.verticalScrollBar()
                if bar:
                    delta = event.angleDelta().y()
                    bar.setValue(bar.value() - delta)
            event.accept()
            return

        if getattr(self, "reminders_in_notch", False):
            if hasattr(self, "reminder_widget") and self.reminder_widget:
                if getattr(self.reminder_widget, "_mode", "") == "list" and hasattr(self.reminder_widget, "reminder_list"):
                    bar = self.reminder_widget.reminder_list.scroll.verticalScrollBar()
                    if bar:
                        delta = event.angleDelta().y()
                        bar.setValue(bar.value() - delta)
            event.accept()
            return

        if self.tasks_in_notch:
            pixels = event.pixelDelta().y()
            if pixels:
                self._scroll_tasks_notch(-float(pixels))
            else:
                angle = event.angleDelta().y()
                if angle:
                    # One row per wheel notch keeps the feel predictable on a mouse
                    pitch = self._tasks_pitch()
                    self._scroll_tasks_notch(pitch if angle < 0 else -pitch)
            event.accept()
            return

        if self.notes_in_notch:
            delta = event.angleDelta().y()
            if delta < 0:
                self.next_notes_page()
            elif delta > 0:
                self.prev_notes_page()
            event.accept()
            return

        # When in hover state, scrolled on tasks (or notch), cycle / rotate other tasks
        if (self._is_hovered or self.height() > 38) and not self.add_expanded and not self.notes_in_notch and not self.tasks_in_notch and not self.is_creating_task and not self.is_creating_note and not self.timer_in_notch and not self.timer_is_running and not getattr(self, "ai_chat_in_notch", False) and not getattr(self, "media_in_notch", False) and not getattr(self, "reminders_in_notch", False) and not getattr(self, "app_search_in_notch", False):
            tasks = []
            if self.main_window and hasattr(self.main_window, "tasks"):
                tasks = list(self.main_window.tasks)
            else:
                tasks = config.load_tasks()

            if len(tasks) > 1:
                delta = event.angleDelta().y()
                if delta == 0:
                    delta = event.angleDelta().x()
                if delta != 0:
                    curr_idx = 0
                    if self.current_random_task in tasks:
                        curr_idx = tasks.index(self.current_random_task)
                    step = 1 if delta < 0 else -1
                    next_idx = (curr_idx + step) % len(tasks)
                    self.current_random_task = tasks[next_idx]
                    self.task_completed_anim = False
                    self.hover_w = self.calc_expanded_width()
                    self.animate_to(self.hover_w, self.hover_h)
                    self.update()
                    event.accept()
                    return

        super().wheelEvent(event)

    def enterEvent(self, event):
        self._is_hovered = True
        self.unhover_collapse_timer.stop()
        if hasattr(self, "empty_notes_restore_timer") and not getattr(self, "empty_notes_showing", False):
            self.empty_notes_restore_timer.stop()
        if not getattr(self, "empty_notes_showing", False):
            self.empty_notes_showing = False
        if hasattr(self, "sub_pill_leave_timer"):
            self.sub_pill_leave_timer.stop()
        self.cancel_idle_animations()

        if getattr(self, "ai_chat_in_notch", False) or getattr(self, "reminders_in_notch", False):
            if event:
                super().enterEvent(event)
            return

        if getattr(self, "media_in_notch", False):
            if self.timer_in_notch:
                # Paused timer row stays open while the cursor is on the notch
                if not self.timer_is_running and hasattr(self, "timer_stopped_collapse_timer"):
                    self.timer_stopped_collapse_timer.stop()
                if not self.add_expanded and not self.is_creating_task and not self.is_creating_note and not self.notes_in_notch:
                    self.update_notch_timer_geometry()
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
                if not self.sub_pill.isVisible() and not self.sub_pill_hover_timer.isActive():
                    self.sub_pill_hover_timer.start(500)
            if event:
                super().enterEvent(event)
            return

        if getattr(self, "dictation_in_notch", False):
            if event:
                super().enterEvent(event)
            return

        if self.timer_in_notch:
            if not self.timer_is_running:
                if hasattr(self, "timer_stopped_collapse_timer"):
                    self.timer_stopped_collapse_timer.stop()
            if not self.add_expanded and not self.is_creating_task and not self.is_creating_note and not self.notes_in_notch:
                self.update_notch_timer_geometry()
        elif not self.add_expanded and not self.is_creating_task and not self.is_creating_note and not self.notes_in_notch and not self.tasks_in_notch and not getattr(self, "ai_chat_in_notch", False) and not getattr(self, "reminders_in_notch", False) and not getattr(self, "app_search_in_notch", False):
            self.pick_random_task()
            self.task_completed_anim = False
            self.hover_w = self.calc_expanded_width()
            self.animate_to(self.hover_w, self.hover_h)

        # Start timer to show sub-pill after 0.5s of hovering
        if hasattr(self, "sub_pill") and not self.sub_pill.isVisible() and not self.sub_pill_hover_timer.isActive() and not getattr(self, "ai_chat_in_notch", False) and not getattr(self, "reminders_in_notch", False) and not getattr(self, "app_search_in_notch", False):
            self.sub_pill_hover_timer.start(500)

        if event:
            super().enterEvent(event)

    def leaveEvent(self, event):
        if getattr(self, "active_update_alert", None) is not None:
            self.hover_update_now = False
            self.hover_update_later = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            if event:
                super().leaveEvent(event)
            return

        if getattr(self, "active_reminder_alert", None) is not None:
            self.hover_reminder_dismiss = False
            self.hover_reminder_snooze = False
            self.hover_reminder_done = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            if event:
                super().leaveEvent(event)
            return

        if hasattr(self, "sub_pill_hover_timer"):
            self.sub_pill_hover_timer.stop()

        if getattr(self, "app_search_in_notch", False):
            # Keep app search open while user is interacting or typing
            if event:
                super().leaveEvent(event)
            return

        if self.ai_chat_in_notch:
            # Keep mini AI chat open while user is interacting or viewing responses
            if event:
                super().leaveEvent(event)
            return

        if getattr(self, "media_in_notch", False):
            # If sub-pill is open, give a 350ms grace period so user can cross into the sub-pill
            if hasattr(self, "sub_pill") and self.sub_pill.isVisible():
                self.sub_pill_leave_timer.start(350)
            self._is_hovered = False
            self.hover_media_play = False
            self.hover_media_prev = False
            self.hover_media_next = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            if event:
                super().leaveEvent(event)
            return

        if getattr(self, "dictation_in_notch", False):
            # Keep listening HUD open for the full dictation session
            if getattr(self, "hover_dictation_cancel", False):
                self.hover_dictation_cancel = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()
            if event:
                super().leaveEvent(event)
            return

        if self.is_creating_task or self.is_creating_note:
            # Don't collapse if user is actively in the middle of creating a task or note
            if event:
                super().leaveEvent(event)
            return

        if self.tasks_in_notch:
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill_leave_timer.start(450)
                if event:
                    super().leaveEvent(event)
                return
            self.tasks_in_notch = False
            self.notch_task_rects = []
            self.notch_task_cb_rects = []
            self.hovered_task_idx = None
            self.hovered_task_cb_idx = None
            self.collapse_to_idle()
            if event:
                super().leaveEvent(event)
            return

        if self.notes_in_notch:
            if getattr(self, "empty_notes_showing", False):
                # Don't immediately collapse; wait for empty_notes_restore_timer to complete 2.2s
                self._is_hovered = False
                if event:
                    super().leaveEvent(event)
                return
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill_leave_timer.start(450)
                if event:
                    super().leaveEvent(event)
                return
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
            self.collapse_to_idle()
            if event:
                super().leaveEvent(event)
            return

        if getattr(self, "reminders_in_notch", False):
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill_leave_timer.start(450)
                if event:
                    super().leaveEvent(event)
                return
            if hasattr(self, "sub_pill") and self.sub_pill:
                self.sub_pill.set_vertical_mode(False)
            self.collapse_to_idle()
            if event:
                super().leaveEvent(event)
            return

        # If sub-pill is open, give a 450ms grace period so user can cross into the sub-pill
        if hasattr(self, "sub_pill") and self.sub_pill.isVisible():
            self.sub_pill_leave_timer.start(450)
            if self.timer_is_running:
                self._is_hovered = False
                self.hover_play = False
                self.hover_cb = False
                self.hover_card = False
                self.hover_add_btn = False
                self.timer_hover_play = False
                self.timer_hover_restart = False
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()
            if event:
                super().leaveEvent(event)
            return

        if self.timer_is_running:
            # While timer is running / active, keep timer in notch (do NOT collapse to idle)
            self._is_hovered = False
            self.hover_play = False
            self.hover_cb = False
            self.hover_card = False
            self.hover_add_btn = False
            self.timer_hover_play = False
            self.timer_hover_restart = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            if event:
                super().leaveEvent(event)
            return

        if self.timer_in_notch and not self.timer_is_running:
            self._is_hovered = False
            self.hover_play = False
            self.hover_cb = False
            self.hover_card = False
            self.hover_add_btn = False
            self.timer_hover_play = False
            self.timer_hover_restart = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
            if hasattr(self, "timer_stopped_collapse_timer") and self.timer_stopped_collapse_timer.isActive():
                if event:
                    super().leaveEvent(event)
                return
            else:
                self.collapse_to_idle()
                if event:
                    super().leaveEvent(event)
                return

        if self.add_expanded:
            # When add button / capsule is open, give a 5-second grace period before collapsing to ground stage
            self.unhover_collapse_timer.start(5000)
            self._is_hovered = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if event:
                super().leaveEvent(event)
            return

        self.collapse_to_idle()
        if event:
            super().leaveEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()

        # Handle dictation cancel button hover regardless of height
        if getattr(self, "dictation_in_notch", False):
            new_cancel = hasattr(self, "dictation_cancel_rect") and self.dictation_cancel_rect.contains(pos)
            self.setCursor(Qt.CursorShape.PointingHandCursor if new_cancel else Qt.CursorShape.ArrowCursor)
            if new_cancel != getattr(self, "hover_dictation_cancel", False):
                self.hover_dictation_cancel = new_cancel
                self.update()
            return

        # Handle reminder alert buttons hover (Dismiss, Snooze, Done)
        if getattr(self, "active_reminder_alert", None) is not None:
            new_dismiss = hasattr(self, "reminder_dismiss_rect") and self.reminder_dismiss_rect.contains(pos)
            new_snooze = hasattr(self, "reminder_snooze_rect") and self.reminder_snooze_rect.contains(pos)
            new_done = hasattr(self, "reminder_done_rect") and self.reminder_done_rect.contains(pos)
            is_hand = new_dismiss or new_snooze or new_done
            self.setCursor(Qt.CursorShape.PointingHandCursor if is_hand else Qt.CursorShape.ArrowCursor)
            if (new_dismiss != getattr(self, "hover_reminder_dismiss", False) or
                new_snooze != getattr(self, "hover_reminder_snooze", False) or
                new_done != getattr(self, "hover_reminder_done", False)):
                self.hover_reminder_dismiss = new_dismiss
                self.hover_reminder_snooze = new_snooze
                self.hover_reminder_done = new_done
                self.update()
            return

        # Handle update alert buttons hover (Update now, Remind later)
        if getattr(self, "active_update_alert", None) is not None:
            new_now = hasattr(self, "update_now_rect") and self.update_now_rect.contains(pos)
            new_later = hasattr(self, "update_later_rect") and self.update_later_rect.contains(pos)
            is_hand = new_now or new_later
            self.setCursor(Qt.CursorShape.PointingHandCursor if is_hand else Qt.CursorShape.ArrowCursor)
            if (new_now != getattr(self, "hover_update_now", False) or
                new_later != getattr(self, "hover_update_later", False)):
                self.hover_update_now = new_now
                self.hover_update_later = new_later
                self.update()
            return

        if (self._is_hovered or self.add_expanded or self.timer_in_notch or self.notes_in_notch or self.tasks_in_notch or self.is_creating_note or self.is_creating_task or getattr(self, "ai_chat_in_notch", False) or getattr(self, "media_in_notch", False) or getattr(self, "reminders_in_notch", False)) and self.height() > 38:
            if self.unhover_collapse_timer.isActive():
                self.unhover_collapse_timer.stop()
                self._is_hovered = True
            if hasattr(self, "sub_pill_leave_timer") and self.sub_pill_leave_timer.isActive():
                self.sub_pill_leave_timer.stop()
                self._is_hovered = True

            if getattr(self, "media_in_notch", False):
                media_hand, changed = self._media_button_hover_flags(pos)
                if media_hand:
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                elif not self.timer_in_notch:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                if changed:
                    self.update()
                if not self.timer_in_notch:
                    if hasattr(self, "sub_pill") and self.sub_pill and not self.sub_pill.isVisible() and not self.sub_pill_hover_timer.isActive():
                        self.sub_pill.set_vertical_mode(False)
                        self.sub_pill_hover_timer.start(500)
                    return

            if getattr(self, "ai_chat_in_notch", False):
                new_ai_close = hasattr(self, "notch_ai_close_rect") and self.notch_ai_close_rect.contains(pos)
                self.setCursor(Qt.CursorShape.PointingHandCursor if new_ai_close else Qt.CursorShape.ArrowCursor)
                if new_ai_close != self.hover_ai_close:
                    self.hover_ai_close = new_ai_close
                    self.update()
                return

            if self.tasks_in_notch and not (self.is_creating_task or self.is_creating_note):
                new_task_cb_idx = None
                new_task_play_idx = None
                new_task_idx = None
                for rect, idx, text in self.notch_task_cb_rects:
                    if rect.contains(pos):
                        new_task_cb_idx = idx
                        break
                for rect, idx, text in self.notch_task_play_rects:
                    if rect.contains(pos):
                        new_task_play_idx = idx
                        break
                # Row hover only if not on cb or play button
                if new_task_cb_idx is None and new_task_play_idx is None:
                    for rect, idx, text in self.notch_task_rects:
                        if rect.contains(pos):
                            new_task_idx = idx
                            break
                capsule_hand = self._add_capsule_hover(pos)
                is_hand = (new_task_cb_idx is not None or new_task_play_idx is not None
                           or new_task_idx is not None or capsule_hand)
                self.setCursor(Qt.CursorShape.PointingHandCursor if is_hand else Qt.CursorShape.ArrowCursor)
                if (new_task_cb_idx != self.hovered_task_cb_idx or
                        new_task_play_idx != self.hovered_task_play_idx or
                        new_task_idx != self.hovered_task_idx):
                    self.hovered_task_cb_idx = new_task_cb_idx
                    self.hovered_task_play_idx = new_task_play_idx
                    self.hovered_task_idx = new_task_idx
                    self.update()
            elif self.is_creating_note:
                new_tick = self.note_tick_rect.contains(pos)
                new_cross = self.note_cross_rect.contains(pos)
                new_delete = self.note_delete_rect.contains(pos) if getattr(self, "editing_note_index", None) is not None else False
                new_add = self.add_toggle_rect.contains(pos) if self.add_expanded else False
                is_hand = (new_tick or new_cross or new_delete or new_add)
                self.setCursor(Qt.CursorShape.PointingHandCursor if is_hand else Qt.CursorShape.ArrowCursor)
                if (new_tick != self.hover_note_tick or new_cross != self.hover_note_cross or 
                    new_delete != self.hover_note_delete or new_add != self.hover_add_btn):
                    self.hover_note_tick = new_tick
                    self.hover_note_cross = new_cross
                    self.hover_note_delete = new_delete
                    self.hover_add_btn = new_add
                    self.update()
            elif self.notes_in_notch:
                new_copy_idx = None
                new_card_idx = None
                for rect, idx, text in self.notch_note_copy_rects:
                    if rect.contains(pos):
                        new_copy_idx = idx
                        break
                for rect, idx, text in self.notch_note_rects:
                    if rect.contains(pos):
                        new_card_idx = idx
                        break
                new_add = self.add_toggle_rect.contains(pos) if self.add_expanded else self.add_btn_rect.contains(pos)
                is_hand = (new_copy_idx is not None or new_card_idx is not None or new_add)
                self.setCursor(Qt.CursorShape.PointingHandCursor if is_hand else Qt.CursorShape.ArrowCursor)
                if new_copy_idx != self.hovered_note_copy_idx or new_card_idx != self.hovered_note_card_idx or new_add != self.hover_add_btn:
                    self.hovered_note_copy_idx = new_copy_idx
                    self.hovered_note_card_idx = new_card_idx
                    self.hover_add_btn = new_add
                    self.update()
            elif self.timer_in_notch:
                new_timer_play = self.timer_play_rect.contains(pos)
                new_timer_restart = self.timer_restart_rect.contains(pos)
                new_cb = self.task_cb_rect.contains(pos) if self.timer_task_title else False
                new_add = self.add_toggle_rect.contains(pos) if self.add_expanded else self.add_btn_rect.contains(pos)
                new_sub_task = self.sub_task_rect.contains(pos) if self.add_expanded else False
                new_sub_note = self.sub_note_rect.contains(pos) if self.add_expanded else False
                new_sub_reminder = self.sub_reminder_rect.contains(pos) if self.add_expanded else False

                is_hand = (new_timer_play or new_timer_restart or new_cb or new_add or new_sub_task or new_sub_note or new_sub_reminder
                           or self.hover_media_prev or self.hover_media_play or self.hover_media_next)
                self.setCursor(Qt.CursorShape.PointingHandCursor if is_hand else Qt.CursorShape.ArrowCursor)

                if (new_timer_play != self.timer_hover_play or
                    new_timer_restart != self.timer_hover_restart or
                    new_cb != self.hover_cb or
                    new_add != self.hover_add_btn or
                    new_sub_task != self.hover_sub_task or
                    new_sub_note != self.hover_sub_note or
                    new_sub_reminder != self.hover_sub_reminder):
                    self.timer_hover_play = new_timer_play
                    self.timer_hover_restart = new_timer_restart
                    self.hover_cb = new_cb
                    self.hover_add_btn = new_add
                    self.hover_sub_task = new_sub_task
                    self.hover_sub_note = new_sub_note
                    self.hover_sub_reminder = new_sub_reminder
                    self.update()
            elif self.add_expanded:
                new_sub_task = self.sub_task_rect.contains(pos)
                new_sub_note = self.sub_note_rect.contains(pos)
                new_sub_reminder = self.sub_reminder_rect.contains(pos)
                new_add_btn = self.add_toggle_rect.contains(pos)

                if new_sub_task or new_sub_note or new_sub_reminder or new_add_btn:
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)

                if (new_sub_task != self.hover_sub_task or
                    new_sub_note != self.hover_sub_note or
                    new_sub_reminder != self.hover_sub_reminder or
                    new_add_btn != self.hover_add_btn):
                    self.hover_sub_task = new_sub_task
                    self.hover_sub_note = new_sub_note
                    self.hover_sub_reminder = new_sub_reminder
                    self.hover_add_btn = new_add_btn
                    self.update()
            else:
                new_hover_btn = self.add_btn_rect.contains(pos)
                new_hover_card = self.task_card_rect.contains(pos)
                new_hover_cb = self.task_cb_rect.contains(pos)
                new_hover_play = self.task_play_rect.contains(pos)

                if new_hover_btn or new_hover_card or new_hover_cb or new_hover_play:
                    self.setCursor(Qt.CursorShape.PointingHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)

                if (new_hover_btn != self.hover_add_btn or
                    new_hover_card != self.hover_card or
                    new_hover_cb != self.hover_cb or
                    new_hover_play != self.hover_play):
                    self.hover_add_btn = new_hover_btn
                    self.hover_card = new_hover_card
                    self.hover_cb = new_hover_cb
                    self.hover_play = new_hover_play
                    self.update()
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def _on_sub_pill_hover_trigger(self):
        """Called after 0.5s of hovering on the notch to display the sub-pill."""
        if getattr(self, "ai_chat_in_notch", False) or getattr(self, "dictation_in_notch", False):
            return
        if self._is_hovered and not self.is_typing:
            if hasattr(self, "sub_pill"):
                if getattr(self, "media_in_notch", False):
                    self.sub_pill.set_vertical_mode(False)
                self.sub_pill.show_animated()

    def _on_sub_pill_leave_timeout(self):
        """Called when mouse leaves both notch and sub-pill after 350ms grace period."""
        if getattr(self, "ai_chat_in_notch", False) or getattr(self, "dictation_in_notch", False):
            return
        cursor_pos = QCursor.pos()
        notch_contains = self.geometry().contains(cursor_pos)
        sub_pill_contains = self.sub_pill.geometry().contains(cursor_pos) if (hasattr(self, "sub_pill") and self.sub_pill.isVisible()) else False

        if notch_contains or sub_pill_contains:
            return

        if self.is_creating_task or self.is_creating_note or getattr(self, "empty_notes_showing", False):
            return

        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.set_vertical_mode(False)
            if getattr(self, "media_in_notch", False) or self.timer_is_running:
                if self.sub_pill.isVisible():
                    self.sub_pill.hide_animated()

        if getattr(self, "media_in_notch", False):
            # Keep media player in notch active (do not collapse to idle)
            return

        # If timer was just spawned or stopped and waiting for user to click play or collapse,
        # let timer_stopped_collapse_timer govern the timeout so it doesn't vanish in 350ms
        if self.timer_in_notch and not self.timer_is_running:
            if hasattr(self, "timer_stopped_collapse_timer") and self.timer_stopped_collapse_timer.isActive():
                return

        if self.timer_is_running:
            # While timer is running / focus mode, keep timer in notch (do NOT collapse to idle)
            return

        self.collapse_to_idle()

    def hideEvent(self, event):
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.hide()
        super().hideEvent(event)

    def closeEvent(self, event):
        if hasattr(self, "sub_pill") and self.sub_pill:
            self.sub_pill.close()
        super().closeEvent(event)

    def on_play_task_clicked(self):
        """Start task focus with timer spawning inside the task card."""
        if not self.current_random_task:
            return
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        self.timer_in_notch = True
        self.timer_task_title = self.current_random_task
        self.timer_is_running = True
        self.is_active_focus = True
        self.timer_ms = 0
        self.timer_time_peek_active = False
        self.notch_stopwatch_timer.start(1000)
        self.timer_peek_scheduler.start(random.randint(12000, 20000))
        if self.main_window and hasattr(self.main_window, "toolbar") and self.main_window.toolbar:
            self.main_window.toolbar.start_stopwatch_for_task()
        self.update_notch_timer_geometry()
        self.update()

    def _start_task_from_notch_list(self, task_text):
        """Start a focus timer for a task clicked in the expanded tasks list view."""
        if not task_text:
            return
        self.current_random_task = task_text
        self.tasks_in_notch = False
        self.notch_task_rects = []
        self.notch_task_cb_rects = []
        self.notch_task_play_rects = []
        self.hovered_task_idx = None
        self.hovered_task_cb_idx = None
        self.hovered_task_play_idx = None
        # Start focus timer exactly like on_play_task_clicked but for this specific task
        if hasattr(self, "timer_stopped_collapse_timer"):
            self.timer_stopped_collapse_timer.stop()
        self.timer_in_notch = True
        self.timer_task_title = task_text
        self.timer_is_running = True
        self.is_active_focus = True
        self.timer_ms = 0
        self.timer_time_peek_active = False
        self.notch_stopwatch_timer.start(1000)
        self.timer_peek_scheduler.start(random.randint(12000, 20000))
        if self.main_window and hasattr(self.main_window, "toolbar") and self.main_window.toolbar:
            self.main_window.toolbar.start_stopwatch_for_task()
        self.update_notch_timer_geometry()
        self.update()

    def _complete_task_from_notch_list(self, idx, task_text):
        """Complete a specific task clicked in the expanded tasks list view."""
        if not task_text or self.completing_task_text == task_text:
            return

        def do_complete():
            self.completing_task_text = None
            self.complete_row_anim.stop()
            self._complete_row_progress = 0.0

            if self.main_window and hasattr(self.main_window, "complete_task"):
                self.main_window.complete_task(task_text)
            else:
                tasks = config.load_tasks()
                if task_text in tasks:
                    tasks.remove(task_text)
                    config.save_tasks(tasks)

            # If this was the currently shown task in the header, pick another
            if self.current_random_task == task_text:
                self.pick_random_task()

            # Refresh the tasks list view
            all_tasks = self._get_tasks_list()
            if not all_tasks:
                self.tasks_in_notch = False
                self.notch_task_rects = []
                self.notch_task_cb_rects = []
                self.hovered_task_idx = None
                self.hovered_task_cb_idx = None
                self.task_completed_anim = False
                self.hover_w = self.calc_expanded_width()
                self.animate_to(self.hover_w, self.hover_h)
            else:
                self.show_tasks_in_notch()
            self.update()

        self.completing_task_text = task_text
        self.complete_row_anim.stop()
        self._complete_row_progress = 0.0
        self.complete_row_anim.start()
        QTimer.singleShot(340, do_complete)

    def on_task_checkbox_clicked(self):
        """Mark task as completed, immediately stop timer if in focus mode, and return to ground state or pick next task."""
        task_to_complete = self.timer_task_title or self.current_random_task
        if not task_to_complete or self.task_completed_anim:
            return

        was_in_focus = bool(self.is_active_focus or self.timer_is_running or (self.timer_in_notch and self.timer_task_title))

        # 1. Immediately stop all timers if in focus mode without any delay
        if was_in_focus:
            self.timer_is_running = False
            self.is_active_focus = False
            self.notch_stopwatch_timer.stop()
            self.timer_peek_scheduler.stop()
            self.timer_peek_restore_timer.stop()
            self.timer_time_peek_active = False
            self.timer_ms = 0
            if hasattr(self, "timer_stopped_collapse_timer"):
                self.timer_stopped_collapse_timer.stop()
            if self.main_window and hasattr(self.main_window, "toolbar") and self.main_window.toolbar:
                if hasattr(self.main_window.toolbar, "stop_stopwatch"):
                    self.main_window.toolbar.stop_stopwatch()
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill.hide_animated()

        self.task_completed_anim = True
        self.update()

        def finalize_completion():
            if self.main_window and hasattr(self.main_window, "complete_task"):
                self.main_window.complete_task(task_to_complete)
            else:
                tasks = config.load_tasks()
                if task_to_complete in tasks:
                    tasks.remove(task_to_complete)
                    config.save_tasks(tasks)

            self.task_completed_anim = False
            self.is_active_focus = False
            self.timer_in_notch = False
            self.timer_is_running = False
            self.timer_task_title = None

            self.pick_random_task()

            if was_in_focus:
                if getattr(self, "media_in_notch", False):
                    self.update_media_geometry()
                else:
                    self.collapse_to_idle()
            else:
                self.animate_to(self.calc_expanded_width(), self.hover_h)
                self.update()

        QTimer.singleShot(350, finalize_completion)

    def animate_to(self, target_w, target_h, duration=None, easing=None):
        if getattr(self, "active_reminder_alert", None) is not None and target_h < 80:
            return
        if getattr(self, "active_update_alert", None) is not None and target_h < 80:
            return
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        screen_geo = screen.geometry()
        target_x = screen_geo.x() + (screen_geo.width() - target_w) // 2
        target_y = screen_geo.y()
        target_rect = QRect(target_x, target_y, target_w, target_h)

        if self.anim and self.anim.state() == QPropertyAnimation.State.Running:
            self.anim.stop()

        self.anim = QPropertyAnimation(self, b"geometry", self)
        if duration is None:
            duration = 300 if target_w > self.width() or target_h > self.height() else 250
        if easing is None:
            easing = QEasingCurve.Type.OutQuad
        self.anim.setDuration(duration)
        self.anim.setEasingCurve(easing)
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(target_rect)
        def on_anim_step():
            self.update()
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill.recenter_under_notch()
            if getattr(self, "ai_chat_in_notch", False):
                self.update_ai_chat_geometry()
            if getattr(self, "reminders_in_notch", False):
                self.update_reminder_geometry()
            if getattr(self, "app_search_in_notch", False):
                self.update_app_search_geometry()

        def on_anim_finished():
            self.ensure_stays_on_top()
            if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
                self.sub_pill.recenter_under_notch()
                if not self._is_hovered and self.width() <= self.idle_w + 5 and self.height() <= self.idle_h + 5:
                    self.sub_pill.hide_animated()
            if getattr(self, "reminders_in_notch", False):
                self.update_reminder_geometry()
            if getattr(self, "app_search_in_notch", False):
                self.update_app_search_geometry()

        self.anim.valueChanged.connect(on_anim_step)
        self.anim.finished.connect(on_anim_finished)
        self.anim.start()
        self.ensure_stays_on_top()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()

            # App search mode (children handle clicks)
            if getattr(self, "app_search_in_notch", False):
                return

            # Voice dictation cancel (×) - always interactive regardless of notch height
            if getattr(self, "dictation_in_notch", False):
                if hasattr(self, "dictation_cancel_rect") and self.dictation_cancel_rect.contains(pos):
                    self.cancel_dictation()
                    return
                return

            # Reminder alert buttons click (Dismiss, Snooze, Done)
            if getattr(self, "active_reminder_alert", None) is not None:
                if hasattr(self, "reminder_dismiss_rect") and self.reminder_dismiss_rect.contains(pos):
                    self.dismiss_reminder_alert()
                    return
                if hasattr(self, "reminder_snooze_rect") and self.reminder_snooze_rect.contains(pos):
                    self.snooze_reminder_alert()
                    return
                if hasattr(self, "reminder_done_rect") and self.reminder_done_rect.contains(pos):
                    self.complete_reminder_alert()
                    return
                return

            # Update alert buttons click (Update now, Remind later)
            if getattr(self, "active_update_alert", None) is not None:
                if hasattr(self, "update_now_rect") and self.update_now_rect.contains(pos):
                    self.start_update_from_alert()
                    return
                if hasattr(self, "update_later_rect") and self.update_later_rect.contains(pos):
                    self.dismiss_update_alert()
                    return
                return

            # When expanded, handle clicks on interactive elements only
            if self.height() > 38:

                # Media player in notch clicks (play/pause, prev, next)
                if getattr(self, "media_in_notch", False):
                    # Beside a timer row only the player block itself is claimed by media
                    if (not self.timer_in_notch) or self.media_block_rect.contains(pos):
                        if hasattr(self, "media_play_rect") and self.media_play_rect.contains(pos):
                            self.notch_media_play_pause()
                            return
                        if hasattr(self, "media_prev_rect") and self.media_prev_rect.contains(pos):
                            self.notch_media_prev()
                            return
                        if hasattr(self, "media_next_rect") and self.media_next_rect.contains(pos):
                            self.notch_media_next()
                            return
                    if not self.timer_in_notch:
                        return

                # Mini AI chat close button click
                if self.ai_chat_in_notch:
                    if hasattr(self, "notch_ai_close_rect") and self.notch_ai_close_rect.contains(pos):
                        self.collapse_ai_chat()
                        return
                    return

                # Reminders mode click handling (passed to reminder_widget children)
                if getattr(self, "reminders_in_notch", False):
                    if not getattr(self, "is_creating_reminder", False):
                        if self._route_add_click(pos):
                            return
                    if getattr(self, "timer_in_notch", False):
                        # Timer controls stay reachable while reminders are shown
                        if self.timer_play_rect.contains(pos):
                            self.toggle_notch_timer_playback()
                            return
                        if self.timer_restart_rect.contains(pos):
                            self.restart_notch_timer()
                            return
                        if self.timer_task_title and self.task_cb_rect.contains(pos):
                            self.on_task_checkbox_clicked()
                            return
                    return

                # 1. Note creation & editing clicks (combined tick / cross / delete pill)
                if self.is_creating_note:
                    if self.note_tick_rect.contains(pos):
                        self.submit_notch_note()
                        return
                    if self.note_cross_rect.contains(pos):
                        self.cancel_notch_note()
                        return
                    if getattr(self, "editing_note_index", None) is not None and self.note_delete_rect.contains(pos):
                        self.delete_notch_note()
                        return

                # 2. Tasks list view clicks (checkbox/play keep their own targets; the row completes)
                if self.tasks_in_notch and not self.is_creating_task:
                    # The capsule stays reachable above the list so Add works without collapsing first
                    if self._route_add_click(pos):
                        return
                    # Checkbox click: complete that specific task
                    for rect, idx, text in self.notch_task_cb_rects:
                        if rect.contains(pos):
                            self._complete_task_from_notch_list(idx, text)
                            return
                    # Play button click: start focus timer for that task
                    for rect, idx, text in self.notch_task_play_rects:
                        if rect.contains(pos):
                            self._start_task_from_notch_list(text)
                            return
                    # Row click anywhere else on the card: mark that task done
                    for rect, idx, text in self.notch_task_rects:
                        if rect.contains(pos):
                            self._complete_task_from_notch_list(idx, text)
                            return
                    return
                if self.is_creating_task:
                    # Only the capsule is live while the creation input owns the extended area
                    self._route_add_click(pos)
                    return

                # 3. Notes Grid view clicks (copy button or note card)
                if self.notes_in_notch:
                    for rect, idx, text in self.notch_note_copy_rects:
                        if rect.contains(pos):
                            cb = QApplication.clipboard()
                            if cb:
                                cb.setText(text)
                            self.copied_note_idx = idx
                            QTimer.singleShot(1500, self._clear_copied_note_feedback)
                            self.update()
                            return
                    for rect, idx, text in self.notch_note_rects:
                        if rect.contains(pos):
                            # Note card clicked; double-click will open inline editor
                            return

                if self.timer_in_notch:
                    if self.timer_play_rect.contains(pos):
                        self.toggle_notch_timer_playback()
                        return
                    if self.timer_restart_rect.contains(pos):
                        self.restart_notch_timer()
                        return
                    # In timer mode: checkbox marks done, card click does nothing extra
                    if self.timer_task_title and self.task_cb_rect.contains(pos):
                        self.on_task_checkbox_clicked()
                        return

                    # Add button / capsule handling while timer is in notch
                    if self.add_expanded:
                        if self.add_toggle_rect.contains(pos):
                            self.collapse_add_mode()
                            return
                        if self.sub_task_rect.contains(pos):
                            self.start_notch_task_creation()
                            return
                        if self.sub_note_rect.contains(pos):
                            self.start_notch_note_creation()
                            return
                        if self.sub_reminder_rect.contains(pos):
                            self.start_notch_reminder_creation()
                            return
                    else:
                        if self.add_btn_rect.contains(pos):
                            self.expand_add_mode()
                            return
                    return
                elif self.add_expanded:
                    if self.add_toggle_rect.contains(pos):
                        self.collapse_add_mode()
                        return
                    if self.sub_task_rect.contains(pos):
                        self.start_notch_task_creation()
                        return
                    if self.sub_note_rect.contains(pos):
                        self.start_notch_note_creation()
                        return
                    if self.sub_reminder_rect.contains(pos):
                        self.start_notch_reminder_creation()
                        return
                else:
                    if self.add_btn_rect.contains(pos):
                        self.expand_add_mode()
                        return
                    if self.task_play_rect.contains(pos):
                        self.on_play_task_clicked()
                        return
                    # Checkbox only -> mark done
                    if self.task_cb_rect.contains(pos):
                        self.on_task_checkbox_clicked()
                        return
                    # Task card (non-checkbox) -> expand tasks list
                    if self.task_card_rect.contains(pos):
                        self.show_tasks_in_notch()
                        return
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.globalPosition().toPoint())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self.notes_in_notch:
                pos = event.position().toPoint()
                # Ignore if double-click was on copy button
                for rect, idx, text in self.notch_note_copy_rects:
                    if rect.contains(pos):
                        return
                # If double-clicked on any note card, edit it inline
                for rect, idx, text in self.notch_note_rects:
                    if rect.contains(pos):
                        self.start_notch_note_editing(idx, text)
                        return
        super().mouseDoubleClickEvent(event)

    def show_context_menu(self, global_pos):
        menu = QMenu(self)

        act_toggle = menu.addAction("Show / Hide Ticky")
        def toggle_ticky():
            self.setVisible(not self.isVisible())
        act_toggle.triggered.connect(toggle_ticky)

        act_settings = menu.addAction("Settings")
        if self.main_window and hasattr(self.main_window, "show_settings_menu"):
            act_settings.triggered.connect(self.main_window.show_settings_menu)

        menu.addSeparator()
        act_quit = menu.addAction("Quit Ticky")
        act_quit.triggered.connect(QApplication.instance().quit)

        menu.exec(global_pos)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())

        if hasattr(self, "sub_pill") and self.sub_pill and self.sub_pill.isVisible():
            self.sub_pill.recenter_under_notch()

        # Scale curve radiuses smoothly with height
        h_ratio = max(0.0, min(1.0, (h - self.idle_h) / max(1.0, (self.hover_h - self.idle_h))))
        ear_r = 7.0 + h_ratio * 3.0      # 7px to 10px
        corner_r = 12.0 + h_ratio * 4.0  # 12px to 16px

        # Construct Apple MacBook notch silhouette
        path = QPainterPath()
        path.moveTo(0.0, 0.0)

        # Top-left ear (concave curve from screen edge into notch side)
        path.quadTo(ear_r, 0.0, ear_r, ear_r)

        # Left vertical side
        path.lineTo(ear_r, h - corner_r)

        # Bottom-left corner (convex curve into bottom)
        path.quadTo(ear_r, h, ear_r + corner_r, h)

        # Bottom edge
        path.lineTo(w - ear_r - corner_r, h)

        # Bottom-right corner (convex curve into right side)
        path.quadTo(w - ear_r, h, w - ear_r, h - corner_r)

        # Right vertical side
        path.lineTo(w - ear_r, ear_r)

        # Top-right ear (concave curve out to screen edge)
        path.quadTo(w - ear_r, 0.0, w, 0.0)

        # Top edge back to origin
        path.lineTo(0.0, 0.0)
        path.closeSubpath()

        # Dynamic theme background fill matching active UI theme (Obsidian, Midnight Blue, etc.)
        notch_bg = QColor(theme.BG_COLOR)
        notch_border = QColor(theme.BORDER_COLOR)
        if not notch_border.isValid():
            notch_border = QColor(255, 255, 255, 24)
        elif notch_border.alpha() < 30:
            notch_border.setAlpha(36)

        painter.setBrush(QBrush(notch_bg))
        painter.setPen(QPen(notch_border, 1.0))
        painter.drawPath(path)

        # Clip all internal drawing cleanly inside the notch path for pristine edges
        painter.save()
        painter.setClipPath(path)

        # Synchronize eye position and card opacity precisely with notch width progress
        if self.task_peek_active:
            target_w = float(getattr(self, "task_peek_target_w", 380))
            span = max(1.0, target_w - float(self.idle_w))
            progress = max(0.0, min(1.0, (w - float(self.idle_w)) / span))

            total_eyes_w = 49.0
            margin_x = 18.0
            if self.task_peek_side == "right":
                target_eyes_center = margin_x + (total_eyes_w / 2.0)
            else:
                target_eyes_center = target_w - margin_x - (total_eyes_w / 2.0)
            target_eyes_offset = target_eyes_center - (target_w / 2.0)

            self.eyes_offset_x = target_eyes_offset * progress

            if progress < 0.50:
                self.task_peek_opacity = 0.0
            else:
                self.task_peek_opacity = min(1.0, (progress - 0.50) / 0.40)

        # -------------------------------------------------------------
        # Opacity Crossfade: Eyes fade while expanding, Time displays once expanded
        # -------------------------------------------------------------
        # Only crossfade to expanded header when hovered or creating task/note or timer/notes is in notch
        if getattr(self, "dictation_in_notch", False):
            eyes_opacity = 0.0
            time_opacity = 0.0
        elif getattr(self, "ai_chat_in_notch", False):
            eyes_opacity = 1.0
            time_opacity = 0.0
        elif getattr(self, "media_in_notch", False) and not self.timer_in_notch:
            eyes_opacity = 0.0
            time_opacity = 0.0
        elif self._is_hovered or self.add_expanded or self.is_creating_task or self.is_creating_note or self.notes_in_notch or self.timer_in_notch or self.tasks_in_notch or getattr(self, "reminders_in_notch", False) or getattr(self, "active_reminder_alert", None) is not None or getattr(self, "active_update_alert", None) is not None:
            eyes_opacity = max(0.0, min(1.0, 1.0 - (h_ratio / 0.45)))
            time_opacity = max(0.0, min(1.0, (h_ratio - 0.50) / 0.50))
        else:
            eyes_opacity = 1.0
            time_opacity = 0.0

        accent_color = QColor(theme.ACCENT_COLOR)

        # Voice dictation listening HUD (waveform + cancel)
        if getattr(self, "dictation_in_notch", False):
            self._paint_dictation_hud(painter, w, h, accent_color)
            painter.restore()
            return

        # System-Wide App Search HUD
        if getattr(self, "app_search_in_notch", False):
            painter.restore()
            return

        # 1. Render Live Typewriter Text OR Cute Square Eyes (with silky smooth crossfade)
        if eyes_opacity > 0.001:
            eyes_blend = max(0.0, 1.0 - self.typing_blend) * eyes_opacity
            text_blend = self.typing_blend * eyes_opacity

            # Draw Eyes (smoothly squashing & fading when transitioning to typing)
            if eyes_blend > 0.005:
                trans_scale = 1.0 - (self.typing_blend * 0.35)
                base_eye_w = 19.0 * trans_scale
                base_eye_h = 19.0 * trans_scale
                eye_spacing = 11.0 * trans_scale
                base_eye_radius = 5.0 * trans_scale
                base_pupil_size = 8.5 * trans_scale
                base_pupil_radius = 2.5 * trans_scale
                glint_r = 1.6 * trans_scale

                total_eyes_w = base_eye_w * 2.0 + eye_spacing
                if getattr(self, "ai_chat_in_notch", False):
                    start_x = 20.0 + self.eyes_offset_x
                    center_eye_y = 19.0
                else:
                    start_x = (w - total_eyes_w) / 2.0 + self.eyes_offset_x
                    center_eye_y = (h / 2.0) + self.eyes_scroll_y

                # Blinking squash calculation
                scale_h = 1.0 - (self.blink_progress * 0.85)
                base_current_h = max(1.5, base_eye_h * scale_h)

                eye_col = QColor(accent_color)
                eye_col.setAlphaF(eyes_blend)

                # Flat eyes (- -) pupil and glint opacity fade out
                pupil_fade = max(0.0, 1.0 - (self.current_flat_eyes * 1.2))
                pupil_col = QColor(theme.BG_COLOR)
                pupil_col.setAlphaF(eyes_blend * pupil_fade)

                glint_alpha = int(230 * eyes_blend * pupil_fade)
                glint_col = QColor(255, 255, 255, glint_alpha)

                eye_scales = [
                    (self.current_left_eye_scale_x, self.current_left_eye_scale_y),
                    (self.current_right_eye_scale_x, self.current_right_eye_scale_y)
                ]

                ex_positions = [start_x, start_x + base_eye_w + eye_spacing]

                for idx, ex in enumerate(ex_positions):
                    sc_x, sc_y = eye_scales[idx]

                    # Scale for this specific eye
                    eye_w = base_eye_w * sc_x
                    normal_eye_h = base_current_h * sc_y

                    # Flat line eyes (- -) and Half-closed eyes calculation
                    flat_h = max(2.5, 3.2 * trans_scale)
                    half_closed_h = max(3.0, 9.5 * trans_scale * sc_y)

                    # First apply half-closed drooping
                    eye_h = (1.0 - self.current_half_closed) * normal_eye_h + self.current_half_closed * half_closed_h
                    eye_radius = (1.0 - self.current_half_closed) * base_eye_radius + self.current_half_closed * (3.8 * trans_scale)

                    # Then apply flat line squash if active (- -)
                    eye_h = (1.0 - self.current_flat_eyes) * eye_h + self.current_flat_eyes * flat_h
                    eye_radius = (1.0 - self.current_flat_eyes) * eye_radius + self.current_flat_eyes * (flat_h / 2.0)

                    # Center alignment
                    cur_ex = ex - (eye_w - base_eye_w) / 2.0
                    cur_ey = center_eye_y - (eye_h / 2.0)

                    # Outer eye
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QBrush(eye_col))
                    painter.drawRoundedRect(
                        QRectF(cur_ex, cur_ey, eye_w, eye_h),
                        eye_radius,
                        min(eye_radius, eye_h / 2.0)
                    )

                    # Inner pupil (moves towards cursor or gaze override)
                    if self.blink_progress < 0.7 and self.current_flat_eyes < 0.85:
                        pupil_w = base_pupil_size * sc_x
                        pupil_h_normal = max(1.5, base_pupil_size * sc_y * scale_h)
                        # When half-closed, pupil scales down proportionally so it fits nicely inside the eye
                        pupil_h = max(2.0, min(eye_h - 2.0, pupil_h_normal * (1.0 - 0.40 * self.current_half_closed)))

                        px = cur_ex + (eye_w - pupil_w) / 2.0 + (self.pupil_x * trans_scale)
                        py = cur_ey + (eye_h - pupil_h) / 2.0 + (self.pupil_y * trans_scale * (1.0 - 0.35 * self.current_half_closed))

                        painter.setBrush(QBrush(pupil_col))
                        painter.drawRoundedRect(
                            QRectF(px, py, pupil_w, pupil_h),
                            base_pupil_radius,
                            min(base_pupil_radius, pupil_h / 2.0)
                        )

                        # Cute sparkle glint
                        if self.blink_progress < 0.4 and self.current_flat_eyes < 0.5:
                            gx = cur_ex + (4.0 * trans_scale * sc_x)
                            gy = cur_ey + (3.0 * trans_scale * sc_y if self.current_half_closed > 0.5 else 4.0 * trans_scale * sc_y)
                            painter.setBrush(QBrush(glint_col))
                            painter.drawEllipse(QPointF(gx, gy), glint_r * (1.0 - 0.2 * self.current_half_closed), glint_r * (1.0 - 0.2 * self.current_half_closed))

            # Draw Ground Time Peek (rolling down from top)
            if self.time_peek_val > 0.005 and eyes_opacity > 0.5:
                self.draw_ground_time_peek(painter, w, h, self.time_peek_val * eyes_opacity * (1.0 - self.typing_blend), accent_color)

            # Draw Ground Task Peek Card (expanded pill)
            if self.task_peek_opacity > 0.005 and eyes_opacity > 0.5:
                self.draw_ground_task_peek(painter, w, h, self.task_peek_opacity * eyes_opacity * (1.0 - self.typing_blend), accent_color)

            # Draw Typewriter Text (smoothly scaling in with smooth caret & ribbon scroll)
            if text_blend > 0.005:
                self.draw_typewriter_text(painter, w, h, text_blend, accent_color)

        # Render Top Header Elements when in Mini AI Chat Mode
        if getattr(self, "ai_chat_in_notch", False):
            font_family = config.load_font_family("DM Sans")

            # Close Button [✕] at top-right
            close_size = 18.0
            close_x = w - 16.0 - close_size
            close_y = 9.0
            close_rect = QRectF(close_x, close_y, close_size, close_size)
            self.notch_ai_close_rect = QRect(int(close_x - 3), int(close_y - 3), int(close_size + 6), int(close_size + 6))

            # AI Provider & LLM Mode Text placed to the right of the Left Eyes
            provider_name = config.load_ai_provider("Gemini").strip()
            model_name = config.load_ai_model("gemini-1.5-flash").strip()

            text_x = 78.0
            max_text_w = max(80.0, close_x - text_x - 12.0)

            # 1. AI Provider (Title)
            font_provider = QFont()
            font_provider.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
            font_provider.setPointSize(9.5)
            font_provider.setWeight(QFont.Weight.Bold)
            painter.setFont(font_provider)
            painter.setPen(QColor(theme.TEXT_PRIMARY))
            painter.drawText(QRectF(text_x, 3.0, max_text_w, 16.0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, provider_name)

            # 2. LLM Mode (Subtitle below provider)
            font_model = QFont()
            font_model.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
            font_model.setPointSize(7.8)
            font_model.setWeight(QFont.Weight.Medium)
            painter.setFont(font_model)
            fm_model = QFontMetrics(font_model)
            elided_model = fm_model.elidedText(model_name, Qt.TextElideMode.ElideRight, int(max_text_w))
            painter.setPen(QColor(theme.TEXT_SECONDARY))
            painter.drawText(QRectF(text_x, 19.0, max_text_w, 14.0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided_model)

            # 3. Top-Right Close Button [✕]
            if self.hover_ai_close:
                h_bg = QColor(theme.HOVER_COLOR)
                h_bg.setAlpha(180)
                painter.setBrush(QBrush(h_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(close_rect, 5.0, 5.0)
                c_pen = QColor(255, 255, 255)
            else:
                c_pen = QColor(theme.TEXT_SECONDARY)

            painter.setPen(QPen(c_pen, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            cx = close_x + close_size / 2.0
            cy = close_y + close_size / 2.0
            p_len = 3.6
            painter.drawLine(QPointF(cx - p_len, cy - p_len), QPointF(cx + p_len, cy + p_len))
            painter.drawLine(QPointF(cx + p_len, cy - p_len), QPointF(cx - p_len, cy + p_len))


        # 2. Render Header (Time | Add Button | Random Task) once expanded
        media_shares_row = self.media_timer_combined()
        if time_opacity > 0.001 and not getattr(self, "ai_chat_in_notch", False) and (not getattr(self, "media_in_notch", False) or media_shares_row):
            self.draw_expanded_header(painter, w, h, time_opacity, accent_color)

        # 3. Render Media Player Controls once expanded (beside the timer row when both are open)
        if getattr(self, "media_in_notch", False):
            left_x = self._media_row_left_x if (media_shares_row and self._media_row_left_x > 0) else None
            if left_x is None:
                self._media_row_left_x = 0.0
            self.draw_media_in_notch(painter, w, h, 1.0, accent_color, left_x=left_x)

        painter.restore()

    def draw_ground_time_peek(self, painter, w, h, opacity, accent_color):
        """Draws the scrolling time and date peek in ground stage (spacious 200x38 notch)."""
        if opacity <= 0.001:
            return

        font_family = config.load_font_family("DM Sans")
        spec = self.clock_style_spec()
        now = QDateTime.currentDateTime()
        use_24h = config.load_use_24h(True)
        show_sec = config.load_show_seconds(False)

        time_str = self.clock_time_string(now, use_24h, show_sec)
        date_str = self.clock_date_string(now, spec)

        font_time, font_date = self.make_clock_fonts(11.0, 8.5)

        # Smooth vertical roll down
        roll_offset = (1.0 - self.time_peek_val) * 18.0

        painter.save()
        painter.setFont(font_time)
        peek_time_col = self.clock_time_color(accent_color, spec=spec)
        peek_time_col.setAlpha(int(245 * opacity))
        painter.setPen(peek_time_col)
        time_rect = QRectF(0, 3.5 - roll_offset, w, 17.5)
        painter.drawText(time_rect, Qt.AlignmentFlag.AlignCenter, time_str)

        if self.clock_date_visible(spec):
            painter.setFont(font_date)
            date_col = QColor(theme.TEXT_SECONDARY)
            painter.setPen(QColor(date_col.red(), date_col.green(), date_col.blue(), int(210 * opacity)))
            date_rect = QRectF(0, 21.0 - roll_offset, w, 14.0)
            painter.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, date_str)
        painter.restore()

    def draw_ground_task_peek(self, painter, w, h, opacity, accent_color):
        """Draws the expanded task peek card in ground stage (spacious 42px height notch)."""
        if opacity <= 0.001 or not self.task_peek_title:
            return

        card_h = 30.0
        card_y = (h - card_h) / 2.0
        margin_x = 18.0
        total_eyes_w = 49.0
        gap = 14.0

        card_w = float(getattr(self, "task_peek_card_w", 200.0))

        if self.task_peek_side == "right":
            card_x = margin_x + total_eyes_w + gap
        else:
            card_x = margin_x

        painter.save()

        # 1. Card Container: MAIN_CARD_COLOR background + task_color tinted rim
        card_rect = QRectF(card_x, card_y, card_w, card_h)
        card_bg = QColor(theme.MAIN_CARD_COLOR)
        card_bg.setAlpha(int(175 * opacity))

        task_color = QColor(get_task_color(self.task_peek_title))
        b_base = QColor(theme.BORDER_COLOR)
        r = b_base.red() + int((task_color.red() - b_base.red()) * 0.35)
        g = b_base.green() + int((task_color.green() - b_base.green()) * 0.35)
        b = b_base.blue() + int((task_color.blue() - b_base.blue()) * 0.35)
        card_border = QColor(r, g, b, int(75 * opacity))

        painter.setBrush(QBrush(card_bg))
        painter.setPen(QPen(card_border, 1.0))
        painter.drawRoundedRect(card_rect, 8.0, 8.0)

        # 2. Checkbox [ ] inside card with task color
        cb_size = 16.0
        cb_x = card_x + 10.0
        cb_y = card_y + (card_h - cb_size) / 2.0
        cb_rect = QRectF(cb_x, cb_y, cb_size, cb_size)
        cb_fill = QColor(task_color.red(), task_color.green(), task_color.blue(), int(38 * opacity))
        cb_border = QColor(task_color)
        cb_border.setAlphaF(opacity)
        painter.setBrush(QBrush(cb_fill))
        painter.setPen(QPen(cb_border, 1.3))
        painter.drawRoundedRect(cb_rect, 4.0, 4.0)

        # 3. Start Task / Focus Button on the right
        play_size = 16.0
        play_x = card_x + card_w - 10.0 - play_size
        play_y = card_y + (card_h - play_size) / 2.0
        play_rect = QRectF(play_x, play_y, play_size, play_size)
        colored_svg = FOCUS_SVG.replace("COLOR_PLACEHOLDER", task_color.name())
        renderer_focus = QSvgRenderer(QByteArray(colored_svg.encode("utf-8")))
        renderer_focus.render(painter, play_rect)

        # 4. Task text in task_color
        text_x = cb_x + cb_size + 9.0
        elided_text = getattr(self, "task_peek_elided_title", self.task_peek_title)

        if not hasattr(self, "cached_font_task") or self.cached_font_task is None:
            font_family = config.load_font_family("DM Sans")
            self.cached_font_task = QFont()
            self.cached_font_task.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
            self.cached_font_task.setPointSize(9)
            self.cached_font_task.setWeight(QFont.Weight.Medium)
            self.cached_fm_task = QFontMetrics(self.cached_font_task)

        painter.setFont(self.cached_font_task)
        text_col = QColor(task_color)
        text_col.setAlphaF(opacity)
        painter.setPen(text_col)
        text_y = card_y + (card_h / 2.0) + (self.cached_fm_task.capHeight() / 2.0)
        painter.drawText(QPointF(text_x, text_y), elided_text)

        painter.restore()

    def draw_expanded_header(self, painter, w, h, opacity, accent_color):
        """
        Draw the expanded notch header:
        - When timer_in_notch:
            [Time + Date Box (peek only)] [Timer Card (Standalone or Task Timer)] [Add Button / Capsule]
        - Normal mode:
            [Time + Date Box] [Task Card (Checkbox + Text + Start Task Button)] [Add Button / Capsule]
        """
        font_family = config.load_font_family("DM Sans")

        spec = self.clock_style_spec()
        font_time, font_date = self.make_clock_fonts(10, 8)

        font_task = QFont()
        font_task.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
        font_task.setPointSize(9)
        font_task.setWeight(QFont.Weight.Medium)
        if self.task_completed_anim:
            font_task.setStrikeOut(True)

        now = QDateTime.currentDateTime()
        use_24h = config.load_use_24h(True)
        show_sec = config.load_show_seconds(True)
        show_date = self.clock_date_visible(spec)

        time_str = self.clock_time_string(now, use_24h, show_sec)
        full_date = self.clock_date_string(now, spec)

        painter.setFont(font_time)
        fm_time = painter.fontMetrics()
        w_time = float(fm_time.horizontalAdvance(time_str))

        painter.setFont(font_date)
        fm_date = painter.fontMetrics()
        w_date = float(fm_date.horizontalAdvance(full_date)) if show_date else 0.0

        show_box = theme.CLOCK_BOX_BG
        time_content_w = max(w_time, w_date)
        time_box_w = (time_content_w + 20.0) if show_box else time_content_w
        time_box_h = 36.0

        add_btn_size = 28.0
        margin_x = 22.0
        gap_elements = 12.0
        capsule_w = 184.0

        # A media row beside the timer is taller, so that row centres on the notch height
        media_shares_row = self.media_timer_combined()
        if h >= 54.0 and not media_shares_row:
            top_cy = 27.0
        else:
            top_cy = h / 2.0

        # -------------------------------------------------------------
        # REMINDER DUE ALERT MODE
        # -------------------------------------------------------------
        if getattr(self, "active_reminder_alert", None) is not None:
            # 1. Left Cover Box with Bell Icon
            margin_left = 18.0
            cover_size = 58.0
            cover_y = (h - cover_size) / 2.0
            cover_rect = QRectF(margin_left, cover_y, cover_size, cover_size)

            # Draw cover container with stylish rounded corners
            cover_bg = QColor(theme.ACCENT_COLOR)
            cover_bg.setAlpha(int(36 * opacity))
            cover_border = QColor(theme.ACCENT_COLOR)
            cover_border.setAlpha(int(70 * opacity))
            painter.setBrush(QBrush(cover_bg))
            painter.setPen(QPen(cover_border, 1.0))
            painter.drawRoundedRect(cover_rect, 14.0, 14.0)

            # Render bell SVG inside cover box
            bell_svg = REMINDER_ALERT_BELL_SVG.replace("COLOR_PLACEHOLDER", accent_color.name())
            r_bell = QSvgRenderer(QByteArray(bell_svg.encode("utf-8")))
            bell_icon_size = 30.0
            bell_icon_rect = QRectF(
                cover_rect.x() + (cover_size - bell_icon_size) / 2.0,
                cover_rect.y() + (cover_size - bell_icon_size) / 2.0,
                bell_icon_size,
                bell_icon_size
            )
            r_bell.render(painter, bell_icon_rect)

            # 2. Content area (between cover box and the right-side button column)
            btn_h = 26.0
            btn_w = 84.0
            btn_gap = 8.0
            btn_x = w - 18.0 - btn_w
            stack_h = btn_h * 2 + btn_gap
            btn_y_top = (h - stack_h) / 2.0

            content_x = margin_left + cover_size + 14.0
            content_w = max(100.0, btn_x - 14.0 - content_x)

            # Top: Time
            hr = self.active_reminder_alert.get("hour", 0)
            mi = self.active_reminder_alert.get("minute", 0)
            date_disp = self.active_reminder_alert.get("date_display", "Today")
            use_24h_cfg = config.load_use_24h(True)
            if use_24h_cfg:
                t_str = f"{hr:02d}:{mi:02d}"
            else:
                period = "AM" if hr < 12 else "PM"
                h12 = hr % 12 or 12
                t_str = f"{h12}:{mi:02d} {period}"
            disp_time = f"{date_disp} • {t_str}"

            time_rect = QRectF(content_x, cover_y + 1.0, content_w, 15.0)
            font_rem_time = QFont(font_family, 9, QFont.Weight.Bold)
            font_rem_time.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
            painter.setFont(font_rem_time)
            time_col = QColor(theme.ACCENT_COLOR)
            time_col.setAlphaF(opacity)
            painter.setPen(time_col)
            painter.drawText(time_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, disp_time)

            # Middle: Reminder TITLE
            title_text = self.active_reminder_alert.get("title", "Reminder").strip()
            title_rect = QRectF(content_x, cover_y + 17.0, content_w, 20.0)
            font_rem_title = QFont(font_family, 12, QFont.Weight.Bold)
            painter.setFont(font_rem_title)
            fm_rem_title = painter.fontMetrics()
            elided_title = fm_rem_title.elidedText(title_text, Qt.TextElideMode.ElideRight, int(content_w))
            title_col = QColor("#FFFFFF")
            title_col.setAlphaF(opacity)
            painter.setPen(title_col)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_title)

            # Right column: stacked action buttons, [ Snooze ] above [ Done ]
            # Button 1: Snooze (top)
            snooze_rect = QRectF(btn_x, btn_y_top, btn_w, btn_h)
            self.reminder_snooze_rect = QRect(int(snooze_rect.x()), int(snooze_rect.y()), int(btn_w), int(btn_h))
            snz_hover = getattr(self, "hover_reminder_snooze", False)
            snz_bg = QColor(255, 179, 0, int((55 if snz_hover else 26) * opacity))
            snz_border = QColor(255, 179, 0, int((90 if snz_hover else 50) * opacity))
            painter.setBrush(QBrush(snz_bg))
            painter.setPen(QPen(snz_border, 1.0))
            painter.drawRoundedRect(snooze_rect, 8.0, 8.0)

            font_btn = QFont(font_family, 9, QFont.Weight.DemiBold)
            painter.setFont(font_btn)
            snz_text_col = QColor("#FFD54F" if snz_hover else "#FFB300")
            snz_text_col.setAlphaF(opacity)
            painter.setPen(snz_text_col)
            painter.drawText(snooze_rect, Qt.AlignmentFlag.AlignCenter, "Snooze")

            # Button 2: Done (below)
            done_rect = QRectF(btn_x, btn_y_top + btn_h + btn_gap, btn_w, btn_h)
            self.reminder_done_rect = QRect(int(done_rect.x()), int(done_rect.y()), int(btn_w), int(btn_h))
            done_hover = getattr(self, "hover_reminder_done", False)
            done_bg = QColor("#34C759").lighter(115) if done_hover else QColor("#30D158")
            done_bg.setAlphaF(opacity)
            painter.setBrush(QBrush(done_bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(done_rect, 8.0, 8.0)

            font_done = QFont(font_family, 9, QFont.Weight.Bold)
            painter.setFont(font_done)
            done_text_col = QColor("#FFFFFF")
            done_text_col.setAlphaF(opacity)
            painter.setPen(done_text_col)
            painter.drawText(done_rect, Qt.AlignmentFlag.AlignCenter, "Done")

            self.reminder_dismiss_rect = QRect()
            self.hover_reminder_dismiss = False

            # Clear normal mode rects
            self.time_box_rect = QRect()
            self.task_card_rect = QRect()
            self.task_cb_rect = QRect()
            self.task_play_rect = QRect()
            self.add_btn_rect = QRect()
            self.sub_task_rect = QRect()
            self.sub_note_rect = QRect()
            self.sub_reminder_rect = QRect()
            self.add_toggle_rect = QRect()
            return

        # -------------------------------------------------------------
        # SOFTWARE UPDATE ALERT MODE
        # -------------------------------------------------------------
        if getattr(self, "active_update_alert", None) is not None:
            status = getattr(self, "update_alert_status", "available")

            # 1. Left Cover Box with Download Icon
            margin_left = 18.0
            cover_size = 58.0
            cover_y = (h - cover_size) / 2.0
            cover_rect = QRectF(margin_left, cover_y, cover_size, cover_size)

            cover_bg = QColor(theme.ACCENT_COLOR)
            cover_bg.setAlpha(int(36 * opacity))
            cover_border = QColor(theme.ACCENT_COLOR)
            cover_border.setAlpha(int(70 * opacity))
            painter.setBrush(QBrush(cover_bg))
            painter.setPen(QPen(cover_border, 1.0))
            painter.drawRoundedRect(cover_rect, 14.0, 14.0)

            dl_svg = UPDATE_ALERT_DOWNLOAD_SVG.replace("COLOR_PLACEHOLDER", accent_color.name())
            r_dl = QSvgRenderer(QByteArray(dl_svg.encode("utf-8")))
            dl_icon_size = 30.0
            dl_icon_rect = QRectF(
                cover_rect.x() + (cover_size - dl_icon_size) / 2.0,
                cover_rect.y() + (cover_size - dl_icon_size) / 2.0,
                dl_icon_size,
                dl_icon_size
            )
            r_dl.render(painter, dl_icon_rect)

            # 2. Content area (between cover box and the right-side button column)
            btn_h = 26.0
            btn_w = 92.0
            btn_gap = 8.0
            btn_x = w - 18.0 - btn_w
            stack_h = btn_h * 2 + btn_gap
            btn_y_top = (h - stack_h) / 2.0

            content_x = margin_left + cover_size + 14.0
            content_w = max(100.0, btn_x - 14.0 - content_x)

            # Top: status line
            status_text = {
                "available": "UPDATE AVAILABLE",
                "downloading": "DOWNLOADING…",
                "ready": "READY TO INSTALL",
                "failed": "UPDATE FAILED",
            }.get(status, "UPDATE AVAILABLE")
            status_rect = QRectF(content_x, cover_y + 1.0, content_w, 15.0)
            font_upd_status = QFont(font_family, 9, QFont.Weight.Bold)
            font_upd_status.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
            painter.setFont(font_upd_status)
            status_col = QColor("#FF453A") if status == "failed" else QColor(theme.ACCENT_COLOR)
            status_col.setAlphaF(opacity)
            painter.setPen(status_col)
            painter.drawText(status_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, status_text)

            # Middle: release title
            version_text = str(getattr(self.active_update_alert, "version", "") or "").strip()
            title_text = f"Ticky {version_text}".strip() or "Ticky update"
            title_rect = QRectF(content_x, cover_y + 17.0, content_w, 20.0)
            font_upd_title = QFont(font_family, 12, QFont.Weight.Bold)
            painter.setFont(font_upd_title)
            elided_title = painter.fontMetrics().elidedText(title_text, Qt.TextElideMode.ElideRight, int(content_w))
            title_col = QColor("#FFFFFF")
            title_col.setAlphaF(opacity)
            painter.setPen(title_col)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_title)

            # Bottom: what's happening detail
            detail_text = getattr(self, "update_alert_detail", "") or ""
            detail_rect = QRectF(content_x, cover_y + 37.0, content_w, 14.0)
            font_upd_detail = QFont(font_family, 9)
            painter.setFont(font_upd_detail)
            elided_detail = painter.fontMetrics().elidedText(detail_text, Qt.TextElideMode.ElideRight, int(content_w))
            detail_col = QColor("#FFFFFF")
            detail_col.setAlphaF(opacity * 0.55)
            painter.setPen(detail_col)
            painter.drawText(detail_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_detail)

            # Right column: stacked action buttons, [ primary ] above [ secondary ]
            primary_label = {"failed": "Retry", "downloading": "Downloading…"}.get(status, "Update now")
            secondary_label = "Hide" if status == "downloading" else "Remind later"
            primary_live = status in ("available", "failed")

            now_rect = QRectF(btn_x, btn_y_top, btn_w, btn_h)
            now_hover = getattr(self, "hover_update_now", False) and primary_live
            if primary_live:
                self.update_now_rect = QRect(int(btn_x), int(btn_y_top), int(btn_w), int(btn_h))
                now_bg = QColor(accent_color).lighter(118 if now_hover else 108)
                now_bg.setAlphaF(opacity)
                painter.setBrush(QBrush(now_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(now_rect, 8.0, 8.0)
                now_text_col = QColor("#FFFFFF")
            else:
                self.update_now_rect = QRect()
                now_bg = QColor(accent_color)
                now_bg.setAlpha(int((26 if now_hover else 18) * opacity))
                now_border = QColor(accent_color)
                now_border.setAlpha(int((50 if now_hover else 36) * opacity))
                painter.setBrush(QBrush(now_bg))
                painter.setPen(QPen(now_border, 1.0))
                painter.drawRoundedRect(now_rect, 8.0, 8.0)
                now_text_col = QColor(theme.ACCENT_COLOR)
            now_text_col.setAlphaF(opacity * (0.75 if not primary_live else 1.0))
            painter.setFont(QFont(font_family, 9, QFont.Weight.Bold))
            painter.drawText(now_rect, Qt.AlignmentFlag.AlignCenter, primary_label)

            later_rect = QRectF(btn_x, btn_y_top + btn_h + btn_gap, btn_w, btn_h)
            self.update_later_rect = QRect(int(btn_x), int(btn_y_top + btn_h + btn_gap), int(btn_w), int(btn_h))
            later_hover = getattr(self, "hover_update_later", False)
            later_bg = QColor("#FFFFFF")
            later_bg.setAlpha(int((44 if later_hover else 22) * opacity))
            later_border = QColor("#FFFFFF")
            later_border.setAlpha(int((80 if later_hover else 46) * opacity))
            painter.setBrush(QBrush(later_bg))
            painter.setPen(QPen(later_border, 1.0))
            painter.drawRoundedRect(later_rect, 8.0, 8.0)
            later_text_col = QColor("#FFFFFF")
            later_text_col.setAlphaF(opacity * (1.0 if later_hover else 0.8))
            painter.setFont(QFont(font_family, 9, QFont.Weight.DemiBold))
            painter.drawText(later_rect, Qt.AlignmentFlag.AlignCenter, secondary_label)

            # Clear normal mode rects
            self.time_box_rect = QRect()
            self.task_card_rect = QRect()
            self.task_cb_rect = QRect()
            self.task_play_rect = QRect()
            self.add_btn_rect = QRect()
            self.sub_task_rect = QRect()
            self.sub_note_rect = QRect()
            self.sub_reminder_rect = QRect()
            self.add_toggle_rect = QRect()
            return

        # -------------------------------------------------------------
        # TIMER MODE IN NOTCH
        # -------------------------------------------------------------
        if self.timer_in_notch:
            creating_reminder = getattr(self, "is_creating_reminder", False) and getattr(self, "reminders_in_notch", False)
            show_time_box = (not self.timer_is_running) or self.timer_time_peek_active
            if creating_reminder:
                # Clock time must not interfere while the reminder creator is open
                show_time_box = False
            time_draw_w = time_box_w if show_time_box else 0.0

            timer_time_str = self.get_formatted_timer_time()
            painter.setFont(font_time)
            fm_timer = painter.fontMetrics()
            w_timer_text = float(fm_timer.horizontalAdvance(timer_time_str))

            if self.timer_task_title:
                display_task = self.timer_task_title
                painter.setFont(font_task)
                fm_task = painter.fontMetrics()
                max_task_text_w = 180.0
                elided_task = fm_task.elidedText(display_task, Qt.TextElideMode.ElideRight, int(max_task_text_w))
                w_task_text = float(fm_task.horizontalAdvance(elided_task))

                cb_size = 18.0
                cb_gap = 10.0
                play_size = 20.0
                restart_size = 18.0
                card_pad_h = 14.0

                card_w = card_pad_h + cb_size + cb_gap + w_task_text + 10.0 + w_timer_text + 8.0 + restart_size + 8.0 + play_size + card_pad_h
            else:
                play_size = 20.0
                restart_size = 18.0
                card_pad_h = 14.0
                card_w = 12.0 + play_size + 8.0 + restart_size + 10.0 + w_timer_text + card_pad_h

            card_h = 36.0
            add_w = 0.0 if creating_reminder else (capsule_w if self.add_expanded else add_btn_size)
            total_content_w = (time_draw_w + gap_elements if show_time_box else 0.0) + card_w + gap_elements + add_w
            media_block_w = self.media_block_width() if media_shares_row else 0.0
            row_w = total_content_w
            if media_shares_row:
                row_w += self.MEDIA_TIMER_GAP + media_block_w
            if creating_reminder:
                start_x = margin_x
            else:
                start_x = max(margin_x, (w - row_w) / 2.0)
            if media_shares_row:
                self._media_row_left_x = start_x + total_content_w + self.MEDIA_TIMER_GAP

            # Draw Time + Date Box (if peek is active or timer is paused)
            if show_time_box:
                time_box_x = start_x
                time_box_y = top_cy - (time_box_h / 2.0)
                time_box_rect = QRectF(time_box_x, time_box_y, time_box_w, time_box_h)
                self.time_box_rect = QRect(int(time_box_x), int(time_box_y), int(time_box_w), int(time_box_h))

                if show_box:
                    bg = QColor(theme.SEC_CARD_COLOR)
                    bg.setAlpha(int(152 * opacity))
                    border = QColor(255, 255, 255, int(24 * opacity))
                    painter.setBrush(bg)
                    painter.setPen(QPen(border, 1.0))
                    painter.drawRoundedRect(time_box_rect, 10.0, 10.0)

                inner_time_x = (time_box_x + 10.0) if show_box else time_box_x
                time_text_y = time_box_y + 16.0 if show_date else (top_cy + fm_time.capHeight() / 2.0)

                painter.setFont(font_time)
                time_col = self.clock_time_color(accent_color, opacity, spec)
                painter.setPen(time_col)
                painter.drawText(QPointF(inner_time_x, time_text_y), time_str)

                if show_date:
                    painter.setFont(font_date)
                    date_col = QColor(theme.TEXT_SECONDARY)
                    date_col.setAlphaF(opacity)
                    painter.setPen(date_col)
                    date_text_y = time_box_y + 28.0
                    painter.drawText(QPointF(inner_time_x, date_text_y), full_date)

                next_x = time_box_x + time_box_w + gap_elements
            else:
                self.time_box_rect = QRect()
                next_x = start_x

            # Draw Timer Card
            card_x = next_x
            card_y = top_cy - (card_h / 2.0)
            card_rect = QRectF(card_x, card_y, card_w, card_h)
            self.timer_card_rect = QRect(int(card_x), int(card_y), int(card_w), int(card_h))
            if creating_reminder:
                self.reminder_title_area_x = int(card_x + card_w + gap_elements)

            card_bg = QColor(theme.MAIN_CARD_COLOR)
            card_bg.setAlpha(int(165 * opacity))
            card_border = QColor(theme.BORDER_COLOR)
            card_border.setAlphaF(opacity)
            painter.setBrush(QBrush(card_bg))
            painter.setPen(QPen(card_border, 1.0))
            painter.drawRoundedRect(card_rect, 10.0, 10.0)

            if self.timer_task_title:
                task_color = QColor(get_task_color(self.timer_task_title))

                # Tint border with task_color
                b_base = QColor(theme.BORDER_COLOR)
                r = b_base.red() + int((task_color.red() - b_base.red()) * 0.35)
                g = b_base.green() + int((task_color.green() - b_base.green()) * 0.35)
                b = b_base.blue() + int((task_color.blue() - b_base.blue()) * 0.35)
                card_border = QColor(r, g, b, int(72 * opacity))
                painter.setPen(QPen(card_border, 1.0))
                painter.setBrush(QBrush(card_bg))
                painter.drawRoundedRect(card_rect, 10.0, 10.0)

                # Checkbox [ ]
                cb_x = card_x + 14.0
                cb_y = top_cy - (cb_size / 2.0)
                cb_rect = QRectF(cb_x, cb_y, cb_size, cb_size)
                self.task_cb_rect = QRect(int(cb_x - 3), int(cb_y - 3), int(cb_size + 6), int(cb_size + 6))

                if self.task_completed_anim:
                    c_fill = QColor(task_color)
                    c_fill.setAlphaF(opacity)
                    painter.setBrush(QBrush(c_fill))
                    painter.setPen(QPen(c_fill, 1.5))
                    painter.drawRoundedRect(cb_rect, 4.0, 4.0)
                    chk_pen = QColor(255, 255, 255)
                    chk_pen.setAlphaF(opacity)
                    painter.setPen(QPen(chk_pen, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    chk = QPainterPath()
                    chk.moveTo(cb_x + 4.2, cb_y + 9.0)
                    chk.lineTo(cb_x + 7.5, cb_y + 13.0)
                    chk.lineTo(cb_x + 13.8, cb_y + 5.2)
                    painter.drawPath(chk)
                else:
                    cb_fill_alpha = int((55 if self.hover_cb else 38) * opacity)
                    cb_fill = QColor(task_color.red(), task_color.green(), task_color.blue(), cb_fill_alpha)
                    cb_border = QColor(task_color)
                    cb_border.setAlphaF(opacity)
                    painter.setBrush(QBrush(cb_fill))
                    painter.setPen(QPen(cb_border, 1.5 if self.hover_cb else 1.3))
                    painter.drawRoundedRect(cb_rect, 4.0, 4.0)

                # Task title text in task_color
                painter.setFont(font_task)
                text_x = cb_x + cb_size + cb_gap
                text_y = top_cy + (fm_task.capHeight() / 2.0)
                t_col = QColor(task_color)
                t_col.setAlphaF(opacity)
                painter.setPen(t_col)
                painter.drawText(QPointF(text_x, text_y), elided_task)

                # Timer display (HH:MM:SS)
                timer_x = text_x + w_task_text + 10.0
                painter.setFont(font_time)
                timer_col = accent_color if self.timer_is_running else QColor(theme.TEXT_PRIMARY)
                timer_col.setAlphaF(opacity)
                painter.setPen(timer_col)
                timer_y = top_cy + (fm_timer.capHeight() / 2.0)
                painter.drawText(QPointF(timer_x, timer_y), timer_time_str)
                self.timer_display_rect = QRect(int(timer_x), int(card_y), int(w_timer_text), int(card_h))

                # Restart Button [↺]
                restart_x = timer_x + w_timer_text + 8.0
                restart_y = top_cy - (restart_size / 2.0)
                restart_rect = QRectF(restart_x, restart_y, restart_size, restart_size)
                self.timer_restart_rect = QRect(int(restart_x - 3), int(restart_y - 3), int(restart_size + 6), int(restart_size + 6))
                r_col = accent_color if self.timer_hover_restart else QColor(theme.TEXT_SECONDARY)
                colored_restart = RESTART_SVG.replace("COLOR_PLACEHOLDER", r_col.name())
                renderer_restart = QSvgRenderer(QByteArray(colored_restart.encode("utf-8")))
                renderer_restart.render(painter, restart_rect)

                # Stop / Play Button [⏹ / ▶]
                play_x = restart_x + restart_size + 8.0
                play_y = top_cy - (play_size / 2.0)
                play_rect = QRectF(play_x, play_y, play_size, play_size)
                self.timer_play_rect = QRect(int(play_x - 3), int(play_y - 3), int(play_size + 6), int(play_size + 6))

                if self.timer_is_running:
                    p_col = QColor("#FF6961") if self.timer_hover_play else QColor("#FF453A")
                    colored_play = TOOLBAR_STOP_SVG.replace("COLOR_PLACEHOLDER", p_col.name())
                else:
                    p_col = accent_color if self.timer_hover_play else QColor(theme.TEXT_PRIMARY)
                    colored_play = PLAY_SVG.replace("COLOR_PLACEHOLDER", p_col.name())
                renderer_play = QSvgRenderer(QByteArray(colored_play.encode("utf-8")))
                renderer_play.render(painter, play_rect)

            else:
                # Standalone Timer Card: [▶/⏹] [↺] HH:MM:SS
                play_x = card_x + 12.0
                play_y = top_cy - (play_size / 2.0)
                play_rect = QRectF(play_x, play_y, play_size, play_size)
                self.timer_play_rect = QRect(int(play_x - 3), int(play_y - 3), int(play_size + 6), int(play_size + 6))

                if self.timer_is_running:
                    p_col = QColor("#FF6961") if self.timer_hover_play else QColor("#FF453A")
                    colored_play = TOOLBAR_STOP_SVG.replace("COLOR_PLACEHOLDER", p_col.name())
                else:
                    p_col = accent_color if self.timer_hover_play else QColor(theme.TEXT_PRIMARY)
                    colored_play = PLAY_SVG.replace("COLOR_PLACEHOLDER", p_col.name())
                renderer_play = QSvgRenderer(QByteArray(colored_play.encode("utf-8")))
                renderer_play.render(painter, play_rect)

                # Restart Button [↺]
                restart_x = play_x + play_size + 8.0
                restart_y = top_cy - (restart_size / 2.0)
                restart_rect = QRectF(restart_x, restart_y, restart_size, restart_size)
                self.timer_restart_rect = QRect(int(restart_x - 3), int(restart_y - 3), int(restart_size + 6), int(restart_size + 6))
                r_col = accent_color if self.timer_hover_restart else QColor(theme.TEXT_SECONDARY)
                colored_restart = RESTART_SVG.replace("COLOR_PLACEHOLDER", r_col.name())
                renderer_restart = QSvgRenderer(QByteArray(colored_restart.encode("utf-8")))
                renderer_restart.render(painter, restart_rect)

                # Timer display (HH:MM:SS)
                timer_x = restart_x + restart_size + 10.0
                painter.setFont(font_time)
                timer_col = accent_color if self.timer_is_running else QColor(theme.TEXT_PRIMARY)
                timer_col.setAlphaF(opacity)
                painter.setPen(timer_col)
                timer_y = top_cy + (fm_timer.capHeight() / 2.0)
                painter.drawText(QPointF(timer_x, timer_y), timer_time_str)
                self.timer_display_rect = QRect(int(timer_x), int(card_y), int(w_timer_text), int(card_h))

            if creating_reminder:
                # Reminder creation takes over: timer card sits left, title input
                # on the right (child widget), no add button / capsule / clock box
                self.add_btn_rect = QRect()
                self.add_toggle_rect = QRect()
                self.sub_task_rect = QRect()
                self.sub_note_rect = QRect()
                self.sub_reminder_rect = QRect()
                return

            # Add Button / Capsule placement directly following the timer card
            add_start_x = card_x + card_w + gap_elements

            if not self.add_expanded:
                self.sub_task_rect = QRect()
                self.sub_note_rect = QRect()
                self.add_toggle_rect = QRect()

                add_btn_y = top_cy - (add_btn_size / 2.0)
                add_btn_rect = QRectF(add_start_x, add_btn_y, add_btn_size, add_btn_size)
                self.add_btn_rect = QRect(int(add_start_x - 2), int(add_btn_y - 2), int(add_btn_size + 4), int(add_btn_size + 4))

                add_bg = QColor(accent_color)
                if self.hover_add_btn:
                    add_bg = add_bg.lighter(115)
                add_bg.setAlphaF(opacity)

                painter.setBrush(QBrush(add_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(add_btn_rect)

                plus_pen = QColor(255, 255, 255)
                plus_pen.setAlphaF(opacity)
                painter.setPen(QPen(plus_pen, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                ac_x = add_start_x + add_btn_size / 2.0
                ac_y = add_btn_y + add_btn_size / 2.0
                p_len = 5.0
                painter.drawLine(QPointF(ac_x - p_len, ac_y), QPointF(ac_x + p_len, ac_y))
                painter.drawLine(QPointF(ac_x, ac_y - p_len), QPointF(ac_x, ac_y + p_len))
            else:
                self.add_btn_rect = QRect()
                capsule_x = add_start_x
                capsule_y = top_cy - 16.0
                capsule_rect = QRectF(capsule_x, capsule_y, capsule_w, 32.0)

                cap_bg = QColor(theme.SEC_CARD_COLOR)
                cap_bg.setAlpha(int(152 * opacity))
                cap_border = QColor(theme.BORDER_COLOR)
                if not cap_border.isValid():
                    cap_border = QColor(255, 255, 255, int(24 * opacity))
                else:
                    cap_border.setAlpha(int(max(24, cap_border.alpha()) * opacity))
                painter.setBrush(QBrush(cap_bg))
                painter.setPen(QPen(cap_border, 1.0))
                painter.drawRoundedRect(capsule_rect, 16.0, 16.0)

                font_sub = QFont()
                font_sub.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
                font_sub.setPointSize(10)
                font_sub.setWeight(QFont.Weight.Bold)
                painter.setFont(font_sub)

                task_btn_rect = QRectF(capsule_x + 3.0, top_cy - 14.0, 40.0, 28.0)
                self.sub_task_rect = QRect(int(task_btn_rect.x()), int(task_btn_rect.y()), int(task_btn_rect.width()), int(task_btn_rect.height()))

                if self.is_creating_task or self.hover_sub_task:
                    h_bg = QColor(theme.HOVER_COLOR)
                    h_bg.setAlphaF(opacity)
                    painter.setBrush(QBrush(h_bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(task_btn_rect, 14.0, 14.0)
                    t_col = QColor(accent_color)
                else:
                    t_col = QColor(theme.TEXT_SECONDARY)
                t_col.setAlphaF(opacity)
                painter.setPen(t_col)
                painter.drawText(task_btn_rect, Qt.AlignmentFlag.AlignCenter, "Task")

                note_btn_rect = QRectF(capsule_x + 45.0, top_cy - 14.0, 40.0, 28.0)
                self.sub_note_rect = QRect(int(note_btn_rect.x()), int(note_btn_rect.y()), int(note_btn_rect.width()), int(note_btn_rect.height()))

                if self.hover_sub_note:
                    h_bg = QColor(theme.HOVER_COLOR)
                    h_bg.setAlphaF(opacity)
                    painter.setBrush(QBrush(h_bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(note_btn_rect, 6.0, 6.0)
                    t_col = QColor(accent_color)
                else:
                    t_col = QColor(theme.TEXT_SECONDARY)
                t_col.setAlphaF(opacity)
                painter.setPen(t_col)
                painter.drawText(note_btn_rect, Qt.AlignmentFlag.AlignCenter, "Note")

                reminder_btn_rect = QRectF(capsule_x + 87.0, top_cy - 14.0, 64.0, 28.0)
                self.sub_reminder_rect = QRect(int(reminder_btn_rect.x()), int(reminder_btn_rect.y()), int(reminder_btn_rect.width()), int(reminder_btn_rect.height()))

                if self.hover_sub_reminder:
                    h_bg = QColor(theme.HOVER_COLOR)
                    h_bg.setAlphaF(opacity)
                    painter.setBrush(QBrush(h_bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(reminder_btn_rect, 6.0, 6.0)
                    t_col = QColor(accent_color)
                else:
                    t_col = QColor(theme.TEXT_SECONDARY)
                t_col.setAlphaF(opacity)
                painter.setPen(t_col)
                painter.drawText(reminder_btn_rect, Qt.AlignmentFlag.AlignCenter, "Reminder")

                toggle_x = capsule_x + 153.0
                toggle_y = top_cy - 14.0
                toggle_size = 28.0
                toggle_rect = QRectF(toggle_x, toggle_y, toggle_size, toggle_size)
                self.add_toggle_rect = QRect(int(toggle_x), int(toggle_y), int(toggle_size), int(toggle_size))

                tog_bg = QColor(accent_color)
                if self.hover_add_btn:
                    tog_bg = tog_bg.lighter(115)
                tog_bg.setAlphaF(opacity)
                painter.setBrush(QBrush(tog_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(toggle_rect)

                angle = self._add_expand_progress * 135.0
                painter.save()
                painter.translate(toggle_rect.center())
                painter.rotate(angle)
                plus_pen = QColor(255, 255, 255)
                plus_pen.setAlphaF(opacity)
                painter.setPen(QPen(plus_pen, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(-5.0, 0.0), QPointF(5.0, 0.0))
                painter.drawLine(QPointF(0.0, -5.0), QPointF(0.0, 5.0))
                painter.restore()

        # -------------------------------------------------------------
        # NORMAL MODE (Non-Timer)
        # -------------------------------------------------------------
        else:
            if getattr(self, "reminders_in_notch", False) and getattr(self, "is_creating_reminder", False):
                time_box_x = margin_x
                time_box_y = top_cy - (time_box_h / 2.0)
                time_box_rect = QRectF(time_box_x, time_box_y, time_box_w, time_box_h)
                self.time_box_rect = QRect(int(time_box_x), int(time_box_y), int(time_box_w), int(time_box_h))

                if show_box:
                    bg = QColor(theme.SEC_CARD_COLOR)
                    bg.setAlpha(int(152 * opacity))
                    border = QColor(theme.BORDER_COLOR)
                    if not border.isValid():
                        border = QColor(255, 255, 255, int(24 * opacity))
                    else:
                        border.setAlpha(int(max(24, border.alpha()) * opacity))
                    painter.setBrush(bg)
                    painter.setPen(QPen(border, 1.0))
                    painter.drawRoundedRect(time_box_rect, 10.0, 10.0)

                inner_time_x = (time_box_x + 10.0) if show_box else time_box_x
                time_text_y = time_box_y + 16.0 if show_date else (top_cy + fm_time.capHeight() / 2.0)

                painter.setFont(font_time)
                time_col = self.clock_time_color(accent_color, opacity, spec)
                painter.setPen(time_col)
                painter.drawText(QPointF(inner_time_x, time_text_y), time_str)

                if show_date:
                    painter.setFont(font_date)
                    date_col = QColor(theme.TEXT_SECONDARY)
                    date_col.setAlphaF(opacity)
                    painter.setPen(date_col)
                    date_text_y = time_box_y + 28.0
                    painter.drawText(QPointF(inner_time_x, date_text_y), full_date)

                self.task_card_rect = QRect()
                self.task_cb_rect = QRect()
                self.task_play_rect = QRect()
                self.add_btn_rect = QRect()
                self.sub_task_rect = QRect()
                self.sub_note_rect = QRect()
                self.add_toggle_rect = QRect()
                return

            if self.is_creating_note:
                # -------------------------------------------------------------
                # Notepad Header (Action buttons above text)
                # -------------------------------------------------------------
                time_box_x = margin_x
                time_box_y = top_cy - (time_box_h / 2.0)
                time_box_rect = QRectF(time_box_x, time_box_y, time_box_w, time_box_h)
                self.time_box_rect = QRect(int(time_box_x), int(time_box_y), int(time_box_w), int(time_box_h))

                if show_box:
                    bg = QColor(theme.SEC_CARD_COLOR)
                    bg.setAlpha(int(152 * opacity))
                    border = QColor(theme.BORDER_COLOR)
                    if not border.isValid():
                        border = QColor(255, 255, 255, int(24 * opacity))
                    else:
                        border.setAlpha(int(max(24, border.alpha()) * opacity))
                    painter.setBrush(bg)
                    painter.setPen(QPen(border, 1.0))
                    painter.drawRoundedRect(time_box_rect, 10.0, 10.0)

                inner_time_x = (time_box_x + 10.0) if show_box else time_box_x
                time_text_y = time_box_y + 16.0 if show_date else (top_cy + fm_time.capHeight() / 2.0)

                painter.setFont(font_time)
                time_col = self.clock_time_color(accent_color, opacity, spec)
                painter.setPen(time_col)
                painter.drawText(QPointF(inner_time_x, time_text_y), time_str)

                if show_date:
                    painter.setFont(font_date)
                    date_col = QColor(theme.TEXT_SECONDARY)
                    date_col.setAlphaF(opacity)
                    painter.setPen(date_col)
                    date_text_y = time_box_y + 28.0
                    painter.drawText(QPointF(inner_time_x, date_text_y), full_date)

                # Clear unrelated interactive rects
                self.task_card_rect = QRect()
                self.task_cb_rect = QRect()
                self.task_play_rect = QRect()
                self.add_btn_rect = QRect()
                self.sub_task_rect = QRect()
                self.sub_note_rect = QRect()
                self.add_toggle_rect = QRect()

                # Action pill placed above the text card (right aligned to the note card)
                is_editing = (getattr(self, "editing_note_index", None) is not None)
                pill_w = 108.0 if is_editing else 72.0
                pill_h = 28.0
                pill_x = w - margin_x - pill_w
                pill_y = top_cy - (pill_h / 2.0)
                pill_rect = QRectF(pill_x, pill_y, pill_w, pill_h)

                pill_bg = QColor(theme.SEC_CARD_COLOR)
                pill_bg.setAlpha(int(190 * opacity))
                pill_border = QColor(theme.BORDER_COLOR)
                if not pill_border.isValid():
                    pill_border = QColor(255, 255, 255, int(30 * opacity))
                else:
                    pill_border.setAlpha(int(max(30, pill_border.alpha()) * opacity))
                painter.setBrush(QBrush(pill_bg))
                painter.setPen(QPen(pill_border, 1.0))
                painter.drawRoundedRect(pill_rect, 14.0, 14.0)

                clip_pill = QPainterPath()
                clip_pill.addRoundedRect(pill_rect, 14.0, 14.0)

                if is_editing:
                    # 3-segment pill: [ ✓ | ✕ | 🗑 ] (Save, Cancel, Delete)
                    btn_w = pill_w / 3.0

                    # 1. Tick button [✓] (Save)
                    tick_rect = QRectF(pill_x, pill_y, btn_w, pill_h)
                    self.note_tick_rect = QRect(int(tick_rect.x()), int(tick_rect.y()), int(tick_rect.width()), int(tick_rect.height()))

                    if self.hover_note_tick:
                        painter.save()
                        painter.setClipPath(clip_pill)
                        painter.setBrush(QBrush(QColor(48, 209, 88, int(55 * opacity))))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRect(tick_rect)
                        painter.restore()
                        t_col = QColor("#30D158")
                    else:
                        t_col = QColor(theme.TEXT_SECONDARY)

                    t_svg = TICK_SVG.replace("COLOR_PLACEHOLDER", t_col.name())
                    r_tick = QSvgRenderer(QByteArray(t_svg.encode("utf-8")))
                    tick_icon_rect = QRectF(pill_x + (btn_w / 2.0) - 7.0, pill_y + (pill_h / 2.0) - 7.0, 14.0, 14.0)
                    r_tick.render(painter, tick_icon_rect)

                    # Separator 1
                    sep1_x = pill_x + btn_w
                    painter.setPen(QPen(QColor(255, 255, 255, int(35 * opacity)), 1.0))
                    painter.drawLine(QPointF(sep1_x, pill_y + 4.0), QPointF(sep1_x, pill_y + pill_h - 4.0))

                    # 2. Cross button [✕] (Cancel)
                    cross_rect = QRectF(pill_x + btn_w, pill_y, btn_w, pill_h)
                    self.note_cross_rect = QRect(int(cross_rect.x()), int(cross_rect.y()), int(cross_rect.width()), int(cross_rect.height()))

                    if self.hover_note_cross:
                        painter.save()
                        painter.setClipPath(clip_pill)
                        painter.setBrush(QBrush(QColor(255, 255, 255, int(25 * opacity))))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRect(cross_rect)
                        painter.restore()
                        c_col = QColor("#FFFFFF")
                    else:
                        c_col = QColor(theme.TEXT_SECONDARY)

                    c_svg = CROSS_SVG.replace("COLOR_PLACEHOLDER", c_col.name())
                    r_cross = QSvgRenderer(QByteArray(c_svg.encode("utf-8")))
                    cross_icon_rect = QRectF(pill_x + btn_w + (btn_w / 2.0) - 7.0, pill_y + (pill_h / 2.0) - 7.0, 14.0, 14.0)
                    r_cross.render(painter, cross_icon_rect)

                    # Separator 2
                    sep2_x = pill_x + (btn_w * 2.0)
                    painter.setPen(QPen(QColor(255, 255, 255, int(35 * opacity)), 1.0))
                    painter.drawLine(QPointF(sep2_x, pill_y + 4.0), QPointF(sep2_x, pill_y + pill_h - 4.0))

                    # 3. Delete button [🗑] (Delete)
                    del_rect = QRectF(pill_x + (btn_w * 2.0), pill_y, btn_w, pill_h)
                    self.note_delete_rect = QRect(int(del_rect.x()), int(del_rect.y()), int(del_rect.width()), int(del_rect.height()))

                    if self.hover_note_delete:
                        painter.save()
                        painter.setClipPath(clip_pill)
                        painter.setBrush(QBrush(QColor(255, 69, 58, int(55 * opacity))))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRect(del_rect)
                        painter.restore()
                        d_col = QColor("#FF453A")
                    else:
                        d_col = QColor(theme.TEXT_SECONDARY)

                    d_svg = NOTE_DELETE_SVG.replace("COLOR_PLACEHOLDER", d_col.name())
                    r_del = QSvgRenderer(QByteArray(d_svg.encode("utf-8")))
                    del_icon_rect = QRectF(pill_x + (btn_w * 2.0) + (btn_w / 2.0) - 7.0, pill_y + (pill_h / 2.0) - 7.0, 14.0, 14.0)
                    r_del.render(painter, del_icon_rect)
                else:
                    self.note_delete_rect = QRect()
                    btn_w = pill_w / 2.0

                    # 1. Tick button [✓] (Save)
                    tick_rect = QRectF(pill_x, pill_y, btn_w, pill_h)
                    self.note_tick_rect = QRect(int(tick_rect.x()), int(tick_rect.y()), int(tick_rect.width()), int(tick_rect.height()))

                    if self.hover_note_tick:
                        painter.save()
                        painter.setClipPath(clip_pill)
                        painter.setBrush(QBrush(QColor(48, 209, 88, int(55 * opacity))))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRect(tick_rect)
                        painter.restore()
                        t_col = QColor("#30D158")
                    else:
                        t_col = QColor(theme.TEXT_SECONDARY)

                    t_svg = TICK_SVG.replace("COLOR_PLACEHOLDER", t_col.name())
                    r_tick = QSvgRenderer(QByteArray(t_svg.encode("utf-8")))
                    tick_icon_rect = QRectF(pill_x + (btn_w / 2.0) - 7.0, pill_y + (pill_h / 2.0) - 7.0, 14.0, 14.0)
                    r_tick.render(painter, tick_icon_rect)

                    # Center separator line
                    sep_x = pill_x + btn_w
                    painter.setPen(QPen(QColor(255, 255, 255, int(35 * opacity)), 1.0))
                    painter.drawLine(QPointF(sep_x, pill_y + 4.0), QPointF(sep_x, pill_y + pill_h - 4.0))

                    # 2. Cross button [✕] (Cancel)
                    cross_rect = QRectF(pill_x + btn_w, pill_y, btn_w, pill_h)
                    self.note_cross_rect = QRect(int(cross_rect.x()), int(cross_rect.y()), int(cross_rect.width()), int(cross_rect.height()))

                    if self.hover_note_cross:
                        painter.save()
                        painter.setClipPath(clip_pill)
                        painter.setBrush(QBrush(QColor(255, 69, 58, int(55 * opacity))))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRect(cross_rect)
                        painter.restore()
                        c_col = QColor("#FF453A")
                    else:
                        c_col = QColor(theme.TEXT_SECONDARY)

                    c_svg = CROSS_SVG.replace("COLOR_PLACEHOLDER", c_col.name())
                    r_cross = QSvgRenderer(QByteArray(c_svg.encode("utf-8")))
                    cross_icon_rect = QRectF(pill_x + btn_w + (btn_w / 2.0) - 7.0, pill_y + (pill_h / 2.0) - 7.0, 14.0, 14.0)
                    r_cross.render(painter, cross_icon_rect)
                return

            has_task = bool(self.current_random_task)
            if has_task:
                display_task = self.current_random_task
                painter.setFont(font_task)
                fm_task = painter.fontMetrics()
                max_task_text_w = 220.0
                elided_task = fm_task.elidedText(display_task, Qt.TextElideMode.ElideRight, int(max_task_text_w))
                w_task_text = float(fm_task.horizontalAdvance(elided_task))

                cb_size = 18.0
                cb_gap = 10.0
                play_size = 20.0
                play_gap = 10.0
                card_pad_h = 14.0

                task_card_w = card_pad_h + cb_size + cb_gap + w_task_text + play_gap + play_size + card_pad_h
                task_card_h = 36.0
                total_content_w_normal = time_box_w + gap_elements + task_card_w + gap_elements + add_btn_size
            else:
                task_card_w = 0.0
                task_card_h = 36.0
                total_content_w_normal = time_box_w + gap_elements + add_btn_size

            total_content_w_add = time_box_w + 14.0 + capsule_w
            p = self._add_expand_progress
            curr_total_content_w = (1.0 - p) * total_content_w_normal + p * total_content_w_add

            start_x = max(margin_x, (w - curr_total_content_w) / 2.0)

            # -------------------------------------------------------------
            # 1. Time + Date Block
            # -------------------------------------------------------------
            time_box_x = start_x
            time_box_y = top_cy - (time_box_h / 2.0)
            time_box_rect = QRectF(time_box_x, time_box_y, time_box_w, time_box_h)
            self.time_box_rect = QRect(int(time_box_x), int(time_box_y), int(time_box_w), int(time_box_h))

            if show_box:
                bg = QColor(theme.SEC_CARD_COLOR)
                bg.setAlpha(int(152 * opacity))
                border = QColor(theme.BORDER_COLOR)
                if not border.isValid():
                    border = QColor(255, 255, 255, int(24 * opacity))
                else:
                    border.setAlpha(int(max(24, border.alpha()) * opacity))
                painter.setBrush(bg)
                painter.setPen(QPen(border, 1.0))
                painter.drawRoundedRect(time_box_rect, 10.0, 10.0)

            inner_time_x = (time_box_x + 10.0) if show_box else time_box_x
            time_text_y = time_box_y + 16.0 if show_date else (top_cy + fm_time.capHeight() / 2.0)

            painter.setFont(font_time)
            time_col = self.clock_time_color(accent_color, opacity, spec)
            painter.setPen(time_col)
            painter.drawText(QPointF(inner_time_x, time_text_y), time_str)

            if show_date:
                painter.setFont(font_date)
                date_col = QColor(theme.TEXT_SECONDARY)
                date_col.setAlphaF(opacity)
                painter.setPen(date_col)
                date_text_y = time_box_y + 28.0
                painter.drawText(QPointF(inner_time_x, date_text_y), full_date)

            # -------------------------------------------------------------
            # 2. Normal Mode: Task Card + Circular Add Button (fading out when expanding add)
            # -------------------------------------------------------------
            if p < 0.99:
                norm_opacity = opacity * max(0.0, 1.0 - p * 1.5)

                if has_task:
                    # Task Card
                    task_card_x = time_box_x + time_box_w + gap_elements
                    task_card_y = top_cy - (task_card_h / 2.0)
                    task_card_rect = QRectF(task_card_x, task_card_y, task_card_w, task_card_h)
                    if not self.add_expanded:
                        self.task_card_rect = QRect(int(task_card_x), int(task_card_y), int(task_card_w), int(task_card_h))

                    task_color = QColor(get_task_color(display_task))

                    # Card container background & border (with attention-grabbing task color effect)
                    card_bg = QColor(theme.MAIN_CARD_COLOR)
                    card_bg.setAlpha(int((185 if self.hover_card else 145) * norm_opacity))

                    b_base = QColor(theme.BORDER_COLOR)
                    blend_factor = 0.50 if self.hover_card else 0.35
                    r = b_base.red() + int((task_color.red() - b_base.red()) * blend_factor)
                    g = b_base.green() + int((task_color.green() - b_base.green()) * blend_factor)
                    b = b_base.blue() + int((task_color.blue() - b_base.blue()) * blend_factor)
                    card_border = QColor(r, g, b, int((95 if self.hover_card else 72) * norm_opacity))

                    painter.setBrush(QBrush(card_bg))
                    painter.setPen(QPen(card_border, 1.0))
                    painter.drawRoundedRect(task_card_rect, 10.0, 10.0)

                    # Checkbox [ ] inside card
                    cb_x = task_card_x + card_pad_h
                    cb_y = top_cy - (cb_size / 2.0)
                    cb_rect = QRectF(cb_x, cb_y, cb_size, cb_size)
                    if not self.add_expanded:
                        self.task_cb_rect = QRect(int(cb_x - 3), int(cb_y - 3), int(cb_size + 6), int(cb_size + 6))

                    if self.task_completed_anim:
                        c_fill = QColor(task_color)
                        c_fill.setAlphaF(norm_opacity)
                        painter.setBrush(QBrush(c_fill))
                        painter.setPen(QPen(c_fill, 1.5))
                        painter.drawRoundedRect(cb_rect, 4.0, 4.0)

                        chk_pen = QColor(255, 255, 255)
                        chk_pen.setAlphaF(norm_opacity)
                        painter.setPen(QPen(chk_pen, 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                        chk = QPainterPath()
                        chk.moveTo(cb_x + 4.2, cb_y + 9.0)
                        chk.lineTo(cb_x + 7.5, cb_y + 13.0)
                        chk.lineTo(cb_x + 13.8, cb_y + 5.2)
                        painter.drawPath(chk)
                    else:
                        cb_fill_alpha = int((55 if (self.hover_cb or self.hover_card) else 38) * norm_opacity)
                        cb_fill = QColor(task_color.red(), task_color.green(), task_color.blue(), cb_fill_alpha)
                        cb_border = QColor(task_color)
                        cb_border.setAlphaF(norm_opacity)
                        painter.setBrush(QBrush(cb_fill))
                        painter.setPen(QPen(cb_border, 1.5 if (self.hover_cb or self.hover_card) else 1.3))
                        painter.drawRoundedRect(cb_rect, 4.0, 4.0)

                    # Task text (in task_color to grab attention!)
                    painter.setFont(font_task)
                    text_x = cb_x + cb_size + cb_gap
                    text_y = top_cy + (fm_task.capHeight() / 2.0)

                    t_col = QColor(task_color)
                    t_col.setAlphaF(norm_opacity)
                    painter.setPen(t_col)
                    painter.drawText(QPointF(text_x, text_y), elided_task)

                    # Start Task (Play / Focus) Button
                    play_x = text_x + w_task_text + play_gap
                    play_y = top_cy - (play_size / 2.0)
                    play_rect = QRectF(play_x, play_y, play_size, play_size)
                    if not self.add_expanded:
                        self.task_play_rect = QRect(int(play_x - 3), int(play_y - 3), int(play_size + 6), int(play_size + 6))

                    if self.is_active_focus:
                        svg_template = STOP_SVG
                        svg_color = QColor("#FF453A") if not self.hover_play else QColor("#FF6961")
                    else:
                        svg_template = FOCUS_SVG
                        svg_color = task_color if self.hover_play else QColor(task_color.red(), task_color.green(), task_color.blue(), 180)

                    colored_svg = svg_template.replace("COLOR_PLACEHOLDER", svg_color.name())
                    renderer = QSvgRenderer(QByteArray(colored_svg.encode("utf-8")))
                    renderer.render(painter, play_rect)

                    add_btn_x = task_card_x + task_card_w + gap_elements
                else:
                    self.task_card_rect = QRect()
                    self.task_cb_rect = QRect()
                    self.task_play_rect = QRect()
                    add_btn_x = time_box_x + time_box_w + gap_elements

                # Circular Add Button (when not expanded)
                add_btn_y = top_cy - (add_btn_size / 2.0)
                add_btn_rect = QRectF(add_btn_x, add_btn_y, add_btn_size, add_btn_size)
                if not self.add_expanded:
                    self.add_btn_rect = QRect(int(add_btn_x - 2), int(add_btn_y - 2), int(add_btn_size + 4), int(add_btn_size + 4))

                add_bg = QColor(accent_color)
                if self.hover_add_btn:
                    add_bg = add_bg.lighter(115)
                add_bg.setAlphaF(norm_opacity)

                painter.setBrush(QBrush(add_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(add_btn_rect)

                # White Plus '+' inside circular button
                plus_pen = QColor(255, 255, 255)
                plus_pen.setAlphaF(norm_opacity)
                painter.setPen(QPen(plus_pen, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                ac_x = add_btn_x + add_btn_size / 2.0
                ac_y = add_btn_y + add_btn_size / 2.0
                p_len = 5.0
                painter.drawLine(QPointF(ac_x - p_len, ac_y), QPointF(ac_x + p_len, ac_y))
                painter.drawLine(QPointF(ac_x, ac_y - p_len), QPointF(ac_x, ac_y + p_len))
            else:
                self.task_card_rect = QRect()
                self.task_cb_rect = QRect()
                self.task_play_rect = QRect()

            # -------------------------------------------------------------
            # 3. Add Expanded Mode: Capsule [Task] [Note] [x]
            # -------------------------------------------------------------
            if p > 0.01:
                add_opacity = opacity * min(1.0, p * 1.5)
                capsule_x = time_box_x + time_box_w + 14.0
                capsule_y = top_cy - 16.0
                capsule_rect = QRectF(capsule_x, capsule_y, capsule_w, 32.0)

                # Capsule glassy background & border
                cap_bg = QColor(theme.SEC_CARD_COLOR)
                cap_bg.setAlpha(int(152 * add_opacity))
                cap_border = QColor(theme.BORDER_COLOR)
                if not cap_border.isValid():
                    cap_border = QColor(255, 255, 255, int(24 * add_opacity))
                else:
                    cap_border.setAlpha(int(max(24, cap_border.alpha()) * add_opacity))
                painter.setBrush(QBrush(cap_bg))
                painter.setPen(QPen(cap_border, 1.0))
                painter.drawRoundedRect(capsule_rect, 16.0, 16.0)

                font_sub = QFont()
                font_sub.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
                font_sub.setPointSize(10)
                font_sub.setWeight(QFont.Weight.Bold)
                painter.setFont(font_sub)

                # [Task] Sub-Button
                task_btn_rect = QRectF(capsule_x + 3.0, top_cy - 14.0, 40.0, 28.0)
                if self.add_expanded:
                    self.sub_task_rect = QRect(int(task_btn_rect.x()), int(task_btn_rect.y()), int(task_btn_rect.width()), int(task_btn_rect.height()))

                if self.is_creating_task or self.hover_sub_task:
                    h_bg = QColor(theme.HOVER_COLOR)
                    h_bg.setAlphaF(add_opacity)
                    painter.setBrush(QBrush(h_bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(task_btn_rect, 14.0, 14.0)
                    t_col = QColor(accent_color)
                else:
                    t_col = QColor(theme.TEXT_SECONDARY)
                t_col.setAlphaF(add_opacity)
                painter.setPen(t_col)
                painter.drawText(task_btn_rect, Qt.AlignmentFlag.AlignCenter, "Task")

                # [Note] Sub-Button
                note_btn_rect = QRectF(capsule_x + 45.0, top_cy - 14.0, 40.0, 28.0)
                if self.add_expanded:
                    self.sub_note_rect = QRect(int(note_btn_rect.x()), int(note_btn_rect.y()), int(note_btn_rect.width()), int(note_btn_rect.height()))

                if self.hover_sub_note:
                    h_bg = QColor(theme.HOVER_COLOR)
                    h_bg.setAlphaF(add_opacity)
                    painter.setBrush(QBrush(h_bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(note_btn_rect, 6.0, 6.0)
                    t_col = QColor(accent_color)
                else:
                    t_col = QColor(theme.TEXT_SECONDARY)
                t_col.setAlphaF(add_opacity)
                painter.setPen(t_col)
                painter.drawText(note_btn_rect, Qt.AlignmentFlag.AlignCenter, "Note")

                # [Reminder] Sub-Button
                reminder_btn_rect = QRectF(capsule_x + 87.0, top_cy - 14.0, 64.0, 28.0)
                if self.add_expanded:
                    self.sub_reminder_rect = QRect(int(reminder_btn_rect.x()), int(reminder_btn_rect.y()), int(reminder_btn_rect.width()), int(reminder_btn_rect.height()))

                if self.hover_sub_reminder:
                    h_bg = QColor(theme.HOVER_COLOR)
                    h_bg.setAlphaF(add_opacity)
                    painter.setBrush(QBrush(h_bg))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRoundedRect(reminder_btn_rect, 6.0, 6.0)
                    t_col = QColor(accent_color)
                else:
                    t_col = QColor(theme.TEXT_SECONDARY)
                t_col.setAlphaF(add_opacity)
                painter.setPen(t_col)
                painter.drawText(reminder_btn_rect, Qt.AlignmentFlag.AlignCenter, "Reminder")

                # Toggle / Close [x] Button (rotates from + to x by 135 deg)
                toggle_x = capsule_x + 153.0
                toggle_y = top_cy - 14.0
                toggle_size = 28.0
                toggle_rect = QRectF(toggle_x, toggle_y, toggle_size, toggle_size)
                if self.add_expanded:
                    self.add_toggle_rect = QRect(int(toggle_x), int(toggle_y), int(toggle_size), int(toggle_size))
                    self.add_btn_rect = self.add_toggle_rect

                tog_bg = QColor(accent_color)
                if self.hover_add_btn:
                    tog_bg = tog_bg.lighter(115)
                tog_bg.setAlphaF(add_opacity)
                painter.setBrush(QBrush(tog_bg))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(toggle_rect)

                angle = p * 135.0
                painter.save()
                painter.translate(toggle_rect.center())
                painter.rotate(angle)
                plus_pen = QColor(255, 255, 255)
                plus_pen.setAlphaF(add_opacity)
                painter.setPen(QPen(plus_pen, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                painter.drawLine(QPointF(-5.0, 0.0), QPointF(5.0, 0.0))
                painter.drawLine(QPointF(0.0, -5.0), QPointF(0.0, 5.0))
                painter.restore()
            else:
                if not self.add_expanded:
                    self.sub_task_rect = QRect()
                    self.sub_note_rect = QRect()
                    self.sub_reminder_rect = QRect()
                    self.add_toggle_rect = QRect()

        # -------------------------------------------------------------
        # 4. Extended Area for Task List / Task Creation / Note Creation / Notes Grid (when h > 58.0)
        # -------------------------------------------------------------
        if h > 58.0:
            if getattr(self, "empty_reminders_showing", False):
                font_fam = config.load_font_family("DM Sans")
                font_empty = QFont(font_fam, 10, QFont.Weight.Medium)
                painter.setFont(font_empty)
                empty_col = QColor(theme.TEXT_SECONDARY)
                empty_col.setAlphaF(opacity)
                painter.setPen(empty_col)
                text_rect = QRectF(0.0, 54.0, w, max(1.0, h - 54.0))
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "No reminders available")
                return

            if self.tasks_in_notch and not self.is_creating_task and not self.is_creating_note:
                all_tasks = self._get_tasks_list()
                ext_top = self.TASK_EXT_TOP
                task_item_h = self.TASK_ITEM_H
                target_ext_h = self._calc_tasks_notch_height(all_tasks)
                ext_progress = min(1.0, max(0.0, (h - 54.0) / max(1.0, target_ext_h - 54.0)))
                ext_opacity = opacity * ext_progress

                self.notch_task_rects = []
                self.notch_task_cb_rects = []
                self.notch_task_play_rects = []

                task_list_margin = 18.0
                task_list_w = w - (task_list_margin * 2.0)
                play_btn_size = 18.0
                play_btn_margin = 10.0   # gap between text and play btn, and btn to card edge

                if not all_tasks:
                    painter.setFont(QFont(font_family, 9, QFont.Weight.Medium))
                    empty_col = QColor(theme.TEXT_SECONDARY)
                    empty_col.setAlphaF(ext_opacity)
                    painter.setPen(empty_col)
                    painter.drawText(
                        QRectF(0.0, ext_top, w, max(1.0, h - ext_top)),
                        Qt.AlignmentFlag.AlignCenter, "No tasks"
                    )
                else:
                    viewport_h = self._tasks_viewport_height()
                    max_scroll = self._tasks_max_scroll(all_tasks)
                    self.notch_task_scroll = max(0.0, min(max_scroll, self.notch_task_scroll))
                    row_top = self.TASK_ROW_TOP
                    band = QRectF(0.0, row_top, w, viewport_h)
                    pitch = self._tasks_pitch()

                    font_task_list = QFont()
                    font_task_list.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
                    font_task_list.setPointSize(9)
                    font_task_list.setWeight(QFont.Weight.Medium)
                    fm_task_list = QFontMetrics(font_task_list)

                    painter.save()
                    painter.setClipRect(band)
                    for abs_idx, task_text in enumerate(all_tasks):
                        ty = row_top + abs_idx * pitch - self.notch_task_scroll
                        if ty + task_item_h < row_top or ty > row_top + viewport_h:
                            continue
                        row_rect = QRectF(task_list_margin, ty, task_list_w, task_item_h)
                        row_qrect = QRect(int(task_list_margin), int(ty), int(task_list_w), int(task_item_h))
                        row_qrect = row_qrect.intersected(band.toRect())
                        if row_qrect.height() <= 4:
                            continue
                        self.notch_task_rects.append((row_qrect, abs_idx, task_text))

                        is_row_hovered = (self.hovered_task_idx == abs_idx)
                        is_cb_hovered = (self.hovered_task_cb_idx == abs_idx)
                        is_play_hovered = (self.hovered_task_play_idx == abs_idx)
                        # 0→1 tick-off progress of the row the user just clicked
                        cp = float(self._complete_row_progress) if self.completing_task_text == task_text else 0.0

                        # Row background
                        row_bg = QColor(theme.HOVER_COLOR if is_row_hovered else theme.MAIN_CARD_COLOR)
                        row_bg.setAlpha(int(200 * ext_opacity * (1.0 - 0.55 * cp)))
                        row_border = QColor(theme.ACCENT_COLOR if is_row_hovered else theme.BORDER_COLOR)
                        row_border.setAlphaF(ext_opacity * (1.0 - 0.55 * cp))
                        painter.setBrush(QBrush(row_bg))
                        painter.setPen(QPen(row_border, 1.0))
                        painter.drawRoundedRect(row_rect, 9.0, 9.0)

                        # Task color checkbox
                        task_color = QColor(get_task_color(task_text))
                        cb_size_t = 16.0
                        cb_x_t = task_list_margin + 12.0
                        cb_y_t = ty + (task_item_h - cb_size_t) / 2.0
                        cb_rect_t = QRectF(cb_x_t, cb_y_t, cb_size_t, cb_size_t)
                        cb_qrect_t = QRect(int(cb_x_t - 4), int(cb_y_t - 4), int(cb_size_t + 8), int(cb_size_t + 8))
                        self.notch_task_cb_rects.append((cb_qrect_t, abs_idx, task_text))

                        if cp > 0.0:
                            box_a = int(255 * min(1.0, cp * 1.7) * ext_opacity)
                            cb_fill = QColor(task_color.red(), task_color.green(), task_color.blue(), box_a)
                            painter.setBrush(QBrush(cb_fill))
                            painter.setPen(QPen(cb_fill, 1.5))
                            painter.drawRoundedRect(cb_rect_t, 4.0, 4.0)

                            chk_a = int(255 * max(0.0, (cp - 0.25) / 0.75) * ext_opacity)
                            painter.setPen(QPen(QColor(255, 255, 255, chk_a), 1.8, Qt.PenStyle.SolidLine,
                                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                            chk = QPainterPath()
                            chk.moveTo(cb_x_t + 4.0, cb_y_t + 8.4)
                            chk.lineTo(cb_x_t + 6.9, cb_y_t + 11.5)
                            chk.lineTo(cb_x_t + 12.2, cb_y_t + 4.6)
                            painter.drawPath(chk)
                        elif is_cb_hovered:
                            cb_fill = QColor(task_color.red(), task_color.green(), task_color.blue(), int(55 * ext_opacity))
                            cb_border_c = QColor(task_color)
                            cb_border_c.setAlphaF(ext_opacity)
                            painter.setBrush(QBrush(cb_fill))
                            painter.setPen(QPen(cb_border_c, 1.5))
                            painter.drawRoundedRect(cb_rect_t, 4.0, 4.0)
                        else:
                            painter.setBrush(QBrush(QColor(255, 255, 255, int(8 * ext_opacity))))
                            painter.setPen(QPen(QColor(255, 255, 255, int(38 * ext_opacity)), 1.3))
                            painter.drawRoundedRect(cb_rect_t, 4.0, 4.0)

                        # Play / Focus button on the right edge
                        play_x_t = task_list_margin + task_list_w - play_btn_margin - play_btn_size
                        play_y_t = ty + (task_item_h - play_btn_size) / 2.0
                        play_rect_t = QRectF(play_x_t, play_y_t, play_btn_size, play_btn_size)
                        play_qrect_t = QRect(int(play_x_t - 4), int(play_y_t - 4), int(play_btn_size + 8), int(play_btn_size + 8))
                        self.notch_task_play_rects.append((play_qrect_t, abs_idx, task_text))

                        play_svg_col = accent_color if is_play_hovered else QColor(theme.TEXT_SECONDARY)
                        play_svg_col.setAlphaF(ext_opacity * (1.0 - 0.7 * cp))
                        colored_focus_svg = FOCUS_SVG.replace("COLOR_PLACEHOLDER", play_svg_col.name())
                        renderer_focus = QSvgRenderer(QByteArray(colored_focus_svg.encode("utf-8")))
                        renderer_focus.render(painter, play_rect_t)

                        # Task text (shrunk to not overlap play button)
                        painter.setFont(font_task_list)
                        text_x_t = cb_x_t + cb_size_t + 9.0
                        avail_text_w_t = (task_list_w
                                          - (cb_x_t - task_list_margin) - cb_size_t - 9.0
                                          - play_btn_margin - play_btn_size - play_btn_margin)
                        elided_t = fm_task_list.elidedText(task_text, Qt.TextElideMode.ElideRight, int(avail_text_w_t))
                        text_y_t = ty + (task_item_h / 2.0) + (fm_task_list.capHeight() / 2.0)
                        t_col_t = QColor(task_color) if is_row_hovered else QColor(theme.TEXT_PRIMARY)
                        t_col_t.setAlphaF(ext_opacity * (1.0 - 0.6 * cp))
                        painter.setPen(t_col_t)
                        painter.drawText(QPointF(text_x_t, text_y_t), elided_t)

                        if cp > 0.0:
                            strike_col = QColor(task_color)
                            strike_col.setAlphaF(ext_opacity * max(0.0, 1.0 - max(0.0, cp - 0.75) * 4.0))
                            painter.setPen(QPen(strike_col, 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                            strike_y = text_y_t - (fm_task_list.capHeight() / 2.0)
                            strike_w = fm_task_list.horizontalAdvance(elided_t) * min(1.0, cp * 1.35)
                            painter.drawLine(QPointF(text_x_t, strike_y), QPointF(text_x_t + strike_w, strike_y))

                    painter.restore()

                    # Slim scroll thumb on the right edge (only when the list overflows)
                    if max_scroll > 0.0:
                        track_top = row_top
                        track_h = viewport_h
                        track_w = 3.0
                        # Gutter between the row cards (w-18) and the notch edge curve (w-10)
                        track_x = w - 14.0
                        content_h = self._tasks_content_height(len(all_tasks))
                        thumb_h = max(18.0, track_h * (track_h / content_h))
                        thumb_y = track_top + (track_h - thumb_h) * (self.notch_task_scroll / max_scroll)
                        thumb_col = QColor(theme.TEXT_SECONDARY)
                        thumb_col.setAlphaF(ext_opacity * 0.75)
                        painter.setBrush(QBrush(thumb_col))
                        painter.setPen(Qt.PenStyle.NoPen)
                        painter.drawRoundedRect(QRectF(track_x, thumb_y, track_w, thumb_h), 1.5, 1.5)

            elif self.is_creating_task:
                ext_progress = min(1.0, max(0.0, (h - 54.0) / (104.0 - 54.0)))
                ext_opacity = opacity * ext_progress

                card_x = margin_x
                card_w = w - (margin_x * 2.0)
                card_y = 56.0
                card_h = 36.0
                card_rect = QRectF(card_x, card_y, card_w, card_h)

                painter.setBrush(QBrush(QColor(theme.MAIN_CARD_COLOR)))
                dash_pen = QPen(QColor(255, 255, 255, int(45 * ext_opacity)), 1.0, Qt.PenStyle.DashLine)
                painter.setPen(dash_pen)
                painter.drawRoundedRect(card_rect, 10.0, 10.0)

                # Checkbox placeholder inside input card
                cb_rect2 = QRectF(card_x + 14.0, card_y + 9.0, 18.0, 18.0)
                painter.setBrush(QBrush(QColor(255, 255, 255, int(8 * ext_opacity))))
                painter.setPen(QPen(QColor(255, 255, 255, int(38 * ext_opacity)), 1.4))
                painter.drawRoundedRect(cb_rect2, 4.0, 4.0)

            elif self.is_creating_note:
                ext_progress = min(1.0, max(0.0, (h - 54.0) / (154.0 - 54.0)))
                ext_opacity = opacity * ext_progress

                card_x = margin_x
                card_w = w - (margin_x * 2.0)
                card_y = 52.0
                card_h = max(30.0, h - card_y - 12.0)
                card_rect = QRectF(card_x, card_y, card_w, card_h)

                painter.setBrush(QBrush(QColor(theme.MAIN_CARD_COLOR)))
                dash_pen = QPen(QColor(255, 255, 255, int(45 * ext_opacity)), 1.0, Qt.PenStyle.DashLine)
                painter.setPen(dash_pen)
                painter.drawRoundedRect(card_rect, 10.0, 10.0)

            elif self.notes_in_notch:
                all_notes = self.get_notes_list()
                total_notes = len(all_notes)

                target_ext_h = 84.0 if total_notes == 0 else 176.0
                ext_progress = min(1.0, max(0.0, (h - 54.0) / max(1.0, target_ext_h - 54.0)))
                ext_opacity = opacity * ext_progress

                font_family = config.load_font_family("DM Sans")
                font_note_text = QFont(font_family, 9, QFont.Weight.Medium)
                font_note_copied = QFont(font_family, 8, QFont.Weight.Bold)

                if total_notes == 0:
                    self.notch_note_rects = []
                    self.notch_note_copy_rects = []

                    # Plain clean text without separate background container
                    painter.setFont(font_note_text)
                    empty_col = QColor(theme.TEXT_SECONDARY)
                    empty_col.setAlphaF(ext_opacity)
                    painter.setPen(empty_col)
                    text_rect = QRectF(0.0, 54.0, w, max(1.0, h - 54.0))
                    painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "No notes available")
                else:
                    num_pages = max(1, (total_notes + 2) // 3)
                    self.notch_notes_page = max(0, min(self.notch_notes_page, num_pages - 1))
                    start_idx = self.notch_notes_page * 3
                    page_notes = all_notes[start_idx : start_idx + 3]

                    self.notch_note_rects = []
                    self.notch_note_copy_rects = []

                    margin_notes_x = 22.0
                    avail_w = w - (margin_notes_x * 2.0)
                    gap = 12.0
                    card_w = (avail_w - (gap * 2.0)) / 3.0
                    card_h = 92.0
                    card_y = 64.0
                    for i, note_text in enumerate(page_notes):
                        abs_idx = start_idx + i
                        cx = margin_notes_x + i * (card_w + gap)
                        card_rect = QRectF(cx, card_y, card_w, card_h)
                        card_qrect = QRect(int(cx), int(card_y), int(card_w), int(card_h))
                        self.notch_note_rects.append((card_qrect, abs_idx, note_text))

                        is_hovered = (self.hovered_note_card_idx == abs_idx)
                        card_bg = QColor(theme.HOVER_COLOR if is_hovered else theme.MAIN_CARD_COLOR)
                        card_bg.setAlpha(int(200 * ext_opacity))
                        card_border = QColor(theme.ACCENT_COLOR if is_hovered else theme.BORDER_COLOR)
                        card_border.setAlphaF(ext_opacity)

                        painter.setBrush(QBrush(card_bg))
                        painter.setPen(QPen(card_border, 1.0))
                        painter.drawRoundedRect(card_rect, 12.0, 12.0)

                        # Note text preview (wrapped)
                        painter.setFont(font_note_text)
                        painter.setPen(QColor(theme.TEXT_PRIMARY))
                        text_padding = 10.0
                        text_rect = QRectF(cx + text_padding, card_y + text_padding, card_w - (text_padding * 2.0), card_h - (text_padding * 2.0) - 10.0)

                        preview_text = note_text if len(note_text) <= 80 else note_text[:76] + "..."
                        painter.drawText(text_rect, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, preview_text)

                        # Copy Button at bottom right
                        copy_size = 18.0
                        copy_x = cx + card_w - copy_size - 8.0
                        copy_y = card_y + card_h - copy_size - 8.0
                        copy_qrect = QRect(int(copy_x - 3), int(copy_y - 3), int(copy_size + 6), int(copy_size + 6))
                        self.notch_note_copy_rects.append((copy_qrect, abs_idx, note_text))

                        if self.copied_note_idx == abs_idx:
                            painter.setFont(font_note_copied)
                            painter.setPen(QColor(theme.ACCENT_COLOR))
                            copied_rect = QRectF(cx + card_w - 60.0, copy_y - 2.0, 52.0, copy_size + 4.0)
                            painter.drawText(copied_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "Copied!")
                        else:
                            is_copy_hovered = (self.hovered_note_copy_idx == abs_idx)
                            cp_col = QColor(theme.ACCENT_COLOR if is_copy_hovered else theme.TEXT_SECONDARY)
                            cp_svg = NOTE_COPY_SVG.replace("COLOR_PLACEHOLDER", cp_col.name())
                            r_copy = QSvgRenderer(QByteArray(cp_svg.encode("utf-8")))
                            r_copy.render(painter, QRectF(copy_x, copy_y, copy_size, copy_size))

                    # Pagination indicator if > 1 page
                    if num_pages > 1:
                        page_str = f"{self.notch_notes_page + 1} / {num_pages}"
                        painter.setFont(font_note_copied)
                        painter.setPen(QColor(theme.TEXT_SECONDARY))
                        pag_rect = QRectF(0, card_y + card_h + 3.0, w, 14.0)
                        painter.drawText(pag_rect, Qt.AlignmentFlag.AlignCenter, page_str)

    def draw_typewriter_text(self, painter, w, h, opacity, accent_col):
        """Draw live typed text with smooth caret glide and smooth 6-character ribbon scroll."""
        font_family = config.load_font_family("DM Sans")
        font = QFont(font_family, 12, QFont.Weight.Bold)
        painter.setFont(font)
        fm = painter.fontMetrics()

        raw_text = self.typed_text
        cur_w = 2.0
        cur_gap = 3.0

        if not raw_text:
            # Empty text: center cursor bar
            total_content_w = cur_w
            target_start_x = (w - total_content_w) / 2.0
            cy = h / 2.0

            # Smooth cursor interpolation
            self.smooth_cursor_x += (target_start_x - self.smooth_cursor_x) * 0.40

            now = time.time()
            is_active = (self.last_key_time == 0.0) or (now - self.last_key_time < 0.35)
            cursor_alpha = 1.0 if is_active else (0.35 + 0.65 * (0.5 + 0.5 * math.cos(now * 6.5)))

            cursor_col = QColor(accent_col)
            cursor_col.setAlphaF(opacity * cursor_alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(cursor_col))
            painter.drawRoundedRect(QRectF(self.smooth_cursor_x, cy - 13.0 / 2.0, cur_w, 13.0), 1.0, 1.0)
            return

        # Width of visible 6 characters (viewport box)
        visible_sub = raw_text[-6:]
        vis_w = fm.horizontalAdvance(visible_sub)
        total_w = fm.horizontalAdvance(raw_text)

        # Target scroll offset to keep only latest 6 chars in view
        target_scroll = max(0.0, float(total_w - vis_w))
        self.scroll_x += (target_scroll - self.scroll_x) * 0.35

        box_w = vis_w + cur_gap + cur_w
        box_x = (w - box_w) / 2.0
        cy = h / 2.0

        # Clip rendering to the 6-character viewport window so overflowing chars scroll smoothly
        painter.save()
        painter.setClipRect(QRectF(box_x - 1.0, 0.0, box_w + 3.0, h))

        text_col = QColor(theme.TEXT_PRIMARY)
        text_col.setAlphaF(opacity)
        painter.setPen(text_col)

        # Draw raw text smoothly offset by scroll_x
        draw_x = box_x - self.scroll_x
        painter.drawText(QPointF(draw_x, cy + fm.capHeight() / 2.0), raw_text)
        painter.restore()

        # Smooth cursor at the end of the text
        target_cur_x = draw_x + total_w + cur_gap
        # Lerp caret position
        self.smooth_cursor_x += (target_cur_x - self.smooth_cursor_x) * 0.40

        now = time.time()
        is_active = (self.last_key_time == 0.0) or (now - self.last_key_time < 0.35)
        cursor_alpha = 1.0 if is_active else (0.35 + 0.65 * (0.5 + 0.5 * math.cos(now * 6.5)))

        cursor_col = QColor(accent_col)
        cursor_col.setAlphaF(opacity * cursor_alpha)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(cursor_col))
        painter.drawRoundedRect(QRectF(self.smooth_cursor_x, cy - 13.0 / 2.0, cur_w, 13.0), 1.0, 1.0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    notch = NotchWidget()
    notch.show()
    sys.exit(app.exec())
