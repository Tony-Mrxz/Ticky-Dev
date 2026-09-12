# widgets/notepad_widgets.py
"""Grid squares and maximized text editor widgets for the Mini Notepad feature."""

import re
import html
from PySide6.QtCore import Qt, Signal, QSize, QTimer, QByteArray, QPropertyAnimation, QEasingCurve, QUrl
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QIcon, QSyntaxHighlighter, QTextCharFormat, QDesktopServices
from styles import theme

URL_REGEX = re.compile(r'(?:https?://|www\.)[^\s<>"{}|\\^`\[\]()]+(?:\([^\s<>]+\)|[^\s<>"{}|\\^`\[\]().,;:!?])')

class NoteUrlHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

    def highlightBlock(self, text):
        if not text:
            return
        
        link_format = QTextCharFormat()
        accent_hex = theme.ACCENT_COLOR if theme and hasattr(theme, 'ACCENT_COLOR') else "#0A84FF"
        link_format.setForeground(QColor(accent_hex))
        link_format.setFontUnderline(True)

        for match in URL_REGEX.finditer(text):
            start = match.start()
            length = match.end() - start
            self.setFormat(start, length, link_format)


class NoteTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.highlighter = NoteUrlHighlighter(self.document())
        self._pressed_pos = None

    def _get_url_at_pos(self, pos):
        cursor = self.cursorForPosition(pos)
        block_text = cursor.block().text()
        pos_in_block = cursor.positionInBlock()

        for match in URL_REGEX.finditer(block_text):
            if match.start() <= pos_in_block <= match.end():
                return match.group()
        return None

    def mouseMoveEvent(self, event):
        url = self._get_url_at_pos(event.pos())
        if url:
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
            self.setToolTip(f"Click to open {url}")
        else:
            self.viewport().setCursor(Qt.CursorShape.IBeamCursor)
            self.setToolTip("")
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed_pos = event.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._pressed_pos:
            dist = (event.pos() - self._pressed_pos).manhattanLength()
            if dist < 4:
                url_str = self._get_url_at_pos(event.pos())
                if url_str:
                    full_url = url_str if url_str.startswith(("http://", "https://")) else "https://" + url_str
                    QDesktopServices.openUrl(QUrl(full_url))
        self._pressed_pos = None
        super().mouseReleaseEvent(event)

class CopyShortcutButton(QPushButton):
    COPY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" fill="COLOR" viewBox="0 0 24 24">
    <path d="M20 2H10c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m0 12H10V4h10z"></path>
    <path d="M14 20H4V10h2V8H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2v-2h-2z"></path>
    </svg>"""
    
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFixedSize(22, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { border: none; background: transparent; }")
        self._hovered = False
        self.refresh_icon()
        
    def enterEvent(self, event):
        self._hovered = True
        self.refresh_icon()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self._hovered = False
        self.refresh_icon()
        super().leaveEvent(event)
        
    def refresh_icon(self):
        from PySide6.QtSvg import QSvgRenderer
        color = theme.ACCENT_COLOR if self._hovered else theme.TEXT_SECONDARY
        
        svg_str = self.COPY_SVG.replace("COLOR", color)
        renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
        pixmap = QPixmap(14, 14)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        
        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(14, 14))


class NoteSquareWidget(QFrame):
    clicked = Signal(int)
    
    def __init__(self, index, text, color_hex, parent=None):
        super().__init__(parent)
        self.index = index
        self.text = text
        self.color_hex = color_hex
        self.setObjectName("NoteSquareWidget")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(157, 90)
        
        # Truncate text preview for label
        preview_text = text if len(text) <= 75 else text[:72] + "..."
        escaped_preview = html.escape(preview_text)
        accent_hex = theme.ACCENT_COLOR if theme and hasattr(theme, 'ACCENT_COLOR') else "#0A84FF"
        formatted_preview = URL_REGEX.sub(
            lambda m: f'<a href="{m.group()}" style="color: {accent_hex}; text-decoration: underline;">{m.group()}</a>',
            escaped_preview
        )
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        
        self.lbl = QLabel(formatted_preview, self)
        self.lbl.setTextFormat(Qt.TextFormat.RichText)
        self.lbl.setOpenExternalLinks(True)
        self.lbl.setWordWrap(True)
        self.lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.lbl)
        
        self.btn_copy = CopyShortcutButton(self)
        self.btn_copy.setGeometry(129, 62, 22, 22)
        self.btn_copy.clicked.connect(self.on_copy_clicked)
        self.btn_copy.hide()
        
        self.update_style()
        
    def update_style(self):
        self.setStyleSheet(f"""
            QFrame#NoteSquareWidget {{
                background-color: {theme.MAIN_CARD_COLOR};
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 12px;
            }}
            QFrame#NoteSquareWidget:hover {{
                background-color: {theme.HOVER_COLOR};
                border: 1px solid {self.color_hex};
            }}
        """)
        self.lbl.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 10px;
                line-height: 1.2;
            }}
        """)
        
    def enterEvent(self, event):
        self.btn_copy.show()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.btn_copy.hide()
        super().leaveEvent(event)
        
    def on_copy_clicked(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text)
            orig_text = self.lbl.text()
            self.lbl.setText("Copied!")
            self.lbl.setStyleSheet(f"QLabel {{ color: {theme.ACCENT_COLOR}; font-family: {theme.FONT_FAMILY}; font-size: 10px; font-weight: bold; }}")
            QTimer.singleShot(1500, lambda: self.restore_lbl(orig_text))
            
    def restore_lbl(self, orig_text):
        self.lbl.setText(orig_text)
        self.lbl.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 10px;
                line-height: 1.2;
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.index)
            event.accept()
        else:
            super().mousePressEvent(event)


