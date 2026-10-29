# ui/onboarding_window.py
"""First-run onboarding wizard: intro, appearance, AI config, detection."""

import os
import sys

from PySide6.QtCore import Qt, QSize, QPointF, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap, QBrush
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QLineEdit, QComboBox, QVBoxLayout,
    QHBoxLayout, QGridLayout, QColorDialog, QSizePolicy,
    QLayout, QApplication,
)
from PySide6.QtMultimedia import QMediaDevices

from styles import theme
from styles.qss import get_onboarding_style, get_appearance_style
from utils import config

# Bump when the wizard gains a page or its meaning changes; returning users
# whose stored version is lower see it again.
ONBOARDING_VERSION = 1

INTRO_SIZE = QSize(720, 440)
MAIN_SIZE = QSize(940, 620)

AI_PROVIDERS = ["Gemini", "OpenAI", "Claude", "Groq", "OpenRouter"]


def _asset_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    return os.path.join(base, filename)


class StepDots(QWidget):
    """One dot per wizard page; the active one is drawn wider in the accent colour."""

    def __init__(self, count, parent=None):
        super().__init__(parent)
        self.count = count
        self.index = 0
        self.setFixedSize(24 * count, 10)

    def set_index(self, index):
        self.index = index
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(self.count):
            x = i * 24
            if i == self.index:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(theme.ACCENT_COLOR)))
                p.drawRoundedRect(QRect(x, 2, 14, 6), 3, 3)
            else:
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(theme.TEXT_SECONDARY).darker(170)))
                p.drawEllipse(QPointF(x + 4, 5), 2.5, 2.5)


