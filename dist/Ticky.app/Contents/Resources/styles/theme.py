# styles/theme.py
"""Global theme constants for the Obsidian design system."""

from utils import config

# ---------------------------------------------------------------------------
# Theme Definitions — each theme overrides the 5 background/surface colors.
# Accent color stays independent (user picks separately).
# ---------------------------------------------------------------------------
THEMES = {
    "Obsidian": {
        "bg":          "#0F1115",
        "main_card":   "#171A21",
        "sec_card":    "#202530",
        "hover":       "#272D38",
        "border":      "rgba(255, 255, 255, 0.06)",
    },
    "Midnight Blue": {
        "bg":          "#080D1A",
        "main_card":   "#101727",
        "sec_card":    "#172035",
        "hover":       "#1E2A42",
        "border":      "rgba(100, 160, 255, 0.08)",
    },
    "Deep Forest": {
        "bg":          "#071008",
        "main_card":   "#0E1A10",
        "sec_card":    "#152419",
        "hover":       "#1C2E20",
        "border":      "rgba(80, 200, 120, 0.08)",
    },
    "Crimson Noir": {
        "bg":          "#110707",
        "main_card":   "#1A0C0C",
        "sec_card":    "#231212",
        "hover":       "#2C1818",
        "border":      "rgba(255, 80, 80, 0.08)",
    },
    "Violet Dusk": {
        "bg":          "#0B071A",
        "main_card":   "#140F28",
        "sec_card":    "#1E1636",
        "hover":       "#271E44",
        "border":      "rgba(160, 100, 255, 0.08)",
    },
    "Amoled Pure": {
        "bg":          "#000000",
        "main_card":   "#0D0D0D",
        "sec_card":    "#141414",
        "hover":       "#1A1A1A",
        "border":      "rgba(255, 255, 255, 0.05)",
    },
}

# ---------------------------------------------------------------------------
# Active background / surface colors — initialised from saved theme
# ---------------------------------------------------------------------------
def _load_initial_theme():
    name = config.load_theme("Obsidian")
    return THEMES.get(name, THEMES["Obsidian"]), name

_initial_theme, _initial_name = _load_initial_theme()

BG_COLOR        = _initial_theme["bg"]
MAIN_CARD_COLOR = _initial_theme["main_card"]
SEC_CARD_COLOR  = _initial_theme["sec_card"]
HOVER_COLOR     = _initial_theme["hover"]
BORDER_COLOR    = _initial_theme["border"]
SELECTED_THEME  = _initial_name

# Accent & semantic colors (independent of theme)
ACCENT_COLOR    = config.load_accent_color("#FF9F0A")
SUCCESS_COLOR   = "#45D483"
TEXT_PRIMARY    = "#F2F4F8"
TEXT_SECONDARY  = "#9AA3B2"

# Vibrant Rainbow Colors for task dots
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


def apply_theme(theme_name: str):
    """Switch all background/surface globals to the selected theme at runtime."""
    global BG_COLOR, MAIN_CARD_COLOR, SEC_CARD_COLOR, HOVER_COLOR, BORDER_COLOR, SELECTED_THEME
    t = THEMES.get(theme_name, THEMES["Obsidian"])
    BG_COLOR        = t["bg"]
    MAIN_CARD_COLOR = t["main_card"]
    SEC_CARD_COLOR  = t["sec_card"]
    HOVER_COLOR     = t["hover"]
    BORDER_COLOR    = t["border"]
    SELECTED_THEME  = theme_name
    config.save_theme(theme_name)


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
SELECTED_FONT       = config.load_font_family("Inter")
FONT_FAMILY         = f"{SELECTED_FONT}, Segoe UI Variable Display, Segoe UI, sans-serif"
HEADER_FONT_FAMILY  = f"{SELECTED_FONT}, Space Grotesk, sans-serif"

def update_font_theme(font_name):
    """Update active font typography families dynamically at runtime."""
    global SELECTED_FONT, FONT_FAMILY, HEADER_FONT_FAMILY
    SELECTED_FONT       = font_name
    FONT_FAMILY         = f"{SELECTED_FONT}, Segoe UI Variable Display, Segoe UI, sans-serif"
    HEADER_FONT_FAMILY  = f"{SELECTED_FONT}, Space Grotesk, sans-serif"

# Clock & Header Text
CLOCK_SIZE   = 16
CLOCK_WEIGHT = config.load_clock_weight("700")
DATE_SIZE    = 16
DATE_WEIGHT  = "500"

# Custom Clock & Drag Settings
USE_24H          = config.load_use_24h(True)
SHOW_DATE        = config.load_show_date(True)
PIN_POSITION     = config.load_pin_position(False)
SHOW_SECONDS     = config.load_show_seconds(True)
CLOCK_STYLE      = config.load_clock_style("neon")
CLOCK_BOX_BG     = config.load_clock_box_bg(False)
STICK_ON_DESKTOP = config.load_stick_on_desktop(False)

# Tasks Typography
TASK_SIZE    = config.load_task_font_size(13)
TASK_WEIGHT  = "500"
TASK_SPACING = "1.5"
