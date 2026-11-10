# widgets/notch_hardware.py
"""
Minimalist hardware monitor stage for the notch:
- TITLE AND USAGE (Live): CPU %, RAM %, Network Speed, GPU %.
- Top resource-consuming processes.
- Automatic polling suspension when closed (0% background CPU impact).
"""

from PySide6.QtCore import Qt, Signal, QByteArray, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer

from styles import theme
from utils import config
from utils.hardware_service import HardwareService
from utils.memreduct import is_memreduct_available, trigger_memreduct_clean

HARDWARE_NOTCH_WIDTH = 490
HARDWARE_NOTCH_HEIGHT = 112
HARDWARE_NOTCH_COMPACT_HEIGHT = 76


class MetricCard(QFrame):
    """Clean minimalist card displaying Title and Live Usage value with optional hover action."""
    clean_finished_signal = Signal(bool)

    def __init__(self, title: str, parent=None, action_callback=None, action_label="🧹 Clean"):
        super().__init__(parent)
        self.title_text = title
        self.raw_val_text = "--"
        self.action_callback = action_callback
        self.action_label = action_label
        self._action_enabled = action_callback is not None
        self._is_cleaning = False

        self.clean_finished_signal.connect(self._on_clean_finished)

        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        font_family = config.load_font_family("DM Sans")

        self.lbl_title = QLabel(title)
        self.lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_title.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-family: '{font_family}'; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; background: transparent; border: none;")

        self.lbl_val = QLabel("--")
        self.lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_val.setStyleSheet(f"color: #FFFFFF; font-family: '{font_family}'; font-size: 17px; font-weight: 800; background: transparent; border: none;")

        self.btn_action = QPushButton(action_label, self)
        self.btn_action.setFixedSize(68, 22)
        self.btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_action.setToolTip("Click to trigger Mem Reduct memory clean")
        self._apply_btn_style()
        self.btn_action.clicked.connect(self._on_action_clicked)
        self.btn_action.hide()

        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_val)
        layout.addWidget(self.btn_action, 0, Qt.AlignmentFlag.AlignCenter)

    def _apply_btn_style(self):
        font_family = config.load_font_family("DM Sans")
        accent = config.load_accent_color(theme.ACCENT_COLOR)
        self.btn_action.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.08);
                border: 1px solid {accent};
                border-radius: 6px;
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 9.5px;
                font-weight: 700;
                padding: 1px 4px;
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: {accent};
                opacity: 0.8;
            }}
        """)

    def set_action_enabled(self, enabled: bool):
        self._action_enabled = enabled
        if not enabled:
            self.btn_action.hide()
            self.lbl_val.show()
            self.lbl_title.setText(self.title_text)

    def set_value(self, text: str):
        self.raw_val_text = text
        self.lbl_val.setText(text)
        if self._action_enabled and self.btn_action.isVisible():
            self.lbl_title.setText(f"{self.title_text} {text}")

    def enterEvent(self, event):
        super().enterEvent(event)
        if self._action_enabled:
            self.lbl_val.hide()
            self.btn_action.show()
            self.lbl_title.setText(f"{self.title_text} {self.raw_val_text}")
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.16);
                    border-radius: 10px;
                }
            """)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self._action_enabled and not self._is_cleaning:
            self.btn_action.hide()
            self.lbl_val.show()
            self.lbl_title.setText(self.title_text)
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 10px;
                }
            """)

    def _on_action_clicked(self):
        if self._is_cleaning:
            return
        self._is_cleaning = True
        self.btn_action.setText("Cleaning...")
        self.btn_action.setEnabled(False)
        accent = config.load_accent_color(theme.ACCENT_COLOR)
        font_family = config.load_font_family("DM Sans")
        self.btn_action.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent};
                border: 1px solid {accent};
                border-radius: 6px;
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 9.5px;
                font-weight: 700;
                padding: 1px 4px;
            }}
        """)

        # Fallback safety timer: guarantees button never stays stuck even if subprocess hangs
        QTimer.singleShot(2200, lambda: self._on_clean_finished(True) if self._is_cleaning else None)

        def _on_done(success):
            self.clean_finished_signal.emit(success)

        if self.action_callback:
            self.action_callback(_on_done)
        else:
            self.clean_finished_signal.emit(True)

    def _on_clean_finished(self, success: bool):
        if not self._is_cleaning:
            return
        self.btn_action.setText("✓ Cleaned" if success else "Failed")

        def _restore():
            self._is_cleaning = False
            self.btn_action.setText(self.action_label)
            self.btn_action.setEnabled(True)
            self._apply_btn_style()
            if not self.underMouse():
                self.btn_action.hide()
                self.lbl_val.show()
                self.lbl_title.setText(self.title_text)
                self.setStyleSheet("""
                    QFrame {
                        background-color: rgba(255, 255, 255, 0.05);
                        border: 1px solid rgba(255, 255, 255, 0.08);
                        border-radius: 10px;
                    }
                """)

        QTimer.singleShot(1000, _restore)

    def wheelEvent(self, event):
        event.ignore()