class PageHost(QWidget):
    """Stacks the wizard pages on top of each other and shows one at a time.

    QStackedWidget advertises the maximum of every page's minimum and writes it
    back onto itself, which held the small intro window at the appearance page's
    height. Plain show/hide keeps the window's size entirely under our control.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages = []
        self._index = 0

    def addWidget(self, page):
        page.setParent(self)
        page.setGeometry(self.rect())
        page.setVisible(not self._pages)
        self._pages.append(page)

    def setCurrentIndex(self, index):
        self._index = index
        for position, page in enumerate(self._pages):
            page.setVisible(position == index)

    def currentIndex(self):
        return self._index

    def widget(self, index):
        return self._pages[index]

    def count(self):
        return len(self._pages)

    def minimumSizeHint(self):
        return QSize(0, 0)

    def resizeEvent(self, event):
        for page in self._pages:
            page.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)


class HeroImage(QWidget):
    """Artwork painted into whatever space the layout gives it.

    A QLabel with a pixmap would report the pixmap as its minimum size hint, so
    each resize would demand more height and the window would grow on its own.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def has_image(self):
        return self._pixmap is not None

    def minimumSizeHint(self):
        return QSize(0, 0)

    def paintEvent(self, event):
        if self._pixmap is None:
            return
        side = min(self.width(), self.height()) - 16
        if side <= 0:
            return
        scaled = self._pixmap.scaled(side, side, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                     Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(x, y, side, side, 16, 16)
        p.setClipPath(path)
        p.drawPixmap(x - (scaled.width() - side) // 2, y - (scaled.height() - side) // 2, scaled)
        p.end()


class OnboardingWindow(QWidget):
    """Frameless wizard window that starts small on the intro and grows for the setup pages."""

    finished = Signal()

    def __init__(self, parent_window=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setWindowTitle("Welcome to Ticky")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self._appearance_dirty = False
        self._selected_accent = config.load_accent_color("#0A84FF")
        self._selected_theme = config.load_theme("Amoled Pure")
        self.drag_start_pos = None
        self.window_start_pos = None

        hero_path = _asset_path("ticky-1.png")
        src = QPixmap(hero_path) if os.path.exists(hero_path) else QPixmap()
        self._hero_src = None if src.isNull() else src

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.container = QFrame(self)
        self.container.setObjectName("OnbContainer")
        # The window drives its own size; content may never raise its minimum.
        self.container.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        outer.addWidget(self.container)

        root = QVBoxLayout(self.container)
        root.setContentsMargins(22, 18, 22, 20)
        root.setSpacing(14)
        # The wizard window drives its own size; a page may never push it larger.
        root.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        self.container.setMinimumSize(0, 0)

        root.addLayout(self._build_header())

        self.pages = PageHost(self.container)
        self.pages.addWidget(self._build_intro_page())
        self.pages.addWidget(self._build_appearance_page())
        self.pages.addWidget(self._build_ai_page())
        self.pages.addWidget(self._build_detection_page())
        for i in range(self.pages.count()):
            self.pages.widget(i).layout().setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        root.addWidget(self.pages, 1)

        self.shadow = None
        self._restyle()
        self._apply_page_geometry(0, animate=False)

    # -- chrome -----------------------------------------------------------
    def _build_header(self):
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(10)

        self.lbl_wordmark = QLabel("TICKY", self.container)
        self.lbl_wordmark.setObjectName("OnbWordmark")
        self.lbl_wordmark.setVisible(False)

        self.step_dots = StepDots(4, self.container)

        self.btn_close = QPushButton("✕", self.container)
        self.btn_close.setObjectName("OnbClose")
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setAccessibleName("Skip onboarding")
        self.btn_close.clicked.connect(self.close)

        header.addWidget(self.lbl_wordmark)
        header.addStretch(1)
        header.addWidget(self.step_dots, 0, Qt.AlignmentFlag.AlignVCenter)
        header.addStretch(1)
        header.addWidget(self.btn_close, 0, Qt.AlignmentFlag.AlignVCenter)
        return header

    # -- page 1: intro ----------------------------------------------------
    def _build_intro_page(self):
        page = QWidget()
        page.setObjectName("OnbIntroPage")
        lay = QHBoxLayout(page)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(22)

        left = QVBoxLayout()
        left.setSpacing(10)

        title = QLabel("Ticky", page)
        title.setObjectName("OnbTitle")
        subtitle = QLabel("LIVING DESKTOP", page)
        subtitle.setObjectName("OnbSubtitle")

        body = QLabel(
            "Ticky turns the edge of your screen into a living strip: tasks, reminders, "
            "a focus timer, your media and AI chat — all one hover away, with no windows "
            "to open and nothing to switch back to.",
            page,
        )
        body.setObjectName("OnbBody")
        body.setWordWrap(True)

        features = QVBoxLayout()
        features.setSpacing(5)
        for text in (
            "•  Tasks and reminders that live inside the notch",
            "•  Focus timer and media controls without a window",
            "•  Voice detection and dictation with your own mic",
            "•  AI chat and search powered by your own key",
        ):
            lbl = QLabel(text, page)
            lbl.setObjectName("OnbFeature")
            lbl.setWordWrap(True)
            features.addWidget(lbl)

        self.btn_intro_next = QPushButton("Next", page)
        self.btn_intro_next.setObjectName("OnbPrimary")
        self.btn_intro_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_intro_next.clicked.connect(lambda: self.go_page(1))

        left.addWidget(title)
        left.addWidget(subtitle)
        left.addSpacing(4)
        left.addWidget(body)
        left.addSpacing(2)
        left.addLayout(features)
        left.addStretch(1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch(1)
        actions.addWidget(self.btn_intro_next)
        left.addLayout(actions)

        lay.addLayout(left, 5)

        self.hero = HeroImage(page)
        self.hero.setObjectName("OnbHero")
        if self._hero_src is not None:
            self.hero.setPixmap(self._hero_src)
        lay.addWidget(self.hero, 4)
        return page

    # -- page 2: appearance ------------------------------------------------
    def _build_appearance_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(12)

        heading = QLabel("Make it yours", page)
        heading.setObjectName("OnbHeading")
        intro = QLabel("Pick an accent colour and a UI theme. Everything applies live — save to keep it.", page)
        intro.setObjectName("OnbBody")
        intro.setWordWrap(True)
        lay.addWidget(heading)
        lay.addWidget(intro)

        accent_box = self._section(page, "Accent colour", "Used for highlights, active buttons and the notch glow.")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.accent_swatches = []
        for color in theme.ACCENT_PRESETS:
            sw = self._make_swatch(color, accent_box)
            self.accent_swatches.append(sw)
            row.addWidget(sw)
        row.addStretch(1)
        self.btn_custom_accent = QPushButton("Custom…", accent_box)
        self.btn_custom_accent.setObjectName("OnbGhost")
        self.btn_custom_accent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_custom_accent.clicked.connect(self._pick_custom_accent)
        row.addWidget(self.btn_custom_accent)
        accent_box.layout().addLayout(row)

        theme_box = self._section(page, "UI theme", "The surface palette behind every Ticky element.")
        grid = QGridLayout()
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        self.theme_cards = []
        from ui.settings_window import ThemeStyleCard
        names = list(theme.THEMES.keys())
        for i, name in enumerate(names):
            card = ThemeStyleCard(name, theme.THEMES[name], name == self._selected_theme, theme_box)
            card.theme_selected.connect(self._on_theme_selected)
            self.theme_cards.append(card)
            grid.addWidget(card, i // 5, i % 5)
        theme_box.layout().addLayout(grid)

        lay.addStretch(1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addStretch(1)
        self.btn_appearance_save = QPushButton("Save", page)
        self.btn_appearance_save.setObjectName("OnbGhost")
        self.btn_appearance_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_appearance_save.clicked.connect(self._save_appearance)
        self.btn_appearance_next = QPushButton("Next", page)
        self.btn_appearance_next.setObjectName("OnbPrimary")
        self.btn_appearance_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_appearance_next.setEnabled(False)
        self.btn_appearance_next.clicked.connect(lambda: self.go_page(2))
        bottom.addWidget(self.btn_appearance_save)
        bottom.addWidget(self.btn_appearance_next)
        lay.addLayout(bottom)
        return page

    def _make_swatch(self, color, parent):
        from ui.settings_window import ColorSwatch
        sw = ColorSwatch(color, color.lower() == self._selected_accent.lower(), parent)
        sw.color_selected.connect(self._on_accent_selected)
        return sw

    # -- page 3: AI config ---------------------------------------------------
    def _build_ai_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(12)

        heading = QLabel("Bring in an AI", page)
        heading.setObjectName("OnbHeading")
        intro = QLabel(
            "The AI panel in the notch uses a key you bring — nothing is shared or sold. "
            "Skip this now and add it later from Settings whenever you like.",
            page,
        )
        intro.setObjectName("OnbBody")
        intro.setWordWrap(True)
        lay.addWidget(heading)
        lay.addWidget(intro)
        lay.addStretch(1)

        box = self._section(page, "Provider & key", "Your provider decides which models the notch can reach.")
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)

        lbl_provider = QLabel("Provider", box)
        lbl_provider.setObjectName("OnbSectionTitle")
        self.combo_provider = QComboBox(box)
        self.combo_provider.setObjectName("OnbInput")
        self.combo_provider.addItems(AI_PROVIDERS)
        self.combo_provider.setCurrentText(config.load_ai_provider())
        self.combo_provider.currentTextChanged.connect(self._on_provider_changed)

        lbl_key = QLabel("API key", box)
        lbl_key.setObjectName("OnbSectionTitle")
        self.input_ai_key = QLineEdit(box)
        self.input_ai_key.setObjectName("OnbInput")
        self.input_ai_key.setPlaceholderText("Paste your API key here")
        self.input_ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_ai_key.setText(config.load_ai_api_key())

        lbl_model = QLabel("Model", box)
        lbl_model.setObjectName("OnbSectionTitle")
        self.input_ai_model = QLineEdit(box)
        self.input_ai_model.setObjectName("OnbInput")
        self.input_ai_model.setPlaceholderText("Optional — leave empty for auto")
        self.input_ai_model.setText(config.load_ai_model(""))

        form.addWidget(lbl_provider, 0, 0)
        form.addWidget(self.combo_provider, 0, 1)
        form.addWidget(lbl_key, 1, 0)
        form.addWidget(self.input_ai_key, 1, 1)
        form.addWidget(lbl_model, 2, 0)
        form.addWidget(self.input_ai_model, 2, 1)
        form.setColumnStretch(1, 1)
        box.layout().addLayout(form)

        self.lbl_ai_hint = QLabel("", box)
        self.lbl_ai_hint.setObjectName("OnbSectionDesc")
        self.lbl_ai_hint.setWordWrap(True)
        box.layout().addWidget(self.lbl_ai_hint)

        lay.addStretch(1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addStretch(1)
        self.btn_ai_skip = QPushButton("Skip for now", page)
        self.btn_ai_skip.setObjectName("OnbGhost")
        self.btn_ai_skip.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai_skip.clicked.connect(lambda: self.go_page(3))
        self.btn_ai_next = QPushButton("Next", page)
        self.btn_ai_next.setObjectName("OnbPrimary")
        self.btn_ai_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai_next.clicked.connect(self._finish_ai_page)
        bottom.addWidget(self.btn_ai_skip)
        bottom.addWidget(self.btn_ai_next)
        lay.addLayout(bottom)

        self._refresh_ai_hint(self.combo_provider.currentText())
        return page

    # -- page 4: detection ----------------------------------------------------
    def _build_detection_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(4, 6, 4, 4)
        lay.setSpacing(12)

        heading = QLabel("Ticky — Detection (Beta)", page)
        heading.setObjectName("OnbHeading")
        intro = QLabel(
            "Detection listens to the microphone you choose and turns speech into tasks, notes "
            "and reminders straight from the notch. It is local to your machine and only records "
            "while you hold the dictation hotkey — pick the mic that actually hears you.",
            page,
        )
        intro.setObjectName("OnbBody")
        intro.setWordWrap(True)
        lay.addWidget(heading)
        lay.addWidget(intro)
        lay.addStretch(1)

        box = self._section(page, "Microphone", "Used by voice dictation and reminder detection.")
        mic_row = QHBoxLayout()
        mic_row.setSpacing(10)
        self.combo_mic = QComboBox(box)
        self.combo_mic.setObjectName("OnbInput")
        self.combo_mic.addItem("System Default", "")
        try:
            for dev in QMediaDevices().audioInputs():
                self.combo_mic.addItem(dev.description(), dev.id())
        except Exception:
            pass
        saved_idx = self.combo_mic.findData(config.load_mic_device_id(""))
        self.combo_mic.setCurrentIndex(saved_idx if saved_idx >= 0 else 0)
        self.combo_mic.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        mic_row.addWidget(self.combo_mic)
        box.layout().addLayout(mic_row)

        self.lbl_mic_status = QLabel("", box)
        self.lbl_mic_status.setObjectName("OnbSectionDesc")
        self.lbl_mic_status.setWordWrap(True)
        box.layout().addWidget(self.lbl_mic_status)
        self._update_mic_status()
        self.combo_mic.currentIndexChanged.connect(self._update_mic_status)

        lay.addStretch(1)

        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addStretch(1)
        self.btn_mic_save = QPushButton("Save", page)
        self.btn_mic_save.setObjectName("OnbGhost")
        self.btn_mic_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mic_save.clicked.connect(self._save_mic)
        self.btn_start = QPushButton("Start Ticky!", page)
        self.btn_start.setObjectName("OnbPrimary")
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self._start_ticky)
        bottom.addWidget(self.btn_mic_save)
        bottom.addWidget(self.btn_start)
        lay.addLayout(bottom)
        return page

    # -- helpers -----------------------------------------------------------
    def _section(self, parent, title, description):
        box = QFrame(parent)
        box.setObjectName("OnbSection")
        lay = QVBoxLayout(box)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)
        lbl_title = QLabel(title, box)
        lbl_title.setObjectName("OnbSectionTitle")
        lbl_desc = QLabel(description, box)
        lbl_desc.setObjectName("OnbSectionDesc")
        lbl_desc.setWordWrap(True)
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_desc)
        box.layout().addSpacing(2)
        parent.layout().addWidget(box)
        return box

    def _restyle(self):
        self.setStyleSheet(get_onboarding_style() + get_appearance_style())
        self.step_dots.update()
        for card in getattr(self, "theme_cards", []):
            card.setActive(card.theme_name == self._selected_theme)

    def _on_accent_selected(self, color_hex):
        self._set_accent(color_hex)
        self._appearance_dirty = True
        self.btn_appearance_next.setEnabled(False)

    def _set_accent(self, color_hex):
        self._selected_accent = color_hex
        theme.ACCENT_COLOR = color_hex
        for sw in self.accent_swatches:
            sw.setSelected(sw.color_hex.lower() == color_hex.lower())
        self._restyle()

    def _pick_custom_accent(self):
        col = QColorDialog.getColor(QColor(self._selected_accent), self, "Custom accent colour")
        if not col.isValid():
            return
        self._set_accent(col.name())
        self._appearance_dirty = True
        self.btn_appearance_next.setEnabled(False)

    def _on_theme_selected(self, name):
        self._selected_theme = name
        theme.apply_theme(name)
        self._appearance_dirty = True
        self.btn_appearance_next.setEnabled(False)
        for card in self.theme_cards:
            card.setActive(card.theme_name == name)

    def _save_appearance(self):
        config.save_accent_color(self._selected_accent)
        config.save_theme(self._selected_theme)
        self._appearance_dirty = False
        self.btn_appearance_next.setEnabled(True)
        self._flash(self.btn_appearance_save, "Save")

    def _on_provider_changed(self, provider):
        self._refresh_ai_hint(provider)

    def _refresh_ai_hint(self, provider):
        if not hasattr(self, "lbl_ai_hint"):
            return
        default_model = {
            "Gemini": "gemini-1.5-flash",
            "OpenAI": "gpt-4o-mini",
            "Claude": "claude-3-5-haiku-latest",
            "Groq": "llama-3.3-70b-versatile",
            "OpenRouter": "auto",
        }.get(provider, "")
        self.lbl_ai_hint.setText(f"No model typed? Ticky falls back to {default_model} for {provider}.")

    def _finish_ai_page(self):
        config.save_ai_provider(self.combo_provider.currentText())
        config.save_ai_api_key(self.input_ai_key.text().strip())
        config.save_ai_model(self.input_ai_model.text().strip())
        self.go_page(3)

    def _update_mic_status(self):
        if not hasattr(self, "lbl_mic_status"):
            return
        name = self.combo_mic.currentText()
        if self.combo_mic.currentData() or name == "System Default":
            self.lbl_mic_status.setText(f"Ready to listen on: {name}. Say it, hold the dictation hotkey, and Ticky writes it down.")
        else:
            self.lbl_mic_status.setText("This mic is no longer connected — pick another one before you start.")

    def _save_mic(self):
        config.save_mic_device_id(self.combo_mic.currentData() or "")
        self._flash(self.btn_mic_save, "Save")

    def _start_ticky(self):
        self._save_mic()
        self.close()

    def _flash(self, button, restore_text):
        from PySide6.QtCore import QTimer
        button.setText("Saved!")
        QTimer.singleShot(1400, lambda: button.setText(restore_text))

    # -- navigation & geometry ------------------------------------------------
    def go_page(self, index):
        self.pages.setCurrentIndex(index)
        self.step_dots.set_index(index)
        self.lbl_wordmark.setVisible(index > 0)
        self._apply_page_geometry(index, animate=True)

    def _target_size(self, index):
        return INTRO_SIZE if index == 0 else MAIN_SIZE

    def _apply_page_geometry(self, index, animate=True):
        size = self._target_size(index)
        start = self.geometry()
        x, y = start.x(), start.y()
        if self.isVisible() and start.width() > 0:
            # Grow and shrink around the middle so the wizard never jumps sideways
            x = int(start.x() + (start.width() - size.width()) / 2)
            y = int(start.y() + (start.height() - size.height()) / 2)

        if not animate:
            self.setFixedSize(size)
            self.move(x, y)
            self._center_on_screen()
            return

        anim = getattr(self, "_geo_anim", None)
        if anim is not None and anim.state() == QPropertyAnimation.State.Running:
            anim.stop()
            self._lock_current_size()

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self._geo_anim = QPropertyAnimation(self, b"geometry", self)
        self._geo_anim.setDuration(300)
        self._geo_anim.setStartValue(self.geometry())
        self._geo_anim.setEndValue(QRect(x, y, size.width(), size.height()))
        self._geo_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._geo_anim.finished.connect(self._lock_current_size)
        self._geo_anim.start()

    def _lock_current_size(self):
        size = self._target_size(self.pages.currentIndex())
        self.setFixedSize(size)

    def _center_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.center().x() - self.width() // 2,
                  area.center().y() - self.height() // 2)

    def showEvent(self, event):
        super().showEvent(event)
        self._lock_current_size()
        if getattr(self, "_positioned", False):
            return
        self._positioned = True
        self._center_on_screen()

    # -- drag ---------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 60:
            self.drag_start_pos = event.globalPosition().toPoint()
            self.window_start_pos = self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_start_pos and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            if self.window_start_pos is not None and delta.manhattanLength() > 3:
                self.move(self.window_start_pos + delta)
                event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None

    # -- close --------------------------------------------------------------
    def closeEvent(self, event):
        if self._appearance_dirty:
            self._save_appearance()
        config.save_onboarding_version(ONBOARDING_VERSION)
        if self.parent_window and hasattr(self.parent_window, "notch_widget"):
            try:
                self.parent_window.notch_widget.apply_notch_style()
            except Exception:
                pass
        self.finished.emit()
        super().closeEvent(event)
