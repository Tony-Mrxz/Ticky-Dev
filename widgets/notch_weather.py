# widgets/notch_weather.py
"""
Embedded weather dashboard stage for the notch:
Compact, glanceable view showing location, current temp, condition, humidity, wind, and High/Low.
"""

from PySide6.QtCore import Qt, Signal, QByteArray, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtGui import QPainter, QColor, QFont, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer

from styles import theme
from utils import config
from utils.weather_service import WeatherService, format_temp

WEATHER_NOTCH_WIDTH = 480
WEATHER_NOTCH_HEIGHT = 106

SUN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#FFB300">
<circle cx="12" cy="12" r="5"></circle>
<path d="M12 1v2m0 18v2M4.22 4.22l1.42 1.42m12.72 12.72 1.42 1.42M1 12h2m18 0h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" stroke="#FFB300" stroke-width="2" stroke-linecap="round"></path>
</svg>"""

CLOUD_SUN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
<path d="M12 2v2m-6.36 1.64 1.41 1.41M2 12h2m1.64 6.36 1.41-1.41" stroke="#FFB300" stroke-width="2" stroke-linecap="round"></path>
<path d="M8.5 7.5A4.5 4.5 0 0 1 13 12" stroke="#FFB300" stroke-width="2" stroke-linecap="round"></path>
<path d="M19.36 15.04A4.5 4.5 0 0 0 16 8a4.6 4.6 0 0 0-1.4.22A5.5 5.5 0 0 0 4 13.5 5.5 5.5 0 0 0 9.5 19H17a4.5 4.5 0 0 0 2.36-3.96Z" fill="#90A4AE" fill-opacity="0.9"></path>
</svg>"""

CLOUD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#90A4AE">
<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96Z"></path>
</svg>"""

RAIN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96Z" fill="#78909C"></path>
<path d="m8 19-2 4m6-4-2 4m6-4-2 4" stroke="#4FC3F7" stroke-width="2" stroke-linecap="round"></path>
</svg>"""

THUNDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96Z" fill="#546E7A"></path>
<path d="m13 14-3 5h3l-1 5 4-6h-3z" fill="#FFD54F" stroke="#FFD54F" stroke-width="1.5" stroke-linejoin="round"></path>
</svg>"""

SNOW_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none">
<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96Z" fill="#90A4AE"></path>
<circle cx="8" cy="20" r="1.5" fill="#E1F5FE"></circle>
<circle cx="12" cy="22" r="1.5" fill="#E1F5FE"></circle>
<circle cx="16" cy="20" r="1.5" fill="#E1F5FE"></circle>
</svg>"""

FOG_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="#B0BEC5">
<path d="M4 14h16v2H4zm-2 4h20v2H2zm4-8h12v2H6z" opacity="0.8"></path>
</svg>"""

REFRESH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="COLOR_PLACEHOLDER" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"></path>
</svg>"""

