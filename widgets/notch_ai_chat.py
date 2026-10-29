# widgets/notch_ai_chat.py
"""
Mini AI Chat widget integrated inside the Ticky Notch.
Provides:
- Scrollable message history with rich bubbles & action buttons (Start Task, Save Note)
- Input bar with send button
- Voice input button with speech-to-text recording and transcription
- Directly utilizes user's configured AI provider, model, and credentials from Settings.
"""

import os
import sys
import json
import re
import base64
import tempfile
import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QScrollArea, QFrame, QPushButton, QSizePolicy, QPlainTextEdit,
    QApplication
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QUrl, QSize, QPropertyAnimation, QEasingCurve, QRectF
from PySide6.QtGui import (
    QColor, QFont, QCursor, QPainter, QPainterPath, QPen, QBrush,
    QPixmap, QIcon, QFontMetrics, QTextDocument
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtMultimedia import QMediaCaptureSession, QAudioInput, QMediaRecorder

from utils import config
from styles import theme
from widgets.ai_panel import AIWorker, SYSTEM_PROMPT

# SVG Icons
SEND_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24">
<path d="M13 18V9.91l3.29 3.3 1.42-1.42L12 6.09l-5.71 5.7 1.42 1.42L11 9.91V18z"></path>
</svg>"""

MIC_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1-9c0-.55.45-1 1-1s1 .45 1 1v6c0 .55-.45 1-1 1s-1-.45-1-1V5zm6 6c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-2.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>"""

MIC_RECORDING_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M12 14c1.66 0 2.99-1.34 2.99-3L15 5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.48 6-3.3 6-6.72h-1.7z"/><circle cx="12" cy="7.5" r="2.5"/></svg>"""

COPY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="M20 2H10c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2m0 12H10V4h10z"></path><path d="M14 20H4V10h2V8H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2v-2h-2z"></path></svg>"""

CHECK_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="COLOR_PLACEHOLDER" viewBox="0 0 24 24"><path d="m10 15.586-3.293-3.293-1.414 1.414L10 18.414l9.707-9.707-1.414-1.414z"></path></svg>"""


class VoiceTranscribeWorker(QThread):
    """Background worker that transcribes an audio file via Whisper or Gemini, with Windows speech fallback."""
    finished = Signal(bool, str)

    def __init__(self, audio_file_path, provider, api_key):
        super().__init__()
        self.audio_file_path = audio_file_path
        self.provider = (provider or "gemini").lower().strip()
        self.api_key = (api_key or "").strip()

    def run(self):
        if not os.path.exists(self.audio_file_path) or os.path.getsize(self.audio_file_path) == 0:
            self.finished.emit(False, "Audio recording is empty or not found.")
            return

        # 1. If Groq API key is set or selected, use ultra-fast Groq Whisper
        if self.provider == "groq" or self.api_key.startswith("gsk_"):
            try:
                url = "https://api.groq.com/openai/v1/audio/transcriptions"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                with open(self.audio_file_path, "rb") as f:
                    files = {"file": (os.path.basename(self.audio_file_path), f, "audio/wav")}
                    data = {"model": "whisper-large-v3"}
                    resp = requests.post(url, headers=headers, files=files, data=data, timeout=12)
                if resp.status_code == 200:
                    text = resp.json().get("text", "").strip()
                    if text:
                        self.finished.emit(True, text)
                        return
            except Exception as e:
                pass

        # 2. If OpenAI API key is set or selected, use OpenAI Whisper
        if self.provider == "openai" or self.api_key.startswith("sk-"):
            try:
                url = "https://api.openai.com/v1/audio/transcriptions"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                with open(self.audio_file_path, "rb") as f:
                    files = {"file": (os.path.basename(self.audio_file_path), f, "audio/wav")}
                    data = {"model": "whisper-1"}
                    resp = requests.post(url, headers=headers, files=files, data=data, timeout=12)
                if resp.status_code == 200:
                    text = resp.json().get("text", "").strip()
                    if text:
                        self.finished.emit(True, text)
                        return
            except Exception as e:
                pass

        # 3. If Gemini is configured, use Gemini audio multimodal transcription
        if (self.provider == "gemini" or self.api_key.startswith("AIzaSy")) and self.api_key:
            try:
                with open(self.audio_file_path, "rb") as f:
                    raw_bytes = f.read()
                b64_data = base64.b64encode(raw_bytes).decode("utf-8")
                model = config.load_ai_model("gemini-1.5-flash")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{
                        "parts": [
                            {"inline_data": {"mime_type": "audio/wav", "data": b64_data}},
                            {"text": "Transcribe the spoken words verbatim. Output ONLY the transcribed words without any timestamps, introductory text, or quotation marks."}
                        ]
                    }]
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=14)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if text:
                        self.finished.emit(True, text)
                        return
            except Exception as e:
                pass

        # 4. Fallback: Windows offline dictation check if available
        if sys.platform == "win32":
            try:
                import subprocess
                ps_script = f"""
Add-Type -AssemblyName System.Speech;
try {{
    $sre = New-Object System.Speech.Recognition.SpeechRecognitionEngine;
    $sre.SetInputToWaveFile('{self.audio_file_path.replace("'", "''")}');
    $sre.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar));
    $res = $sre.Recognize();
    if ($res -and $res.Text) {{ Write-Output $res.Text }}
}} catch {{}}
"""
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW
                )
                out, _ = proc.communicate(timeout=6)
                clean_res = out.strip()
                if clean_res:
                    self.finished.emit(True, clean_res)
                    return
            except Exception:
                pass

        if not self.api_key:
            self.finished.emit(False, "API key required for AI voice transcription. Please save your API key in Settings -> AI Chat.")
        else:
            self.finished.emit(False, "Could not transcribe audio. Please speak clearly and try again.")


