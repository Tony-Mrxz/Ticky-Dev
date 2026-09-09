# widgets/ai_panel.py
"""Ticky AI Panel with Natural Language Intent Detection (Task & Note Actions)."""

import os
import json
import re
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QScrollArea, QFrame, QGraphicsDropShadowEffect,
                               QSpacerItem, QSizePolicy, QPushButton)
from PySide6.QtCore import Qt, Property, QPropertyAnimation, QEasingCurve, QThread, Signal, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QCursor, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer

from utils import config
from styles import theme
from widgets.toolbar import ToolbarButton

AI_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M20 10c-.74 0-1.38.4-1.72 1H13V9h4c.55 0 1-.45 1-1V5.72c.6-.35 1-.98 1-1.72 0-1.1-.9-2-2-2s-2 .9-2 2c0 .74.4 1.38 1 1.72V7h-3V5c0-1.65-1.35-3-3-3-1.3 0-2.41.83-2.83 2.01A3.51 3.51 0 0 0 4 7.5c0 .33.05.65.14.96C2.87 9.14 2 10.49 2 12c0 1.08.43 2.09 1.17 2.83-.11.38-.17.77-.17 1.17 0 1.96 1.41 3.59 3.31 3.93C6.86 21.16 8.11 22 9.5 22c1.93 0 3.5-1.57 3.5-3.5V17h3v1.28c-.6.35-1 .98-1 1.72 0 1.1.9 2 2 2s2-.9 2-2c0-.74-.4-1.38-1-1.72V16c0-.55-.45-1-1-1h-4v-2h5.28c.35.6.98 1 1.72 1 1.1 0 2-.9 2-2s-.9-2-2-2m-9 8.5c0 .83-.67 1.5-1.5 1.5-.71 0-1.33-.5-1.47-1.2l-.21-.8H7c-1.1 0-2-.9-2-2 0-.35.08-.68.25-.98l.46-.82-.78-.51C4.35 13.31 4 12.68 4 12c0-.98.72-1.82 1.68-1.97l1.69-.26-1.06-1.35c-.2-.26-.32-.59-.32-.92 0-.83.67-1.5 1.5-1.5.11 0 .21.01.31.03l1.19.17V4.99c0-.55.45-1 1-1s1 .45 1 1v13.5Z"></path></svg>"""
SEND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="m21.41 11.09-18-8a1 1 0 0 0-1.09.19c-.29.28-.39.7-.25 1.08l2.87 7.65-2.87 7.65c-.14.38-.04.8.25 1.08a1 1 0 0 0 1.1.18l18-8a.998.998 0 0 0 0-1.82ZM4.78 18.12l1.23-3.27V15l6-3-6-3v.15L4.78 5.88 18.54 12z"></path></svg>"""

SYSTEM_PROMPT = """You are Ticky AI, an intelligent desktop assistant integrated into the Ticky productivity application.
Your task is to ALWAYS provide a complete, friendly, helpful chat response to the user AND automatically detect actions (TASK or NOTE) implied by their message.

CRITICAL CHAT RESPONSE MANDATE:
- `chat_response`: You MUST ALWAYS fill `chat_response` with your complete, helpful, natural language message to the user.
- For research/information queries (e.g. "Can you do a small research on binary digits?"): Write the FULL research and answers in `chat_response`, AND confirm that you also saved the summary as a note 📝.
- For tasks (e.g. "We gotta update the website now"): Write a friendly confirmation in `chat_response` (e.g., "Got it! I've added **Update the website** to your tasks.\\nWant to start working on it now?").
- For notes (e.g. "Remember port is 3000"): Write a friendly confirmation in `chat_response` (e.g., "Saved it as a note. 📝").
- NEVER leave `chat_response` empty, short, or blank!

INTENT DETECTION RULES:

