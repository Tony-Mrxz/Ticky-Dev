import os
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QScrollArea, QFrame, QGraphicsDropShadowEffect, QSpacerItem, QSizePolicy)
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor
from PySide6.QtSvg import QSvgRenderer

from utils import config
from styles import theme
from widgets.toolbar import ToolbarButton

AI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M20 10c-.74 0-1.38.4-1.72 1H13V9h4c.55 0 1-.45 1-1V5.72c.6-.35 1-.98 1-1.72 0-1.1-.9-2-2-2s-2 .9-2 2c0 .74.4 1.38 1 1.72V7h-3V5c0-1.65-1.35-3-3-3-1.3 0-2.41.83-2.83 2.01A3.51 3.51 0 0 0 4 7.5c0 .33.05.65.14.96C2.87 9.14 2 10.49 2 12c0 1.08.43 2.09 1.17 2.83-.11.38-.17.77-.17 1.17 0 1.96 1.41 3.59 3.31 3.93C6.86 21.16 8.11 22 9.5 22c1.93 0 3.5-1.57 3.5-3.5V17h3v1.28c-.6.35-1 .98-1 1.72 0 1.1.9 2 2 2s2-.9 2-2c0-.74-.4-1.38-1-1.72V16c0-.55-.45-1-1-1h-4v-2h5.28c.35.6.98 1 1.72 1 1.1 0 2-.9 2-2s-.9-2-2-2m-9 8.5c0 .83-.67 1.5-1.5 1.5-.71 0-1.33-.5-1.47-1.2l-.21-.8H7c-1.1 0-2-.9-2-2 0-.35.08-.68.25-.98l.46-.82-.78-.51C4.35 13.31 4 12.68 4 12c0-.98.72-1.82 1.68-1.97l1.69-.26-1.06-1.35c-.2-.26-.32-.59-.32-.92 0-.83.67-1.5 1.5-1.5.11 0 .21.01.31.03l1.19.17V4.99c0-.55.45-1 1-1s1 .45 1 1v13.5Z"></path></svg>"""
SEND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="m9 17 6-5-6-5v4H2v2h7z"></path><path d="M13 3v2c3.86 0 7 3.14 7 7s-3.14 7-7 7v2c4.96 0 9-4.04 9-9s-4.04-9-9-9"></path></svg>"""

class AIWorker(QThread):
    finished = Signal(bool, str)
    
    def __init__(self, provider, model, api_key, prompt):
        super().__init__()
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.prompt = prompt
        
    def run(self):
        import requests
        
        provider = self.provider.lower().strip()
        model = self.model.strip()
        api_key = self.api_key.strip()
        
        if not model:
            if provider == "gemini":
                model = "gemini-1.5-flash"
            elif provider == "openai":
                model = "gpt-4o-mini"
            elif provider == "claude":
                model = "claude-3-5-sonnet-20241022"
            elif provider == "groq":
                model = "llama-3.3-70b-versatile"
            elif provider == "openrouter":
                model = "meta-llama/llama-3-8b-instruct:free"
            else:
                model = "gemini-1.5-flash"

        try:
            if provider == "gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": self.prompt}]}]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    self.finished.emit(True, text.strip())
                else:
                    err_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.finished.emit(False, err_msg)
                    
            elif provider == "openai":
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": self.prompt}]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    self.finished.emit(True, text.strip())
                else:
                    err_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.finished.emit(False, err_msg)
                    
            elif provider == "claude":
                url = "https://api.anthropic.com/v1/messages"
                headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                payload = {
                    "model": model,
                    "max_tokens": 1024,
                    "messages": [{"role": "user", "content": self.prompt}]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    text = data["content"][0]["text"]
                    self.finished.emit(True, text.strip())
                else:
                    err_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.finished.emit(False, err_msg)
                    
            elif provider == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": self.prompt}]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    self.finished.emit(True, text.strip())
                else:
                    err_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.finished.emit(False, err_msg)
                    
            elif provider == "openrouter":
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": self.prompt}]
                }
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 200:
                    data = response.json()
                    text = data["choices"][0]["message"]["content"]
                    self.finished.emit(True, text.strip())
                else:
                    err_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                    self.finished.emit(False, err_msg)
                    
            else:
                self.finished.emit(False, f"Unsupported provider: {self.provider}")
        except Exception as e:
            self.finished.emit(False, str(e))


class ChatBubble(QFrame):
    def __init__(self, text, is_user=True, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatBubble")
        self.is_user = is_user
        
        # Prevent the bubble row itself from ever expanding horizontally
        from PySide6.QtWidgets import QSizePolicy as _SP
        self.setSizePolicy(_SP.Policy.Expanding, _SP.Policy.Minimum)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.lbl_text = QLabel(text, self)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # Shrink to content but never grow beyond available width
        self.lbl_text.setSizePolicy(_SP.Policy.Expanding, _SP.Policy.Minimum)
        
        if is_user:
            layout.addStretch(1)
            layout.addWidget(self.lbl_text, 4)
        else:
            layout.addWidget(self.lbl_text, 4)
            layout.addStretch(1)
        
        self.refresh_style()

    def refresh_style(self):
        from styles import theme as _theme
        bg = "rgba(255, 159, 10, 35)" if self.is_user else "rgba(255, 255, 255, 12)"
        border = f"1px solid {_theme.ACCENT_COLOR}" if self.is_user else f"1px solid {_theme.BORDER_COLOR}"
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                color: {_theme.TEXT_PRIMARY};
                font-family: {_theme.FONT_FAMILY};
                font-size: {_theme.TASK_SIZE}px;
                background-color: {bg};
                border: {border};
                border-radius: 10px;
                padding: 6px 10px;
            }}
        """)


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
        
        # Frame Container matching task list card background
        self.card = QFrame(self)
        self.card.setObjectName("AICard")
        self.card.setStyleSheet(f"""
            QFrame#AICard {{
                background-color: {theme.MAIN_CARD_COLOR};
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
        # Prevent the inner widget from stretching wider than the scroll viewport
        from PySide6.QtWidgets import QSizePolicy as _SP
        self.chat_content.setSizePolicy(_SP.Policy.Expanding, _SP.Policy.Preferred)
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 4, 0)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch(1) # Keeps messages pushed to bottom
        
        self.scroll.setWidget(self.chat_content)
        card_layout.addWidget(self.scroll, 1)
        
        # Welcome/Disclaimer label
        self.lbl_welcome = QLabel(self.card)
        self.lbl_welcome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_welcome.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-family: {theme.FONT_FAMILY}; font-size: {theme.TASK_SIZE - 2}px;")
        self.chat_layout.addWidget(self.lbl_welcome)
        
        # Input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.input_field = QLineEdit(self.card)
        self._apply_input_style()
        self.input_field.returnPressed.connect(self.send_message)
        
        # Send button
        self.btn_send = ToolbarButton(SEND_SVG, "Send message", self.card, draw_background_hover=True)
        self.btn_send.setFixedSize(24, 24)
        self.btn_send.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.btn_send)
        card_layout.addLayout(input_layout)
        
        main_layout.addWidget(self.card)
        
        # Apply slight drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 2)
        self.card.setGraphicsEffect(shadow)
        
        self.update_welcome_text()

    def _apply_input_style(self):
        from styles import theme as _theme
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(0, 0, 0, 80);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 14px;
                color: {_theme.TEXT_PRIMARY};
                font-family: {_theme.FONT_FAMILY};
                font-size: {_theme.TASK_SIZE}px;
                padding: 6px 12px;
                min-height: 16px;
            }}
            QLineEdit:focus {{
                border: 1px solid {_theme.ACCENT_COLOR};
                background-color: rgba(0, 0, 0, 100);
            }}
        """)

    def refresh_styles(self):
        """Re-apply font family and size to all chat elements (called by refresh_theme)."""
        from styles import theme as _theme
        # Welcome label — guard against deleted C++ object (can happen if clear_chat ran deleteLater)
        try:
            if self.lbl_welcome and not self.lbl_welcome.isHidden() or True:
                self.lbl_welcome.setStyleSheet(
                    f"color: {_theme.TEXT_SECONDARY}; font-family: {_theme.FONT_FAMILY}; font-size: {_theme.TASK_SIZE - 2}px;"
                )
        except RuntimeError:
            pass  # C++ object already deleted — safe to ignore
        # Card background
        self.card.setStyleSheet(f"""
            QFrame#AICard {{
                background-color: {_theme.MAIN_CARD_COLOR};
                border: 1px solid {_theme.BORDER_COLOR};
                border-radius: 12px;
            }}
        """)
        # Input field
        self._apply_input_style()
        # All existing chat bubbles
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ChatBubble):
                item.widget().refresh_style()

    def update_welcome_text(self):
        provider = config.load_ai_provider()
        self.lbl_welcome.setText(f"👋 Ask {provider} AI anything!")
        self.input_field.setPlaceholderText(f"Ask {provider}...")

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
            # Clear previous session's messages every time the panel opens
            self.clear_chat()
            self.update_welcome_text()
            self.height_anim.setEndValue(190)
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
        
        # Load API configurations
        provider = config.load_ai_provider()
        model = config.load_ai_model()
        api_key = config.load_ai_api_key()
        
        if not api_key:
            self.add_bubble(f"⚠️ API Key not set! Please save your key in Ticky Settings -> AI Chat tab.", is_user=False)
            return
            
        # Detect incorrect provider selection based on API key prefix to prevent authorization errors
        if api_key.startswith("gsk_") and provider.lower() != "groq":
            self.add_bubble(f"⚠️ API Key Mismatch!\nYour API key starts with 'gsk_', which is a Groq key, but the selected provider is '{provider}'. Please change the AI Provider to 'Groq' in Settings -> AI Chat.", is_user=False)
            return
        elif api_key.startswith("sk-or-v1-") and provider.lower() != "openrouter":
            self.add_bubble(f"⚠️ API Key Mismatch!\nYour API key starts with 'sk-or-v1-', which is an OpenRouter key, but the selected provider is '{provider}'. Please change the AI Provider to 'OpenRouter' in Settings -> AI Chat.", is_user=False)
            return
        elif api_key.startswith("sk-ant-") and provider.lower() != "claude":
            self.add_bubble(f"⚠️ API Key Mismatch!\nYour API key starts with 'sk-ant-', which is a Claude key, but the selected provider is '{provider}'. Please change the AI Provider to 'Claude' in Settings -> AI Chat.", is_user=False)
            return
        elif (api_key.startswith("sk-proj-") or (api_key.startswith("sk-") and not api_key.startswith("sk-or-v1-") and not api_key.startswith("sk-ant-"))) and provider.lower() != "openai":
            self.add_bubble(f"⚠️ API Key Mismatch!\nYour API key starts with 'sk-', which is an OpenAI key, but the selected provider is '{provider}'. Please change the AI Provider to 'OpenAI' in Settings -> AI Chat.", is_user=False)
            return
        elif api_key.startswith("AIzaSy") and provider.lower() != "gemini":
            self.add_bubble(f"⚠️ API Key Mismatch!\nYour API key starts with 'AIzaSy', which is a Gemini key, but the selected provider is '{provider}'. Please change the AI Provider to 'Gemini' in Settings -> AI Chat.", is_user=False)
            return
            
        # Add thinking indicator
        self.thinking_bubble = ChatBubble("AI is thinking...", is_user=False, parent=self)
        self.chat_layout.addWidget(self.thinking_bubble)
        self.scroll_to_bottom()
        
        # Disable inputs while working
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Spawn thread worker
        self.active_worker = AIWorker(provider, model, api_key, prompt)
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
        # Remove lbl_welcome from layout first so it doesn't get deleteLater'd below
        self.chat_layout.removeWidget(self.lbl_welcome)
        # Delete all temporary chat bubble widgets
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                self.chat_layout.removeWidget(widget)
                widget.deleteLater()
        # Re-add and show the persistent welcome label
        self.chat_layout.addWidget(self.lbl_welcome)
        self.lbl_welcome.show()

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
