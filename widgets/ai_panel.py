import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QScrollArea, QFrame, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer

from utils import config
from styles import theme
from widgets.toolbar import ToolbarButton

AI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M19 9 17.5 5.5 14 4 17.5 2.5 19 1l1.5 1.5L24 4l-3.5 1.5zm-7-2L10.5 3.5 7 2 10.5.5 12 2l1.5-1.5L17 2l-3.5 1.5zm-5 13L5.5 16.5 2 15l3.5-1.5L7 12l1.5 1.5L12 15l-3.5 1.5zM11.5 6.5l-2.5 5.5-5.5 2.5 5.5 2.5 2.5 5.5 2.5-5.5 5.5-2.5-5.5-2.5zm-1 3.8 1 2.2 2.2 1-2.2 1-1 2.2-1-2.2-2.2-1 2.2-1z"/></svg>"""
SEND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M2.01 21 23 12 2.01 3 2 10l15 2-15 2z"/></svg>"""
TRASH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>"""

class GeminiWorker(QThread):
    finished = Signal(bool, str)
    
    def __init__(self, api_key, prompt):
        super().__init__()
        self.api_key = api_key
        self.prompt = prompt
        
    def run(self):
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {"parts": [{"text": self.prompt}]}
            ]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                data = response.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                self.finished.emit(True, text.strip())
            else:
                try:
                    err_msg = response.json().get("error", {}).get("message", "API Error")
                except Exception:
                    err_msg = f"HTTP Error {response.status_code}"
                self.finished.emit(False, err_msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class ChatBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatBubble")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_text = QLabel(text, self)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        
        # Style bubbles
        bg = "rgba(255, 159, 10, 35)" if is_user else "rgba(255, 255, 255, 12)"
        border = f"1px solid {theme.ACCENT_COLOR}" if is_user else f"1px solid {theme.BORDER_COLOR}"
        text_color = theme.TEXT_PRIMARY
        
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                background-color: {bg};
                border: {border};
                border-radius: 10px;
                padding: 6px 10px;
            }}
        """)
        
        if is_user:
            layout.addStretch(1)
            layout.addWidget(self.lbl_text, 4)
        else:
            layout.addWidget(self.lbl_text, 4)
            layout.addStretch(1)


class AIPanel(QWidget):
    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.is_expanded = False
        self.active_worker = None
        
        self.init_ui()
        
        # Height Animation configuration
        self.setFixedHeight(0)
        self.height_anim = QPropertyAnimation(self, b"anim_height")
        self.height_anim.setDuration(250)

    def init_ui(self):
        # Base Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(6)
        
        # Frame Container matching Spotify Panel card styling
        self.card = QFrame(self)
        self.card.setObjectName("AICard")
        self.card.setStyleSheet(f"""
            QFrame#AICard {{
                background-color: rgba(30, 30, 35, 140);
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 12px;
            }}
        """)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(8, 8, 8, 8)
        card_layout.setSpacing(6)
        
        # Chat Scroll Area
        self.scroll = QScrollArea(self.card)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 40);
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch(1) # Keeps messages pushed to bottom
        
        self.scroll.setWidget(self.chat_content)
        card_layout.addWidget(self.scroll, 1)
        
        # Welcome/Disclaimer label
        self.lbl_welcome = QLabel("👋 Ask Gemini AI anything!", self.card)
        self.lbl_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_welcome.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-family: {theme.FONT_FAMILY}; font-size: 10px;")
        self.chat_layout.addWidget(self.lbl_welcome)
        
        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.input_field = QLineEdit(self.card)
        self.input_field.setPlaceholderText("Ask Gemini...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(0, 0, 0, 60);
                border: 1px solid {theme.BORDER_COLOR};
                border-radius: 6px;
                color: {theme.TEXT_PRIMARY};
                font-family: {theme.FONT_FAMILY};
                font-size: 11px;
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.ACCENT_COLOR};
            }}
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        # Send button
        self.btn_send = ToolbarButton(SEND_SVG, "Send message", self.card, draw_background_hover=True)
        self.btn_send.setFixedSize(24, 24)
        self.btn_send.clicked.connect(self.send_message)
        
        # Clear button
        self.btn_clear = ToolbarButton(TRASH_SVG, "Clear chat", self.card, draw_background_hover=True)
        self.btn_clear.setFixedSize(24, 24)
        self.btn_clear.clicked.connect(self.clear_chat)
        
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.btn_send)
        input_layout.addWidget(self.btn_clear)
        card_layout.addLayout(input_layout)
        
        main_layout.addWidget(self.card)
        
        # Apply slight drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.card.setGraphicsEffect(shadow)

    def get_anim_height(self):
        return self.height()

    def set_anim_height(self, h):
        self.setFixedHeight(h)
        if self.parent_window:
            self.parent_window.adjust_layout_height()

    anim_height = Property(int, get_anim_height, set_anim_height)

    def toggle(self):
        self.show()
        self.is_expanded = not self.is_expanded
        
        if self.parent_window and hasattr(self.parent_window, 'toolbar'):
            self.parent_window.toolbar.btn_ai.setActive(self.is_expanded)
            
        self.height_anim.stop()
        self.height_anim.setStartValue(self.height())
        if self.is_expanded:
            self.height_anim.setEndValue(190) # Height of the chat widget card
        else:
            self.height_anim.setEndValue(0)
        self.height_anim.start()

    def collapse(self):
        if self.is_expanded:
            self.toggle()

    def send_message(self):
        prompt = self.input_field.text().strip()
        if not prompt:
            return
            
        # Hide welcome prompt
        self.lbl_welcome.hide()
        
        # Add User bubble
        self.add_bubble(prompt, is_user=True)
        self.input_field.clear()
        
        # Check API Key
        api_key = config.load_gemini_api_key()
        if not api_key:
            self.add_bubble("⚠️ Gemini API Key not set! Please save your key in Ticky Settings -> AI tab.", is_user=False)
            return
            
        # Add thinking indicator
        self.thinking_bubble = ChatBubble("AI is thinking...", is_user=False, parent=self)
        self.chat_layout.addWidget(self.thinking_bubble)
        self.scroll_to_bottom()
        
        # Disable buttons while working
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Spawn thread worker
        self.active_worker = GeminiWorker(api_key, prompt)
        self.active_worker.finished.connect(self.on_response_received)
        self.active_worker.start()

    def on_response_received(self, success, text):
        # Remove thinking indicator
        if hasattr(self, 'thinking_bubble') and self.thinking_bubble:
            self.chat_layout.removeWidget(self.thinking_bubble)
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None
            
        # Re-enable inputs
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
        
        # Add response bubble
        self.add_bubble(text, is_user=False)

    def add_bubble(self, text, is_user=True):
        bubble = ChatBubble(text, is_user, self)
        self.chat_layout.addWidget(bubble)
        self.scroll_to_bottom()

    def clear_chat(self):
        # Remove all chat bubbles (except the spacer)
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                self.chat_layout.removeWidget(widget)
                widget.deleteLater()
        self.lbl_welcome.show()
        self.chat_layout.addWidget(self.lbl_welcome)

    def scroll_to_bottom(self):
        # Allow layout to adjust first, then scroll
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
