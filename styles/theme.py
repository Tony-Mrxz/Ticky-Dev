# styles/theme.py
"""Global theme constants for the Obsidian design system."""

from utils import config

# Obsidian Color Palette
BG_COLOR = "#0F1115"          # Deep matte black window background
MAIN_CARD_COLOR = "#171A21"   # Layer 2 card background
SEC_CARD_COLOR = "#202530"    # Layer 3 elevated card background / toolbar
HOVER_COLOR = "#272D38"       # Highlight hover state color
BORDER_COLOR = "rgba(255, 255, 255, 0.06)"  # 1px border highlight
ACCENT_COLOR = config.load_accent_color("#4CC2FF")      # Windows 11 accent blue
SUCCESS_COLOR = "#45D483"     # Active checkmark green
TEXT_PRIMARY = "#F2F4F8"      # Bright primary readability text
TEXT_SECONDARY = "#9AA3B2"    # Muted secondary typography text

# Vibrant Rainbow Colors for Tasks
RAINBOW_COLORS = [
    "#FF453A",  # Coral Red
    "#FF9F0A",  # Orange
    "#FFD60A",  # Yellow
    "#30D158",  # Green
    "#64D2FF",  # Cyan
    "#0A84FF",  # Blue
    "#BF5AF2",  # Violet
    "#FF375F",  # Pink
]



# Typography Guidelines
SELECTED_FONT = config.load_font_family("Inter")
FONT_FAMILY = f"{SELECTED_FONT}, Segoe UI Variable Display, Segoe UI, sans-serif"
HEADER_FONT_FAMILY = f"{SELECTED_FONT}, Space Grotesk, sans-serif"

def update_font_theme(font_name):
    """Update active font typography families dynamically at runtime."""
    global SELECTED_FONT, FONT_FAMILY, HEADER_FONT_FAMILY
    SELECTED_FONT = font_name
    FONT_FAMILY = f"{SELECTED_FONT}, Segoe UI Variable Display, Segoe UI, sans-serif"
    HEADER_FONT_FAMILY = f"{SELECTED_FONT}, Space Grotesk, sans-serif"

# Clock & Header Text
CLOCK_SIZE = 16
CLOCK_WEIGHT = config.load_clock_weight("700")   # "500" for Semibold, "700" for Bold
DATE_SIZE = 16
DATE_WEIGHT = "500"           # Medium / Normal

# Custom Clock & Drag Settings
USE_24H = config.load_use_24h(True)
SHOW_DATE = config.load_show_date(True)
PIN_POSITION = config.load_pin_position(False)
SHOW_SECONDS = config.load_show_seconds(True)
CLOCK_STYLE = config.load_clock_style("classic")   # classic | split | casio | minimal | neon
CLOCK_BOX_BG = config.load_clock_box_bg(False)    # Draw glass toolbar-style background box
STICK_ON_DESKTOP = config.load_stick_on_desktop(False)

# Tasks Typography
TASK_SIZE = config.load_task_font_size(13)
TASK_WEIGHT = "500"           # Medium weight
TASK_SPACING = "1.5"