PIN_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="COLOR_PLACEHOLDER" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M12 2a8 8 0 0 0-8 8c0 5.25 8 12 8 12s8-6.75 8-12a8 8 0 0 0-8-8z"></path>
<circle cx="12" cy="10" r="3"></circle>
</svg>"""


def render_weather_pixmap(icon_key: str, size: int = 24) -> QPixmap:
    mapping = {
        "sun": SUN_SVG,
        "sun_cloud": CLOUD_SUN_SVG,
        "cloud_sun": CLOUD_SUN_SVG,
        "cloud": CLOUD_SVG,
        "drizzle": RAIN_SVG,
        "rain": RAIN_SVG,
        "heavy_rain": RAIN_SVG,
        "freezing_rain": RAIN_SVG,
        "thunder": THUNDER_SVG,
        "thunder_rain": THUNDER_SVG,
        "snow": SNOW_SVG,
        "heavy_snow": SNOW_SVG,
        "fog": FOG_SVG,
    }
    svg = mapping.get(icon_key, CLOUD_SUN_SVG)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()
    return pixmap


def render_svg_icon(svg_template: str, color: str, size: int = 12) -> QIcon:
    svg = svg_template.replace("COLOR_PLACEHOLDER", color)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class NotchWeatherWidget(QWidget):
    """
    Compact weather view for Notch State 2.
    """
    closed = Signal()

    def __init__(self, notch_widget, parent=None):
        super().__init__(parent)
        self.notch = notch_widget
        self.service = WeatherService.get_instance()
        self.service.updated.connect(self._on_weather_updated)
        self.service.error.connect(self._on_weather_error)

        self._weather_data = None
        self._build_ui()

    def _build_ui(self):
        font_family = config.load_font_family("DM Sans")
        accent_color = config.load_accent_color(theme.ACCENT_COLOR)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 6, 10, 6)
        root_layout.setSpacing(8)

        # 1. Header: [Pin + Location] [Condition Description] ... [Unit Toggle] [Refresh]
        header = QHBoxLayout()
        header.setSpacing(8)
        header.setContentsMargins(0, 0, 0, 0)

        pin_label = QLabel()
        pin_label.setPixmap(render_svg_icon(PIN_SVG, accent_color, 14).pixmap(14, 14))
        pin_label.setStyleSheet("background: transparent;")
        header.addWidget(pin_label)

        self.lbl_location = QLabel("Detecting location...")
        self.lbl_location.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 13px;
                font-weight: 700;
                background: transparent;
            }}
        """)
        header.addWidget(self.lbl_location)

        self.lbl_condition_header = QLabel("")
        self.lbl_condition_header.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-family: '{font_family}';
                font-size: 12px;
                font-weight: 500;
                background: transparent;
            }}
        """)
        header.addWidget(self.lbl_condition_header)

        header.addStretch(1)

        # Unit Toggle Button (°C / °F)
        current_unit = config.load_weather_unit("C")
        self.btn_unit = QPushButton(f"°{current_unit}")
        self.btn_unit.setFixedSize(28, 22)
        self.btn_unit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_unit.setToolTip("Toggle Celsius / Fahrenheit")
        self.btn_unit.clicked.connect(self._toggle_unit)
        self.btn_unit.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }}
        """)
        header.addWidget(self.btn_unit)

        # Refresh Button
        self.btn_refresh = QPushButton()
        self.btn_refresh.setFixedSize(24, 22)
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setToolTip("Refresh weather")
        self.btn_refresh.setIcon(render_svg_icon(REFRESH_SVG, theme.TEXT_SECONDARY, 12))
        self.btn_refresh.setIconSize(QSize(12, 12))
        self.btn_refresh.clicked.connect(self.refresh_weather)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.14);
            }
        """)
        header.addWidget(self.btn_refresh)

        root_layout.addLayout(header)

        # 2. Main Row: Free-flowing, seamless typography without disturbing rectangular boxes
        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        content_row.setContentsMargins(6, 4, 6, 2)

        # Left Hero Block: [Icon] [Big Temp] [Feels like / High-Low]
        hero_layout = QHBoxLayout()
        hero_layout.setSpacing(10)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        hero_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_hero_icon = QLabel()
        self.lbl_hero_icon.setFixedSize(32, 32)
        self.lbl_hero_icon.setStyleSheet("background: transparent; border: none;")
        hero_layout.addWidget(self.lbl_hero_icon)

        self.lbl_temp = QLabel("--°")
        self.lbl_temp.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 26px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)
        hero_layout.addWidget(self.lbl_temp)

        sub_temp_layout = QVBoxLayout()
        sub_temp_layout.setContentsMargins(4, 0, 0, 0)
        sub_temp_layout.setSpacing(2)
        sub_temp_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.lbl_feels_like = QLabel("Feels like --°")
        self.lbl_feels_like.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_PRIMARY};
                font-family: '{font_family}';
                font-size: 11.5px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
        self.lbl_high_low = QLabel("H: --°  L: --°")
        self.lbl_high_low.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-family: '{font_family}';
                font-size: 10.5px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        sub_temp_layout.addWidget(self.lbl_feels_like)
        sub_temp_layout.addWidget(self.lbl_high_low)
        hero_layout.addLayout(sub_temp_layout)

        content_row.addLayout(hero_layout, stretch=3)

        # Subtle Vertical Divider 1
        sep1 = QFrame()
        sep1.setFixedSize(1, 26)
        sep1.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); border: none;")
        content_row.addWidget(sep1, 0, Qt.AlignmentFlag.AlignVCenter)

        # Humidity Block (borderless, seamless)
        hum_layout = QVBoxLayout()
        hum_layout.setContentsMargins(0, 0, 0, 0)
        hum_layout.setSpacing(2)
        hum_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_hum_val = QLabel("--%")
        self.lbl_hum_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hum_val.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 15px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)
        lbl_hum_sub = QLabel("HUMIDITY")
        lbl_hum_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hum_sub.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-family: '{font_family}';
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.8px;
                background: transparent;
                border: none;
            }}
        """)
        hum_layout.addWidget(self.lbl_hum_val)
        hum_layout.addWidget(lbl_hum_sub)
        content_row.addLayout(hum_layout, stretch=1)

        # Subtle Vertical Divider 2
        sep2 = QFrame()
        sep2.setFixedSize(1, 26)
        sep2.setStyleSheet("background-color: rgba(255, 255, 255, 0.12); border: none;")
        content_row.addWidget(sep2, 0, Qt.AlignmentFlag.AlignVCenter)

        # Wind Block (borderless, seamless)
        wind_layout = QVBoxLayout()
        wind_layout.setContentsMargins(0, 0, 0, 0)
        wind_layout.setSpacing(2)
        wind_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_wind_val = QLabel("-- km/h")
        self.lbl_wind_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_wind_val.setStyleSheet(f"""
            QLabel {{
                color: #FFFFFF;
                font-family: '{font_family}';
                font-size: 15px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)
        lbl_wind_sub = QLabel("WIND")
        lbl_wind_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_wind_sub.setStyleSheet(f"""
            QLabel {{
                color: {theme.TEXT_SECONDARY};
                font-family: '{font_family}';
                font-size: 9px;
                font-weight: 700;
                letter-spacing: 0.8px;
                background: transparent;
                border: none;
            }}
        """)
        wind_layout.addWidget(self.lbl_wind_val)
        wind_layout.addWidget(lbl_wind_sub)
        content_row.addLayout(wind_layout, stretch=1)

        root_layout.addLayout(content_row)

    def showEvent(self, event):
        super().showEvent(event)
        cached = self.service.get_cached_weather()
        if cached:
            self._render_weather(cached)
        else:
            self.service.refresh(force=False)

    def refresh_weather(self):
        self.lbl_location.setText("Updating...")
        self.service.refresh(force=True)

    def _toggle_unit(self):
        curr = config.load_weather_unit("C")
        new_unit = "F" if curr == "C" else "C"
        config.save_weather_unit(new_unit)
        self.btn_unit.setText(f"°{new_unit}")
        if self._weather_data:
            self._render_weather(self._weather_data)

    def _on_weather_updated(self, data: dict):
        self._weather_data = data
        self._render_weather(data)

    def _on_weather_error(self, err_msg: str):
        self.lbl_location.setText("Weather Unavailable")
        self.lbl_condition_header.setText(f"Offline ({err_msg[:16]})")

    def _render_weather(self, data: dict):
        self._weather_data = data
        unit = config.load_weather_unit("C")
        city = data.get("city") or "My City"
        country = data.get("country") or ""
        loc_str = f"{city}, {country}" if country else city
        self.lbl_location.setText(loc_str)

        condition = data.get("condition") or "Clear"
        self.lbl_condition_header.setText(f"• {condition}")

        icon_key = data.get("icon", "sun")
        self.lbl_hero_icon.setPixmap(render_weather_pixmap(icon_key, size=28))
        self.lbl_temp.setText(format_temp(data.get("temp_c"), unit))

        feels = data.get("feels_like_c")
        self.lbl_feels_like.setText(f"Feels like {format_temp(feels, unit)}" if feels is not None else condition)

        temp_max = data.get("temp_max_c")
        temp_min = data.get("temp_min_c")
        if temp_max is not None and temp_min is not None:
            self.lbl_high_low.setText(f"H: {format_temp(temp_max, unit)}  L: {format_temp(temp_min, unit)}")

        humidity = data.get("humidity")
        self.lbl_hum_val.setText(f"{humidity}%" if humidity is not None else "--%")

        wind = data.get("wind_speed")
        self.lbl_wind_val.setText(f"{wind} km/h" if wind is not None else "--")

    def wheelEvent(self, event):
        if self.notch and hasattr(self.notch, "wheelEvent"):
            self.notch.wheelEvent(event)
        else:
            event.ignore()
