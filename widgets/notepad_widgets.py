# widgets/notepad_widgets.py
"""Grid squares and maximized text editor widgets for the Mini Notepad feature."""

from PySide6.QtCore import Qt, Signal, QSize, QTimer, QByteArray, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPixmap, QIcon
from styles import theme

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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        
        self.lbl = QLabel(preview_text, self)
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
    <path d="M9.16 12.25 6.63 10H15c2.21 0 4 1.79 4 4v6h2v-6c0-3.31-2.69-6-6-6H6.63l2.53-2.25-1.33-1.49-5.34 4.75 5.34 4.75 1.33-1.49Z"></path>
    </svg>"""
    
    COPY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="COLOR" viewBox="0 0 24 24">
    <path d="M20 2H10c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m0 12H10V4h10z"></path>
    <path d="M14 20H4V10h2V8H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2v-2h-2z"></path>
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
        card_layout.setContentsMargins(12, 6, 12, 8)
        card_layout.setSpacing(4)
        
        # 1. Top Bar
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        self.btn_back = QPushButton(self.card_frame)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setFixedSize(28, 28)
        self.btn_back.clicked.connect(self.on_back)
        
        self.btn_copy = QPushButton(self.card_frame)
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
        
        # 2. Text Editor
        self.text_edit = QTextEdit(self.card_frame)
        self.text_edit.setPlaceholderText("Type your note here...")
        self.text_edit.setText(text)
        self.text_edit.textChanged.connect(self.on_text_changed)
        card_layout.addWidget(self.text_edit)
        
        main_layout.addWidget(self.card_frame)
        
        self.update_style()
        self.update_icons()
        self.on_text_changed()
        
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
            }}
        """)
        
    def update_icons(self):
        from PySide6.QtSvg import QSvgRenderer
        
        accent = theme.ACCENT_COLOR
        back_svg = self.BACK_SVG.replace("COLOR", accent)
        copy_svg = self.COPY_SVG.replace("COLOR", accent if self.btn_copy.isEnabled() else "rgba(255,255,255,0.15)")
        
        for btn, svg_str in [(self.btn_back, back_svg), (self.btn_copy, copy_svg)]:
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
        
    def on_copy(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.text_edit.toPlainText())
            self.lbl_title.setText("Copied!")
            self.lbl_title.setStyleSheet(f"QLabel {{ color: {theme.ACCENT_COLOR}; font-family: {theme.FONT_FAMILY}; font-size: 10px; font-weight: bold; }}")
            QTimer.singleShot(1500, lambda: self.lbl_title.setText("Note Editor"))
            QTimer.singleShot(1500, lambda: self.lbl_title.setStyleSheet(f"QLabel {{ color: {theme.TEXT_SECONDARY}; font-family: {theme.FONT_FAMILY}; font-size: 10px; font-weight: bold; }}"))