class MaximizedNoteWidget(QWidget):
    back_clicked = Signal(int, str)
    
    BACK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="COLOR" viewBox="0 0 24 24">
    <path d="M9 10h6c2.21 0 4 1.79 4 4s-1.79 4-4 4h-3v2h3c3.31 0 6-2.69 6-6s-2.69-6-6-6H9V4L3 9l6 5z"></path>
    </svg>"""
    
    COPY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="COLOR" viewBox="0 0 24 24">
    <path d="M20 2H10c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m0 12H10V4h10z"></path>
    <path d="M14 20H4V10h2V8H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2v-2h-2z"></path>
    </svg>"""

    DELETE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="COLOR" viewBox="0 0 24 24">
    <path d="M17 6V4c0-1.1-.9-2-2-2H9c-1.1 0-2 .9-2 2v2H2v2h2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8h2V6zM9 4h6v2H9zM6 20V8h12v12z"></path><path d="M9 10h2v8H9zm4 0h2v8h-2z"></path>
    </svg>"""

    def __init__(self, index, text, color_hex, parent=None):
        super().__init__(parent)
        self.index = index
        self.color_hex = color_hex
        self.setObjectName("MaximizedNoteWidget")
        self.setFixedHeight(138)
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0.0)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)
        
        self.card_frame = QFrame(self)
        self.card_frame.setObjectName("NoteCardFrame")
        
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(12, 6, 12, 6)
        card_layout.setSpacing(2)
        
        # 1. Top Bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        self.btn_back = QPushButton(self.card_frame)
        self.btn_back.setToolTip("Back to Notes")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setFixedSize(28, 28)
        self.btn_back.clicked.connect(self.on_back)
        
        self.btn_copy = QPushButton(self.card_frame)
        self.btn_copy.setToolTip("Copy Note")
        self.btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy.setFixedSize(28, 28)
        self.btn_copy.clicked.connect(self.on_copy)
        
        self.lbl_title = QLabel("Note Editor", self.card_frame)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        top_bar.addWidget(self.btn_back)
        top_bar.addStretch()
        top_bar.addWidget(self.lbl_title)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_copy)
        card_layout.addLayout(top_bar)
        
        # 2. Text Editor (Fills full height of card frame)
        self.text_edit = NoteTextEdit(self.card_frame)
        self.text_edit.setPlaceholderText("Type your note here...")
        self.text_edit.setText(text)
        self.text_edit.textChanged.connect(self.on_text_changed)
        card_layout.addWidget(self.text_edit, 1)
        
        # 3. Floating Delete Button (Overlaid at bottom right of card_frame)
        self.btn_delete = QPushButton(self.card_frame)
        self.btn_delete.setToolTip("Delete Note")
        self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_delete.setFixedSize(22, 22)
        self.btn_delete._hovered = False
        self.btn_delete.clicked.connect(self.on_delete)
        self.btn_delete.raise_()
        
        main_layout.addWidget(self.card_frame)
        
        self.update_style()
        self.update_icons()
        self.on_text_changed()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'btn_delete') and self.btn_delete and hasattr(self, 'card_frame'):
            fw = self.card_frame.width()
            fh = self.card_frame.height()
            self.btn_delete.move(fw - 26, fh - 26)
            self.btn_delete.raise_()

    def _on_delete_enter(self, e):
        self.btn_delete._hovered = True
        self.update_icons()

    def _on_delete_leave(self, e):
        self.btn_delete._hovered = False
        self.update_icons()

    def enterEvent(self, event):
        super().enterEvent(event)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        
    def update_style(self):
        sec_color = QColor(theme.SEC_CARD_COLOR)
        bg_rgba = f"rgba({sec_color.red()}, {sec_color.green()}, {sec_color.blue()}, 152)"
        
        self.card_frame.setStyleSheet(f"""
            QFrame#NoteCardFrame {{
                background-color: {bg_rgba};
                border: 1px solid rgba(255, 255, 255, 0.09);
                border-radius: 10px;
            }}
        """)
        self.lbl_title.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 10px;
                font-weight: bold;
            }}
        """)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                line-height: 1.3;
                padding-right: 4px;
                padding-bottom: 2px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px 0px 0px 0px;
                border: none;
            }}
            QScrollBar::track:vertical {{
                background: transparent;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.25);
                min-height: 16px;
                border-radius: 2px;
                margin: 0px 1px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.ACCENT_COLOR};
                border-radius: 3px;
                margin: 0px 0px;
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {theme.ACCENT_COLOR};
                border-radius: 3px;
                margin: 0px 0px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                width: 0px;
                background: transparent;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
                border: none;
            }}
        """)
        
    def update_icons(self):
        from PySide6.QtSvg import QSvgRenderer
        
        accent = theme.ACCENT_COLOR
        back_svg = self.BACK_SVG.replace("COLOR", accent)
        copy_svg = self.COPY_SVG.replace("COLOR", accent if self.btn_copy.isEnabled() else "rgba(255,255,255,0.15)")
        delete_svg = self.DELETE_SVG.replace("COLOR", accent)
        
        for btn, svg_str in [(self.btn_back, back_svg), (self.btn_copy, copy_svg), (self.btn_delete, delete_svg)]:
            renderer = QSvgRenderer(QByteArray(svg_str.encode('utf-8')))
            pixmap = QPixmap(20, 20)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(QSize(20, 20))
            btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
            
    def on_text_changed(self):
        text = self.text_edit.toPlainText().strip()
        is_valid = len(text) > 0
        
        self.btn_copy.setEnabled(is_valid)
        self.update_icons()
        
    def animate_show(self):
        self.show_fade = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.show_fade.setDuration(220)
        self.show_fade.setStartValue(0.0)
        self.show_fade.setEndValue(1.0)
        self.show_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.show_height1 = QPropertyAnimation(self, b"minimumHeight", self)
        self.show_height1.setDuration(220)
        self.show_height1.setStartValue(0)
        self.show_height1.setEndValue(138)
        self.show_height1.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.show_height2 = QPropertyAnimation(self, b"maximumHeight", self)
        self.show_height2.setDuration(220)
        self.show_height2.setStartValue(0)
        self.show_height2.setEndValue(138)
        self.show_height2.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.show_fade.start()
        self.show_height1.start()
        self.show_height2.start()
        
    def animate_hide(self, callback):
        self.hide_fade = QPropertyAnimation(self.opacity_effect, b"opacity", self)
        self.hide_fade.setDuration(180)
        self.hide_fade.setStartValue(self.opacity_effect.opacity())
        self.hide_fade.setEndValue(0.0)
        self.hide_fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_height1 = QPropertyAnimation(self, b"minimumHeight", self)
        self.hide_height1.setDuration(180)
        self.hide_height1.setStartValue(self.height())
        self.hide_height1.setEndValue(0)
        self.hide_height1.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_height2 = QPropertyAnimation(self, b"maximumHeight", self)
        self.hide_height2.setDuration(180)
        self.hide_height2.setStartValue(self.height())
        self.hide_height2.setEndValue(0)
        self.hide_height2.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_height1.finished.connect(callback)
        
        self.hide_fade.start()
        self.hide_height1.start()
        self.hide_height2.start()
        
    def on_back(self):
        new_text = self.text_edit.toPlainText().strip()
        self.animate_hide(lambda: self.back_clicked.emit(self.index, new_text))
        
    def on_delete(self):
        self.animate_hide(lambda: self.back_clicked.emit(self.index, ""))

    def on_copy(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_edit.toPlainText())
            self.lbl_title.setText("Copied!")
            self.lbl_title.setStyleSheet(f"QLabel {{ color: {theme.ACCENT_COLOR}; font-family: {theme.FONT_FAMILY}; font-size: 10px; font-weight: bold; }}")
            QTimer.singleShot(1500, lambda: self.lbl_title.setText("Note Editor"))
            QTimer.singleShot(1500, lambda: self.lbl_title.setStyleSheet(f"QLabel {{ color: {theme.TEXT_SECONDARY}; font-family: {theme.FONT_FAMILY}; font-size: 10px; font-weight: bold; }}"))