def parse_markdown_code_blocks(text):
    """
    Parses a markdown string into sequential chunks:
    - ('text', plain_markdown_text)
    - ('code', language_str, code_body)
    """
    if not text:
        return [("text", "")]

    pattern = re.compile(r"```([a-zA-Z0-9_#\+\-\.]*)[ \t]*\r?\n?([\s\S]*?)```")
    chunks = []
    last_end = 0

    for match in pattern.finditer(text):
        start, end = match.span()
        if start > last_end:
            sub = text[last_end:start].strip()
            if sub:
                chunks.append(("text", sub))
        lang = match.group(1).strip() or "code"
        code = match.group(2).lstrip("\r\n").rstrip("\r\n")
        chunks.append(("code", lang, code))
        last_end = end

    if last_end < len(text):
        remaining = text[last_end:].strip()
        unclosed = re.match(r"^```([a-zA-Z0-9_#\+\-\.]*)[ \t]*\r?\n?([\s\S]*)$", remaining)
        if unclosed:
            lang = unclosed.group(1).strip() or "code"
            code = unclosed.group(2).lstrip("\r\n").rstrip("\r\n")
            chunks.append(("code", lang, code))
        elif remaining:
            chunks.append(("text", remaining))

    if not chunks:
        chunks.append(("text", text.strip()))

    return chunks


def markdown_to_rich_html(markdown_text, font_family="DM Sans", base_point_size=10.5, text_color=None):
    """
    Converts markdown text to rich HTML with properly scaled headings (h1, h2, h3),
    bold, italics, lists, and clear font hierarchy.
    """
    doc = QTextDocument()
    font = QFont()
    font.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
    font.setPointSizeF(base_point_size)
    doc.setDefaultFont(font)
    doc.setMarkdown(markdown_text)
    html = doc.toHtml()
    
    # Scale down headings so they don't look giant or overwhelming in the chat
    html = html.replace("font-size:xx-large;", "font-size:13pt; font-weight:700; margin-top:4px; margin-bottom:2px;")
    html = html.replace("font-size:x-large;", "font-size:12pt; font-weight:700; margin-top:3px; margin-bottom:2px;")
    html = html.replace("font-size:large;", "font-size:11pt; font-weight:700; margin-top:2px; margin-bottom:2px;")
    html = html.replace("margin-top:7px; margin-bottom:7px;", "margin-top:2px; margin-bottom:3px;")
    
    if text_color:
        html = html.replace('<body style="', f'<body style=" color:{text_color};')
    return html