1. TASK INTENT:
   - When user message implies an item to DO ("We gotta update website", "Finish assignment tomorrow", "Call John").
   - Extract concise title. Extract metadata ONLY if explicitly provided (due_date, priority). Do NOT invent missing details.
   - Action item: {"name": "create_task", "params": {"title": "...", "due_date": "...", "priority": "..."}}
   - Set show_start_button: true, created_task_title: "title".

2. NOTE INTENT:
   - When user request implies saving info ("Research binary digits", "Remember website port is 3000", "Save this idea").
   - Action item: {"name": "create_note", "params": {"title": "...", "content": "..."}}

3. START TASK INTENT:
   - When user asks to start a task or says "start it", "let's do it", "yes start".
   - Action item: {"name": "start_task", "params": {"title": "..."}}

4. AMBIGUOUS INTENT:
   - Statements where intent is unclear ("The website needs updating.").
   - Ask a short clarification in `chat_response` ("Want me to add 'Update the website' to your tasks?"). Set actions: [].

OUTPUT REQUIREMENTS:
Output strictly valid JSON matching:
{
  "actions": [
    {
      "name": "create_task" | "create_note" | "start_task",
      "params": { ... }
    }
  ],
  "chat_response": "YOUR FULL COMPLETE HELPFUL CHAT MESSAGE HERE",
  "show_start_button": false,
  "created_task_title": ""
}
"""

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
                    "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
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
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": self.prompt}
                    ],
                    "response_format": {"type": "json_object"}
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
                    "system": SYSTEM_PROMPT,
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
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": self.prompt}
                    ],
                    "response_format": {"type": "json_object"}
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
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": self.prompt}
                    ],
                    "response_format": {"type": "json_object"}
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
    def __init__(self, text, is_user=True, parent=None, action_buttons=None):
        super().__init__(parent)
        self.setObjectName("ChatBubble")
        self.is_user = is_user
        
        from PySide6.QtWidgets import QSizePolicy as _SP
        self.setSizePolicy(_SP.Policy.Expanding, _SP.Policy.Minimum)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 2)
        main_layout.setSpacing(4)
        
        bubble_layout = QHBoxLayout()
        bubble_layout.setContentsMargins(0, 0, 0, 0)
        bubble_layout.setSpacing(0)
        
        self.lbl_text = QLabel(text, self)
        self.lbl_text.setTextFormat(Qt.TextFormat.MarkdownText)
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_text.setOpenExternalLinks(True)
        self.lbl_text.setSizePolicy(_SP.Policy.Preferred, _SP.Policy.Minimum)
        self.lbl_text.setMaximumWidth(240)
        
        if is_user:
            bubble_layout.addStretch(1)
            bubble_layout.addWidget(self.lbl_text, 0)
        else:
            bubble_layout.addWidget(self.lbl_text, 0)
            bubble_layout.addStretch(1)
            
        main_layout.addLayout(bubble_layout)
        
        # Action buttons for AI messages (e.g. [ Start Task ] [ Not now ])
        if not is_user and action_buttons:
            btn_container = QHBoxLayout()
            btn_container.setContentsMargins(0, 4, 0, 2)
            btn_container.setSpacing(6)
            
            from styles import theme as _theme
            for btn_info in action_buttons:
                btn_label = btn_info.get("label", "Action")
                btn = QPushButton(btn_label, self)
                btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                
                is_primary = "start" in btn_label.lower() or "yes" in btn_label.lower()
                if is_primary:
                    btn_style = f"""
                        QPushButton {{
                            background-color: {_theme.ACCENT_COLOR};
                            color: #FFFFFF;
                            border: none;
                            border-radius: 10px;
                            font-family: {_theme.FONT_FAMILY};
                            font-size: 11px;
                            font-weight: 700;
                            padding: 4px 10px;
                        }}
                        QPushButton:hover {{
                            background-color: {_theme.ACCENT_COLOR};
                            opacity: 0.9;
                        }}
                    """
                else:
                    btn_style = f"""
                        QPushButton {{
                            background-color: rgba(255, 255, 255, 15);
                            color: {_theme.TEXT_PRIMARY};
                            border: 1px solid rgba(255, 255, 255, 20);
                            border-radius: 10px;
                            font-family: {_theme.FONT_FAMILY};
                            font-size: 11px;
                            font-weight: 600;
                            padding: 4px 10px;
                        }}
                        QPushButton:hover {{
                            background-color: rgba(255, 255, 255, 30);
                        }}
                    """
                btn.setStyleSheet(btn_style)
                
                callback = btn_info.get("callback")
                if callback:
                    # Safely absorb clicked(bool) signal argument so callback receives its intended parameters
                    btn.clicked.connect(lambda checked=False, cb=callback: cb())
                    
                btn_container.addWidget(btn)
                
            btn_container.addStretch(1)
            main_layout.addLayout(btn_container)
            
        self.refresh_style()

    def refresh_style(self):
        from styles import theme as _theme
        if self.is_user:
            bg = _theme.ACCENT_COLOR
            border = "none"
            text_color = "#FFFFFF"
            corners = """
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom-right-radius: 3px;
                border-bottom-left-radius: 14px;
            """
        else:
            bg = "rgba(255, 255, 255, 12)"
            border = "1px solid rgba(255, 255, 255, 15)"
            text_color = _theme.TEXT_PRIMARY
            corners = """
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom-right-radius: 14px;
                border-bottom-left-radius: 3px;
            """
            
        self.lbl_text.setStyleSheet(f"""
            QLabel {{
                color: {text_color};
                font-family: {_theme.FONT_FAMILY};
                font-size: {_theme.TASK_SIZE}px;
                background-color: {bg};
                border: {border};
                {corners}
                padding: 6px 12px;
            }}
        """)


class AIPanel(QWidget):
    def __init__(self, parent_window=None):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.is_expanded = False
        self.has_messages = False
        self.active_worker = None
        self.last_created_task = None
        
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
        
        # Frame Container matching transparent background
        self.card = QFrame(self)
        self.card.setObjectName("AICard")
        self.card.setStyleSheet("""
            QFrame#AICard {
                background: transparent;
                border: none;
            }
        """)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
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
        from PySide6.QtWidgets import QSizePolicy as _SP
        self.chat_content.setSizePolicy(_SP.Policy.Expanding, _SP.Policy.Preferred)
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(0, 0, 4, 0)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch(1) # Keeps messages pushed to bottom
        
        self.scroll.setWidget(self.chat_content)
        card_layout.addWidget(self.scroll, 1)

        # Input row container (positioned at BOTTOM)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.input_field = QLineEdit(self.card)
        self.input_field.setPlaceholderText("Ticky, I want help with..")
        self._apply_input_style()
        self.input_field.returnPressed.connect(self.send_message)
        
        # Send button
        self.btn_send = ToolbarButton(SEND_SVG, "Send message", self.card, draw_background_hover=True)
        self.btn_send.setFixedSize(26, 26)
        self.btn_send.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.btn_send)
        card_layout.addLayout(input_layout)
        
        main_layout.addWidget(self.card)

    def _apply_input_style(self):
        from styles import theme as _theme
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(255, 255, 255, 20);
                border: 1px solid rgba(255, 255, 255, 25);
                border-radius: 16px;
                color: {_theme.TEXT_PRIMARY};
                font-family: {_theme.FONT_FAMILY};
                font-size: {_theme.TASK_SIZE}px;
                padding: 8px 14px;
                min-height: 18px;
            }}
            QLineEdit:focus {{
                border: 1px solid {_theme.ACCENT_COLOR};
                background-color: rgba(255, 255, 255, 30);
            }}
        """)

    def refresh_styles(self):
        self.card.setStyleSheet("""
            QFrame#AICard {
                background: transparent;
                border: none;
            }
        """)
        self._apply_input_style()
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ChatBubble):
                item.widget().refresh_style()

    def update_welcome_text(self):
        self.input_field.setPlaceholderText("Ticky, I want help with..")

    def get_anim_height(self):
        return self.height()

    def set_anim_height(self, h):
        self.setFixedHeight(h)
        if self.parent_window:
            self.parent_window.adjust_layout_height()

    anim_height = Property(int, get_anim_height, set_anim_height)

    def update_panel_height(self, animate=True):
        if not self.is_expanded:
            return
            
        base_input_height = 72
        if not self.has_messages:
            target = base_input_height
        else:
            self.chat_layout.activate()
            self.chat_content.adjustSize()
            chat_h = self.chat_layout.sizeHint().height()
            target = min(190, max(base_input_height, base_input_height + chat_h))
            
        if animate and self.height() != target:
            self.height_anim.stop()
            self.height_anim.setStartValue(self.height())
            self.height_anim.setEndValue(target)
            self.height_anim.start()
        elif not animate:
            self.set_anim_height(target)

    def toggle(self):
        self.show()
        self.is_expanded = not self.is_expanded
        
        if self.parent_window and hasattr(self.parent_window, 'toolbar'):
            self.parent_window.toolbar.btn_ai.setActive(self.is_expanded)
            
        self.height_anim.stop()
        self.height_anim.setStartValue(self.height())
        if self.is_expanded:
            self.clear_chat()
            self.height_anim.setEndValue(72)
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
            
        self.has_messages = True
        
        # Local handling for affirmative responses after a task was created
        prompt_lower = prompt.lower()
        start_keywords = ["yes", "start", "start it", "let's do it", "lets do it", "do it", "sure", "start task", "work on it", "yep", "yeah"]
        if self.last_created_task and prompt_lower in start_keywords:
            target = self.last_created_task
            self.last_created_task = None
            self.add_bubble(prompt, is_user=True)
            self.input_field.clear()
            if self.parent_window:
                self.parent_window.start_task_by_title(target)
                self.add_bubble(f"Starting **{target}** now! 🚀", is_user=False)
            return

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
        QTimer.singleShot(20, lambda: self.update_panel_height(animate=True))
        self.scroll_to_bottom()
        
        # Disable inputs while working
        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)
        
        # Spawn thread worker
        self.active_worker = AIWorker(provider, model, api_key, prompt)
        self.active_worker.finished.connect(self.on_response_received)
        self.active_worker.start()

    def parse_ai_response(self, text):
        clean_text = text.strip()

        # Strip triple backticks if whole text is wrapped in ```json ... ```
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        actions = []
        chat_response = ""
        show_start = False
        created_task_title = ""

        # Attempt 1: Direct JSON parse of clean_text
        try:
            data = json.loads(clean_text)
            if isinstance(data, dict):
                actions = data.get("actions", [])
                chat_response = str(data.get("chat_response") or "").strip()
                show_start = bool(data.get("show_start_button", False))
                created_task_title = str(data.get("created_task_title") or "").strip()
                if chat_response or actions:
                    return actions, chat_response, show_start, created_task_title
        except Exception:
            pass

        # Attempt 2: Extract embedded JSON block via regex
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{[\s\S]*\"actions\"[\s\S]*\})", text)

        if json_match:
            json_str = json_match.group(1).strip()
            text_outside = text.replace(json_match.group(0), "").strip()
            try:
                data = json.loads(json_str)
                if isinstance(data, dict):
                    actions = data.get("actions", [])
                    chat_response = str(data.get("chat_response") or text_outside).strip()
                    show_start = bool(data.get("show_start_button", False))
                    created_task_title = str(data.get("created_task_title") or "").strip()
                    return actions, chat_response, show_start, created_task_title
            except Exception:
                pass

        # Attempt 3: Plain text response fallback
        return actions, text.strip(), show_start, created_task_title

    def on_response_received(self, success, text):
        if hasattr(self, 'thinking_bubble') and self.thinking_bubble:
            self.chat_layout.removeWidget(self.thinking_bubble)
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None
            
        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

        if not success:
            self.add_bubble(f"⚠️ Error: {text}", is_user=False)
            return

        actions, chat_response, show_start, created_task_title = self.parse_ai_response(text)

        action_created_tasks = []
        action_created_notes = []

        if actions and self.parent_window:
            for act in actions:
                act_name = act.get("name")
                params = act.get("params", {})
                if act_name == "create_task":
                    title = params.get("title")
                    if title:
                        due = params.get("due_date")
                        prio = params.get("priority")
                        full_title = self.parent_window.add_task_from_ai(title, due_date=due, priority=prio)
                        if full_title:
                            action_created_tasks.append(full_title)
                            self.last_created_task = full_title
                elif act_name == "create_note":
                    content = params.get("content", "")
                    note_title = params.get("title", "")
                    if content or note_title:
                        saved_note = self.parent_window.add_note_from_ai(content, title=note_title)
                        if saved_note:
                            action_created_notes.append((note_title, content))
                elif act_name == "start_task":
                    task_title = params.get("title") or self.last_created_task
                    if task_title:
                        self.parent_window.start_task_by_title(task_title)
                        self.last_created_task = None

        # Build fallback chat response if LLM chat_response is missing, empty, or placeholder
        invalid_placeholders = ["", "natural response text", "chat_response", "YOUR COMPLETE HELPFUL CHAT MESSAGE HERE", "YOUR FULL COMPLETE HELPFUL CHAT MESSAGE HERE"]
        if not chat_response or chat_response in invalid_placeholders:
            response_parts = []
            if action_created_tasks:
                task_list_str = ", ".join([f"**{t}**" for t in action_created_tasks])
                response_parts.append(f"Got it! I've added {task_list_str} to your tasks.\nWant to start working on it now?")
            
            if action_created_notes:
                for n_title, n_content in action_created_notes:
                    if n_content and len(n_content) > 30:
                        response_parts.append(f"{n_content}\n\nI've also saved this research as a note in Ticky. 📝")
                    else:
                        response_parts.append("Saved it as a note in Ticky. 📝")
            
            if response_parts:
                chat_response = "\n\n".join(response_parts)
            else:
                chat_response = text

        if action_created_tasks and not created_task_title:
            created_task_title = action_created_tasks[0]
            show_start = True

        action_buttons = []
        if show_start or created_task_title or len(action_created_tasks) > 0:
            target_task = created_task_title or (action_created_tasks[0] if action_created_tasks else self.last_created_task)
            if target_task:
                action_buttons = [
                    {
                        "label": "🚀 Start Task",
                        "callback": lambda checked=False, t=target_task: self.handle_start_task_click(t)
                    },
                    {
                        "label": "Not now",
                        "callback": self.handle_not_now_click
                    }
                ]

        self.add_bubble(chat_response, is_user=False, action_buttons=action_buttons)

    def handle_start_task_click(self, task_title):
        if self.parent_window:
            self.parent_window.start_task_by_title(task_title)
            self.add_bubble(f"Starting **{task_title}** now! 🚀", is_user=False)
            self.last_created_task = None

    def handle_not_now_click(self):
        self.add_bubble("No problem! Let me know whenever you're ready.", is_user=False)

    def add_bubble(self, text, is_user=True, action_buttons=None):
        bubble = ChatBubble(text, is_user, self, action_buttons=action_buttons)
        self.chat_layout.addWidget(bubble)
        QTimer.singleShot(20, lambda: self.update_panel_height(animate=True))
        self.scroll_to_bottom()

    def clear_chat(self):
        self.has_messages = False
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                self.chat_layout.removeWidget(widget)
                widget.deleteLater()

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))