class NotchHardwareWidget(QWidget):
    """
    Clean, live hardware monitor widget for Notch State 2.
    """
    closed = Signal()

    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self.service = HardwareService.get_instance()
        self.service.updated.connect(self._on_stats_updated)

        self._build_ui()

    def _build_ui(self):
        font_family = config.load_font_family("DM Sans")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 6, 10, 6)
        root_layout.setSpacing(10)

        # 1. Row of 4 Core Metrics: [CPU] [RAM] [NETWORK] [GPU]
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(8)
        metrics_row.setContentsMargins(0, 0, 0, 0)

        self.card_cpu = MetricCard("CPU", self)
        self.card_mem = MetricCard(
            "RAM", self,
            action_callback=lambda cb: trigger_memreduct_clean(cb),
            action_label="🧹 Clean"
        )
        self.card_net = MetricCard("NETWORK", self)
        self.card_gpu = MetricCard("GPU", self)

        metrics_row.addWidget(self.card_cpu, stretch=1)
        metrics_row.addWidget(self.card_mem, stretch=1)
        metrics_row.addWidget(self.card_net, stretch=1)
        metrics_row.addWidget(self.card_gpu, stretch=1)

        root_layout.addLayout(metrics_row)

        # 2. Bottom Row: Top Consumers Chip List
        self.procs_container = QWidget(self)
        procs_row = QHBoxLayout(self.procs_container)
        procs_row.setSpacing(8)
        procs_row.setContentsMargins(4, 0, 4, 0)

        lbl_procs_title = QLabel("TOP CONSUMERS:")
        lbl_procs_title.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-family: '{font_family}';
                font-size: 9.5px;
                font-weight: 700;
                letter-spacing: 0.6px;
                background: transparent;
            }}
        """)
        procs_row.addWidget(lbl_procs_title)

        self.lbl_proc_1 = QLabel("--")
        self.lbl_proc_2 = QLabel("--")
        self.lbl_proc_3 = QLabel("--")

        chip_style = f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}';
                font-size: 11px;
                font-weight: 600;
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 7px;
                padding: 3px 10px;
            }}
        """
        self.lbl_proc_1.setStyleSheet(chip_style)
        self.lbl_proc_2.setStyleSheet(chip_style)
        self.lbl_proc_3.setStyleSheet(chip_style)

        procs_row.addWidget(self.lbl_proc_1)
        procs_row.addWidget(self.lbl_proc_2)
        procs_row.addWidget(self.lbl_proc_3)
        procs_row.addStretch(1)

        root_layout.addWidget(self.procs_container)

    def showEvent(self, event):
        super().showEvent(event)
        self.card_mem.set_action_enabled(is_memreduct_available())
        show_top = config.load_hardware_show_top_consumers(False)
        self.procs_container.setVisible(show_top)
        self.service.start_monitoring()
        if self.service.cached_stats:
            self._render_stats(self.service.cached_stats)

    def hideEvent(self, event):
        super().hideEvent(event)
        self.service.stop_monitoring()

    def _on_stats_updated(self, data: dict):
        self._render_stats(data)

    def _render_stats(self, data: dict):
        # 1. CPU
        cpu = data.get("cpu", {})
        cpu_p = cpu.get("percent", 0.0)
        self.card_cpu.set_value(f"{cpu_p}%")

        # 2. RAM
        mem = data.get("memory", {})
        mem_p = mem.get("percent", 0.0)
        self.card_mem.set_value(f"{mem_p}%")

        # 3. Network Live Speed
        net = data.get("network", {})
        speed = net.get("speed_str", "0 B/s")
        self.card_net.set_value(speed)

        # 4. GPU Live Usage
        gpu = data.get("gpu", {})
        gpu_p = gpu.get("percent", 0.0)
        self.card_gpu.set_value(f"{gpu_p}%")

        # 5. Top Consumers (only render if visible / not explicitly hidden)
        if not self.procs_container.isHidden():
            top_procs = data.get("top_processes", [])
            labels = [self.lbl_proc_1, self.lbl_proc_2, self.lbl_proc_3]
            for idx, lbl in enumerate(labels):
                if idx < len(top_procs):
                    p = top_procs[idx]
                    p_name = p.get("name", "Proc")
                    if len(p_name) > 12:
                        p_name = p_name[:10] + "…"
                    lbl.setText(f"{p_name} {p.get('cpu_percent', 0)}%")
                    lbl.show()
                else:
                    lbl.hide()

    def wheelEvent(self, event):
        if self.notch and hasattr(self.notch, "wheelEvent"):
            self.notch.wheelEvent(event)
        else:
            event.ignore()