class CodeCopyButton(QPushButton):
    """Sleek copy button with icon and checkmark feedback for code blocks."""
    def __init__(self, code_text, parent=None):
        super().__init__("Copy", parent)
        self.code_text = code_text
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(22)
        self._copied = False
        self.clicked.connect(self._copy_code)
        self._update_icon_and_style()

    def _copy_code(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.code_text)
            self._copied = True
            self.setText("Copied!")
            self._update_icon_and_style()
            QTimer.singleShot(1800, self._restore)

    def _restore(self):
        self._copied = False
        self.setText("Copy")
        self._update_icon_and_style()

    def _update_icon_and_style(self):
        font_family = config.load_font_family("DM Sans")
        size = 12
        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        if self._copied:
            svg_data = CHECK_SVG.replace("COLOR_PLACEHOLDER", theme.ACCENT_COLOR).encode("utf-8")
            text_color = theme.ACCENT_COLOR
            border_color = theme.ACCENT_COLOR
            bg_color = "rgba(255, 255, 255, 0.12)"
        else:
            svg_data = COPY_SVG.replace("COLOR_PLACEHOLDER", "rgba(255, 255, 255, 0.65)").encode("utf-8")
            text_color = "rgba(255, 255, 255, 0.70)"
            border_color = "rgba(255, 255, 255, 0.12)"
            bg_color = "rgba(255, 255, 255, 0.06)"

        renderer = QSvgRenderer(svg_data)
        renderer.render(p)
        p.end()
        self.setIcon(QIcon(pix))
        self.setIconSize(QSize(12, 12))

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 10px;
                font-weight: 600;
                padding: 1px 7px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.16);
                color: #FFFFFF;
            }}
        """)


class NotchCodeEdit(QPlainTextEdit):
    """Monospace code editor optimized for chat code blocks with passthrough vertical scrolling."""
    def __init__(self, code_text, parent_scroll=None, parent=None):
        super().__init__(parent)
        self.parent_scroll = parent_scroll
        self.setReadOnly(True)
        self.setPlainText(code_text)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)

        font = QFont()
        font.setFamilies(["Consolas", "Cascadia Code", "Fira Code", "Courier New", "monospace"])
        font.setPointSize(10.5)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

        fm = QFontMetrics(font)
        self.setTabStopDistance(fm.horizontalAdvance(" ") * 4)

        lines = code_text.splitlines() or [""]
        line_height = fm.lineSpacing()
        total_h = len(lines) * line_height + 14

        # Dynamically fit short snippets or cap with scrollbar for longer ones
        if total_h <= 140:
            self.setFixedHeight(max(28, total_h))
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        else:
            self.setFixedHeight(140)
            self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: transparent;
                color: #ECEFF4;
                border: none;
                outline: none;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
                padding: 6px 10px;
                selection-background-color: rgba(255, 255, 255, 0.22);
                selection-color: #FFFFFF;
            }
            QScrollBar:horizontal {
                border: none;
                background: transparent;
                height: 4px;
            }
            QScrollBar::handle:horizontal {
                background: rgba(255, 255, 255, 35);
                border-radius: 2px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar:vertical {
                border: none;
                background: transparent;
                width: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 35);
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def _find_parent_scroll(self):
        p = self.parent()
        while p:
            if isinstance(p, QScrollArea):
                return p
            p = p.parent()
        return None

    def wheelEvent(self, ev):
        vbar = self.verticalScrollBar()
        delta_y = ev.angleDelta().y()
        if delta_y != 0:
            if not vbar or vbar.maximum() == 0 or (delta_y > 0 and vbar.value() == 0) or (delta_y < 0 and vbar.value() == vbar.maximum()):
                parent_scroll = self.parent_scroll or self._find_parent_scroll()
                if parent_scroll:
                    parent_scroll.wheelEvent(ev)
                    return
        super().wheelEvent(ev)


class NotchCodeBlock(QFrame):
    """
    Sleek code block container:
    - Header with language title on left and dedicated Copy button on right
    - Monospace body with selection, syntax readability, and horizontal scrolling
    """
    def __init__(self, code_text, language="code", parent_scroll=None, parent=None):
        super().__init__(parent)
        self.code_text = code_text
        self.language = (language or "code").strip()
        self.setObjectName("NotchCodeBlock")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.setStyleSheet("""
            QFrame#NotchCodeBlock {
                background-color: rgba(14, 14, 18, 0.92);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 7px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = QFrame(self)
        header.setFixedHeight(27)
        header.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.07);
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 6, 0)
        header_layout.setSpacing(6)

        lbl_lang = QLabel(self.language.lower(), header)
        lbl_lang.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.50);
                font-family: 'Consolas', 'DM Sans', monospace;
                font-size: 10px;
                font-weight: 600;
                background: transparent;
                border: none;
            }
        """)
        header_layout.addWidget(lbl_lang)
        header_layout.addStretch(1)

        self.btn_copy = CodeCopyButton(code_text, header)
        header_layout.addWidget(self.btn_copy)

        layout.addWidget(header)

        # Code editor body
        self.editor = NotchCodeEdit(code_text, parent_scroll=parent_scroll, parent=self)
        layout.addWidget(self.editor)


class NotchChatBubble(QFrame):
    """Compact chat bubble styled specifically for the mini notch layout, supporting rich text, headings, and code blocks."""
    def __init__(self, text, is_user=True, parent=None, action_buttons=None, parent_scroll=None):
        super().__init__(parent)
        self.is_user = is_user
        self.raw_text = text
        self.parent_scroll = parent_scroll
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.text_labels = []  # List of tuples: (QLabel, raw_text_chunk)
        self.code_blocks = []

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 1, 0, 1)
        main_layout.setSpacing(6)

        font_family = config.load_font_family("DM Sans")

        if is_user:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(0)
            row_layout.addStretch(1)

            lbl = QLabel(self)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl.setOpenExternalLinks(True)
            lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

            font = QFont()
            font.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
            font.setPointSizeF(10.5)
            lbl.setFont(font)

            fm = QFontMetrics(font)
            raw_lines = text.splitlines() or [""]
            max_line_w = max(fm.horizontalAdvance(l) for l in raw_lines)
            padding_h = 24
            natural_w = max_line_w + padding_h + 8
            max_allowed_w = 340
            target_w = min(max_allowed_w, max(36, natural_w))
            lbl.setFixedWidth(target_w)

            row_layout.addWidget(lbl)
            main_layout.addLayout(row_layout)
            self.text_labels.append((lbl, text))
            self.lbl_text = lbl
        else:
            # Parse AI response into text chunks and code blocks
            chunks = parse_markdown_code_blocks(text)
            for chunk in chunks:
                chunk_type = chunk[0]
                if chunk_type == "text":
                    chunk_text = chunk[1]
                    lbl = QLabel(self)
                    lbl.setTextFormat(Qt.TextFormat.RichText)
                    lbl.setWordWrap(True)
                    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                    lbl.setOpenExternalLinks(True)
                    lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

                    font = QFont()
                    font.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
                    font.setPointSizeF(10.5)
                    lbl.setFont(font)

                    main_layout.addWidget(lbl)
                    self.text_labels.append((lbl, chunk_text))
                elif chunk_type == "code":
                    lang = chunk[1]
                    code_content = chunk[2]
                    cb = NotchCodeBlock(code_content, language=lang, parent_scroll=self.parent_scroll, parent=self)
                    main_layout.addWidget(cb)
                    self.code_blocks.append(cb)

            self.lbl_text = self.text_labels[0][0] if self.text_labels else None

        # For every AI response (except temporary thinking bubble), provide action buttons and icon-only copy button
        if not is_user and text != "💭 *Thinking...*":
            footer_row = QHBoxLayout()
            footer_row.setContentsMargins(2, 2, 2, 1)
            footer_row.setSpacing(6)

            if action_buttons:
                for btn_info in action_buttons:
                    label = btn_info.get("label", "Action")
                    btn = QPushButton(label, self)
                    btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    is_primary = "start" in label.lower() or "yes" in label.lower() or "open" in label.lower()

                    if is_primary:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {theme.ACCENT_COLOR};
                                color: #FFFFFF;
                                border: none;
                                border-radius: 9px;
                                font-family: '{font_family}', 'Segoe UI', sans-serif;
                                font-size: 11px;
                                font-weight: 700;
                                padding: 3px 9px;
                            }}
                            QPushButton:hover {{
                                opacity: 0.9;
                            }}
                        """)
                    else:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: rgba(255, 255, 255, 14);
                                color: {theme.TEXT_PRIMARY};
                                border: 1px solid rgba(255, 255, 255, 24);
                                border-radius: 9px;
                                font-family: '{font_family}', 'Segoe UI', sans-serif;
                                font-size: 11px;
                                font-weight: 600;
                                padding: 3px 9px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 26);
                            }}
                        """)

                    cb = btn_info.get("callback")
                    if cb:
                        btn.clicked.connect(lambda checked=False, f=cb: f())
                    footer_row.addWidget(btn)

            footer_row.addStretch(1)

            # Icon-only copy button for entire message
            self.btn_copy = NotchIconButton(COPY_SVG, "Copy response", self, icon_size=13.0)
            self.btn_copy.setFixedSize(22, 22)
            self.btn_copy.clicked.connect(self._copy_message)
            footer_row.addWidget(self.btn_copy)

            main_layout.addLayout(footer_row)

        self.refresh_style()

    def _copy_message(self):
        """Copies entire message text to system clipboard with visual checkmark feedback."""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.raw_text)
            if hasattr(self, "btn_copy") and self.btn_copy:
                self.btn_copy.set_svg(CHECK_SVG)
                self.btn_copy.setToolTip("Copied!")
                QTimer.singleShot(1500, self._restore_copy_icon)

    def _restore_copy_icon(self):
        if hasattr(self, "btn_copy") and self.btn_copy:
            self.btn_copy.set_svg(COPY_SVG)
            self.btn_copy.setToolTip("Copy response")

    def refresh_style(self):
        font_family = config.load_font_family("DM Sans")
        if self.is_user:
            bg = theme.ACCENT_COLOR
            border = "none"
            text_color = "#FFFFFF"
            corners = "border-radius: 12px;"
            padding = "8px 12px"
        else:
            # ChatGPT style: Direct transparent response without a message box
            bg = "transparent"
            border = "none"
            text_color = theme.TEXT_PRIMARY
            corners = "border-radius: 0px;"
            padding = "2px 2px"

        for lbl, raw_chunk in self.text_labels:
            font = QFont()
            font.setFamilies([font_family, "Segoe UI", "Arial", "sans-serif"])
            font.setPointSizeF(10.5)
            lbl.setFont(font)

            html = markdown_to_rich_html(raw_chunk, font_family=font_family, base_point_size=10.5, text_color=text_color)
            if self.is_user:
                html = html.replace("margin-top:7px;", "margin-top:0px;").replace("margin-bottom:7px;", "margin-bottom:0px;")
            lbl.setText(html)
            lbl.setStyleSheet(f"""
                QLabel {{
                    color: {text_color};
                    background-color: {bg};
                    border: {border};
                    {corners}
                    padding: {padding};
                }}
            """)


class NotchSendButton(QPushButton):
    """Circular send button surrounded by a circle, disabled when input is empty."""
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setToolTip("Send message")
        self.setFixedSize(28, 28)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setEnabled(False)
        self._hover = False

    def enterEvent(self, e):
        if self.isEnabled():
            self._hover = True
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def changeEvent(self, e):
        if e.type() == e.Type.EnabledChange:
            if self.isEnabled():
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self._hover = False
            self.update()
        super().changeEvent(e)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        r = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)

        if not self.isEnabled():
            bg = QColor(255, 255, 255, 14)
            col_name = "rgba(255, 255, 255, 0.28)"
        else:
            if self._hover:
                bg = QColor(theme.ACCENT_COLOR).lighter(112)
            else:
                bg = QColor(theme.ACCENT_COLOR)
            col_name = "#FFFFFF"

        # Surrounding circle
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(r)

        # Render upward arrow Boxicons icon inside circle
        colored_svg = SEND_SVG.replace("COLOR_PLACEHOLDER", col_name)
        renderer = QSvgRenderer(colored_svg.encode("utf-8"))
        icon_size = 17.0
        ix = (self.width() - icon_size) / 2.0
        iy = (self.height() - icon_size) / 2.0
        renderer.render(painter, QRectF(ix, iy, icon_size, icon_size))


class NotchIconButton(QPushButton):
    """Compact vector SVG button for Voice, Send, and Copy actions."""
    def __init__(self, svg_template, tooltip="", parent=None, icon_size=None):
        super().__init__("", parent)
        self.svg_template = svg_template
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(28, 28)
        self.icon_size = icon_size
        self._hover = False
        self._active = False

    def setActive(self, val):
        self._active = val
        self.update()

    def set_svg(self, svg_template):
        self.svg_template = svg_template
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)

        if self._active:
            bg = QColor(255, 69, 58, 200)  # Glowing recording red or accent
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(r, 8, 8)
            col_name = "#FFFFFF"
        elif self._hover:
            bg = QColor(theme.HOVER_COLOR)
            bg.setAlpha(160)
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(r, 8, 8)
            col_name = theme.ACCENT_COLOR
        else:
            col_name = theme.TEXT_SECONDARY

        colored_svg = self.svg_template.replace("COLOR_PLACEHOLDER", col_name)
        renderer = QSvgRenderer(colored_svg.encode("utf-8"))
        size = self.icon_size if self.icon_size is not None else min(17.0, float(min(self.width(), self.height())) - 8.0)
        ix = (self.width() - size) / 2.0
        iy = (self.height() - size) / 2.0
        renderer.render(painter, QRectF(ix, iy, size, size))


class NotchMiniAIChat(QWidget):
    """
    Mini AI Chat interface inside the Notch Widget.
    Contains scrollable messages and the bottom input bar with Send and Voice buttons.
    """
    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self.main_window = getattr(notch_widget, "main_window", None)

        self.active_worker = None
        self.voice_worker = None
        self.is_recording = False
        self.recording_path = None
        self.last_created_task = None
        self.has_messages = False

        self._init_audio_capture()
        self._init_ui()

    def _init_audio_capture(self):
        """Setup PySide6 QtMultimedia audio recorder for voice input."""
        try:
            self.capture_session = QMediaCaptureSession(self)
            self.audio_input = QAudioInput(self)
            self.capture_session.setAudioInput(self.audio_input)
            self.media_recorder = QMediaRecorder(self)
            self.capture_session.setRecorder(self.media_recorder)
        except Exception as e:
            self.capture_session = None
            self.audio_input = None
            self.media_recorder = None

        self.voice_max_timer = QTimer(self)
        self.voice_max_timer.setSingleShot(True)
        self.voice_max_timer.setInterval(15000)  # Max 15s recording
        self.voice_max_timer.timeout.connect(self.stop_voice_recording)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 1. Scrollable Messages Area
        self.scroll = QScrollArea(self)
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
                background: rgba(255, 255, 255, 45);
                border-radius: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background: transparent;")
        self.chat_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setContentsMargins(4, 2, 4, 2)
        self.chat_layout.setSpacing(6)
        self.chat_layout.addStretch(1)

        self.scroll.setWidget(self.chat_content)
        def on_scroll_wheel(ev):
            bar = self.scroll.verticalScrollBar()
            if bar:
                delta = ev.angleDelta().y()
                bar.setValue(bar.value() - delta)
            ev.accept()
        self.scroll.wheelEvent = on_scroll_wheel
        self.scroll.viewport().wheelEvent = on_scroll_wheel
        layout.addWidget(self.scroll, 1)

        # 2. Bottom Input Bar Capsule Container
        self.input_card = QFrame(self)
        self.input_card.setObjectName("NotchInputCard")
        self.input_card.setFixedHeight(36)
        self.input_card.setStyleSheet("""
            QFrame#NotchInputCard {
                background-color: rgba(255, 255, 255, 14);
                border: 1px solid rgba(255, 255, 255, 26);
                border-radius: 18px;
            }
        """)

        input_layout = QHBoxLayout(self.input_card)
        input_layout.setContentsMargins(6, 3, 6, 3)
        input_layout.setSpacing(6)

        # Voice Input Button (New)
        self.btn_voice = NotchIconButton(MIC_SVG, "Voice Input (Click to speak)", self.input_card)
        self.btn_voice.clicked.connect(self.toggle_voice_recording)

        # Input Text Field
        font_family = config.load_font_family("DM Sans")
        self.input_field = QLineEdit(self.input_card)
        self.input_field.setPlaceholderText("Ask Ticky AI or say a task/note...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}', 'Segoe UI', sans-serif;
                font-size: 13.5px;
                padding: 0px 4px;
            }}
        """)
        self.input_field.returnPressed.connect(self.send_message)
        self.input_field.textChanged.connect(self._on_input_text_changed)
        orig_key_press = self.input_field.keyPressEvent
        def on_input_key(ev):
            if ev.key() == Qt.Key.Key_Escape:
                if self.notch and hasattr(self.notch, "collapse_ai_chat"):
                    self.notch.collapse_ai_chat()
                    return
            orig_key_press(ev)
        self.input_field.keyPressEvent = on_input_key

        # Send Button (Circle surround, disabled when empty)
        self.btn_send = NotchSendButton(self.input_card)
        self.btn_send.clicked.connect(self.send_message)

        input_layout.addWidget(self.btn_voice)
        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.btn_send)

        layout.addWidget(self.input_card)

        # Initial Welcome Greeting
        self.add_bubble("👋 Hi! I'm Ticky AI. Ask me anything, or speak a task/note.", is_user=False)

    def _on_input_text_changed(self, text):
        """Enable send button only when input contains non-whitespace text."""
        if hasattr(self, "btn_send") and self.btn_send:
            self.btn_send.setEnabled(bool(text.strip()))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.notch and hasattr(self.notch, "collapse_ai_chat"):
                self.notch.collapse_ai_chat()
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        if hasattr(self, "scroll") and self.scroll:
            bar = self.scroll.verticalScrollBar()
            if bar:
                delta = event.angleDelta().y()
                bar.setValue(bar.value() - delta)
        event.accept()

    def add_bubble(self, text, is_user=True, action_buttons=None):
        """Append a message bubble to the chat list."""
        self.has_messages = True
        bubble = NotchChatBubble(text, is_user=is_user, parent=self.chat_content, action_buttons=action_buttons, parent_scroll=self.scroll)
        self.chat_layout.addWidget(bubble)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        QTimer.singleShot(40, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()
        ))

    def toggle_voice_recording(self):
        """Toggle recording microphone audio for voice transcription."""
        if self.is_recording:
            self.stop_voice_recording()
        else:
            self.start_voice_recording()

    def start_voice_recording(self):
        """Start microphone capture."""
        if not self.media_recorder:
            self.input_field.setPlaceholderText("⚠️ Audio recording not supported on this device.")
            return

        self.is_recording = True
        self.btn_voice.setActive(True)
        self.btn_voice.set_svg(MIC_RECORDING_SVG)
        self.btn_voice.setToolTip("Listening... Click to stop")
        self.input_field.setPlaceholderText("Listening... Speak now 🎙 (click mic to stop)")

        # Notify notch for attentive eye animation
        if hasattr(self.notch, "set_ai_listening_state"):
            self.notch.set_ai_listening_state(True)

        temp_dir = tempfile.gettempdir()
        self.recording_path = os.path.join(temp_dir, "ticky_voice_recording.wav")
        if os.path.exists(self.recording_path):
            try:
                os.remove(self.recording_path)
            except Exception:
                pass

        self.media_recorder.setOutputLocation(QUrl.fromLocalFile(self.recording_path))
        self.media_recorder.record()
        self.voice_max_timer.start()

    def stop_voice_recording(self):
        """Stop microphone capture and launch background transcription worker."""
        if not self.is_recording:
            return

        self.is_recording = False
        self.voice_max_timer.stop()
        self.btn_voice.setActive(False)
        self.btn_voice.set_svg(MIC_SVG)
        self.btn_voice.setToolTip("Voice Input (Click to speak)")
        self.input_field.setPlaceholderText("Transcribing voice audio... ⏳")

        # Restore notch eyes
        if hasattr(self.notch, "set_ai_listening_state"):
            self.notch.set_ai_listening_state(False)

        if self.media_recorder:
            self.media_recorder.stop()

        # Slight pause to let media recorder flush file to disk
        QTimer.singleShot(300, self._launch_voice_transcription)

    def _launch_voice_transcription(self):
        if not self.recording_path or not os.path.exists(self.recording_path):
            self.input_field.setPlaceholderText("Ask Ticky AI or say a task/note...")
            return

        provider = config.load_ai_provider()
        api_key = config.load_ai_api_key()

        self.voice_worker = VoiceTranscribeWorker(self.recording_path, provider, api_key)
        self.voice_worker.finished.connect(self._on_voice_transcription_finished)
        self.voice_worker.start()

    def _on_voice_transcription_finished(self, success, text):
        self.input_field.setPlaceholderText("Ask Ticky AI or say a task/note...")
        if success and text:
            # Place recognized voice directly into input bar for user review / instant sending
            self.input_field.setText(text)
            self.input_field.setFocus()
        else:
            if "API key required" in text:
                self.add_bubble("⚠️ API Key needed for voice transcription.\nPlease configure in Settings -> AI Chat tab.",
                                is_user=False,
                                action_buttons=[{"label": "⚙️ Open Settings", "callback": self.open_settings}])
            else:
                self.input_field.setPlaceholderText("Could not detect speech. Try again.")

    def send_message(self):
        prompt = self.input_field.text().strip()
        if not prompt:
            return

        # Affirmative fast-response for created task
        prompt_lower = prompt.lower()
        start_keywords = ["yes", "start", "start it", "let's do it", "lets do it", "do it", "sure", "work on it"]
        if self.last_created_task and prompt_lower in start_keywords:
            target = self.last_created_task
            self.last_created_task = None
            self.add_bubble(prompt, is_user=True)
            self.input_field.clear()
            self._start_task_in_notch(target)
            return

        self.add_bubble(prompt, is_user=True)
        self.input_field.clear()

        # Check credentials from settings
        provider = config.load_ai_provider()
        model = config.load_ai_model()
        api_key = config.load_ai_api_key()

        if not api_key:
            self.add_bubble(
                "⚠️ **API Key not set!**\nPlease save your API key in Settings -> AI Chat tab to use Ticky AI.",
                is_user=False,
                action_buttons=[{"label": "⚙️ Open Settings", "callback": self.open_settings}]
            )
            return

        # Validate mismatch
        if api_key.startswith("gsk_") and provider.lower() != "groq":
            self.add_bubble(f"⚠️ **API Key Mismatch!** Your key starts with `gsk_` (Groq), but the selected provider is `{provider}`. Please switch to Groq in Settings.",
                            is_user=False, action_buttons=[{"label": "⚙️ Open Settings", "callback": self.open_settings}])
            return
        elif api_key.startswith("AIzaSy") and provider.lower() != "gemini":
            self.add_bubble(f"⚠️ **API Key Mismatch!** Your key starts with `AIzaSy` (Gemini), but provider is `{provider}`.",
                            is_user=False, action_buttons=[{"label": "⚙️ Open Settings", "callback": self.open_settings}])
            return

        # Add thinking bubble and alert notch eyes
        self.thinking_bubble = NotchChatBubble("💭 *Thinking...*", is_user=False, parent=self.chat_content, parent_scroll=self.scroll)
        self.chat_layout.addWidget(self.thinking_bubble)
        self.scroll_to_bottom()

        if hasattr(self.notch, "set_ai_thinking_state"):
            self.notch.set_ai_thinking_state(True)

        self.btn_send.setEnabled(False)
        self.input_field.setEnabled(False)

        self.active_worker = AIWorker(provider, model, api_key, prompt)
        self.active_worker.finished.connect(self._on_ai_response)
        self.active_worker.start()

    def _on_ai_response(self, success, text):
        if hasattr(self, "thinking_bubble") and self.thinking_bubble:
            self.chat_layout.removeWidget(self.thinking_bubble)
            self.thinking_bubble.deleteLater()
            self.thinking_bubble = None

        if hasattr(self.notch, "set_ai_thinking_state"):
            self.notch.set_ai_thinking_state(False)

        self.btn_send.setEnabled(True)
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

        if not success:
            if hasattr(self.notch, "trigger_ai_response_expression"):
                self.notch.trigger_ai_response_expression(success=False)
            self.add_bubble(f"⚠️ Error: {text}", is_user=False)
            return

        if hasattr(self.notch, "trigger_ai_response_expression"):
            self.notch.trigger_ai_response_expression(success=True)

        actions, chat_response, show_start, created_task_title = self._parse_ai_response(text)

        action_created_tasks = []
        action_created_notes = []

        if actions:
            for act in actions:
                act_name = act.get("name")
                params = act.get("params", {})
                if act_name == "create_task":
                    title = params.get("title")
                    if title:
                        due = params.get("due_date")
                        prio = params.get("priority")
                        full_title = self._create_task(title, due, prio)
                        if full_title:
                            action_created_tasks.append(full_title)
                            self.last_created_task = full_title
                elif act_name == "create_note":
                    content = params.get("content", "")
                    note_title = params.get("title", "")
                    if content or note_title:
                        saved = self._create_note(content, note_title)
                        if saved:
                            action_created_notes.append((note_title, content))
                elif act_name == "start_task":
                    task_title = params.get("title") or self.last_created_task
                    if task_title:
                        self._start_task_in_notch(task_title)
                        self.last_created_task = None

        # Build fallback chat response if necessary
        invalid_placeholders = ["", "natural response text", "chat_response", "YOUR COMPLETE HELPFUL CHAT MESSAGE HERE", "YOUR FULL COMPLETE HELPFUL CHAT MESSAGE HERE"]
        if not chat_response or chat_response in invalid_placeholders:
            parts = []
            if action_created_tasks:
                t_str = ", ".join([f"**{t}**" for t in action_created_tasks])
                parts.append(f"Added {t_str} to your tasks.\nWant to start working on it now?")
            if action_created_notes:
                parts.append("Saved as a note in Ticky. 📝")
            chat_response = "\n\n".join(parts) if parts else text

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
                        "callback": lambda t=target_task: self._start_task_in_notch(t)
                    },
                    {
                        "label": "Not now",
                        "callback": lambda: self.add_bubble("No problem! Let me know when you're ready.", is_user=False)
                    }
                ]

        self.add_bubble(chat_response, is_user=False, action_buttons=action_buttons)

    def _create_task(self, title, due_date=None, priority=None):
        if self.main_window and hasattr(self.main_window, "add_task_from_ai"):
            return self.main_window.add_task_from_ai(title, due_date=due_date, priority=priority)
        else:
            full_title = title.strip()
            meta = []
            if due_date: meta.append(due_date.strip())
            if priority: meta.append(priority.strip().capitalize())
            if meta: full_title += f" ({', '.join(meta)})"
            tasks = config.load_tasks()
            if full_title not in tasks:
                tasks.insert(0, full_title)
                config.save_tasks(tasks)
            if self.notch and hasattr(self.notch, "pick_random_task"):
                self.notch.current_random_task = full_title
            return full_title

    def _create_note(self, content, title=None):
        if self.main_window and hasattr(self.main_window, "add_note_from_ai"):
            return self.main_window.add_note_from_ai(content, title=title)
        else:
            note_text = f"{title}\n{content}" if title and content else (content or title or "")
            notes = config.load_notes()
            if note_text and note_text not in notes:
                notes.insert(0, note_text)
                config.save_notes(notes)
            return note_text

    def _start_task_in_notch(self, task_title):
        """Switch the notch directly into focus timer mode for this task."""
        self.add_bubble(f"Starting focus session on **{task_title}**! 🚀", is_user=False)
        self.last_created_task = None
        if self.notch and hasattr(self.notch, "_start_task_from_notch_list"):
            self.notch.ai_chat_in_notch = False
            self.hide()
            self.notch._start_task_from_notch_list(task_title)

    def _parse_ai_response(self, text):
        clean_text = text.strip()
        if clean_text.startswith("```"):
            lines = clean_text.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            clean_text = "\n".join(lines).strip()

        try:
            data = json.loads(clean_text)
            if isinstance(data, dict):
                return (
                    data.get("actions", []),
                    str(data.get("chat_response") or "").strip(),
                    bool(data.get("show_start_button", False)),
                    str(data.get("created_task_title") or "").strip()
                )
        except Exception:
            pass

        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{[\s\S]*\"actions\"[\s\S]*\})", text)

        if json_match:
            try:
                data = json.loads(json_match.group(1).strip())
                if isinstance(data, dict):
                    text_outside = text.replace(json_match.group(0), "").strip()
                    return (
                        data.get("actions", []),
                        str(data.get("chat_response") or text_outside).strip(),
                        bool(data.get("show_start_button", False)),
                        str(data.get("created_task_title") or "").strip()
                    )
            except Exception:
                pass

        return [], text.strip(), False, ""

    def open_settings(self):
        """Open settings window directly to the AI Config tab."""
        if self.main_window and hasattr(self.main_window, "show_settings_menu"):
            self.main_window.show_settings_menu()
            if hasattr(self.main_window, "settings_window") and self.main_window.settings_window:
                self.main_window.settings_window.switch_page(4)
        else:
            from ui.settings_window import SettingsWindow
            sw = SettingsWindow()
            sw.show_centered()
            sw.switch_page(4)
