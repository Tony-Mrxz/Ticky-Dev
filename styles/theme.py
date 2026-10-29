# styles/theme.py
"""Global theme constants for the Obsidian design system."""

from utils import config

# ---------------------------------------------------------------------------
# Theme Definitions — each theme overrides the 5 background/surface colors.
# Accent color stays independent (user picks separately).
# ---------------------------------------------------------------------------
THEMES = {
    "Amoled Pure": {
        "bg":          "#000000",
        "main_card":   "#0D0D0D",
        "sec_card":    "#141414",
        "hover":       "#1A1A1A",
        "border":      "rgba(255, 255, 255, 0.05)",
    },
    "Obsidian": {
        "bg":          "#101318",
        "main_card":   "#181C23",
        "sec_card":    "#212630",
        "hover":       "#282E3A",
        "border":      "rgba(255, 255, 255, 0.06)",
    },
    "Monochrome": {
        "bg":          "#0B0B0C",
        "main_card":   "#16171A",
        "sec_card":    "#1F2124",
        "hover":       "#282A2E",
        "border":      "rgba(255, 255, 255, 0.07)",
    },
    "Midnight Blue": {
        "bg":          "#0A0F1A",
        "main_card":   "#121826",
        "sec_card":    "#192234",
        "hover":       "#202B40",
        "border":      "rgba(130, 175, 255, 0.07)",
    },
    "Arctic": {
        "bg":          "#070B10",
        "main_card":   "#0E151D",
        "sec_card":    "#15202A",
        "hover":       "#1C2937",
        "border":      "rgba(160, 225, 255, 0.09)",
    },
    "Deep Forest": {
        "bg":          "#0A120C",
        "main_card":   "#121C15",
        "sec_card":    "#19261D",
        "hover":       "#203026",
        "border":      "rgba(120, 205, 150, 0.07)",
    },
    "Ember": {
        "bg":          "#100D0A",
        "main_card":   "#191410",
        "sec_card":    "#221B15",
        "hover":       "#2B221B",
        "border":      "rgba(255, 185, 120, 0.08)",
    },
    "Crimson Noir": {
        "bg":          "#120A0B",
        "main_card":   "#1B1112",
        "sec_card":    "#241618",
        "hover":       "#2D1C1E",
        "border":      "rgba(255, 120, 120, 0.07)",
    },
    "Violet Dusk": {
        "bg":          "#0D0A18",
        "main_card":   "#161126",
        "sec_card":    "#1E1733",
        "hover":       "#261E40",
        "border":      "rgba(175, 130, 255, 0.07)",
    },
    "Cloud Light": {
        "bg":          "#EFF1F4",
        "main_card":   "#FFFFFF",
        "sec_card":    "#E7EAEF",
        "hover":       "#DDE1E8",
        "border":      "rgba(20, 24, 32, 0.10)",
        "text_primary":   "#1B1F27",
        "text_secondary": "#5C6472",
    },
}

# ---------------------------------------------------------------------------
# Active background / surface colors — initialised from saved theme
# ---------------------------------------------------------------------------
def _load_initial_theme():
    name = config.load_theme("Amoled Pure")
    return THEMES.get(name, THEMES["Amoled Pure"]), name

_initial_theme, _initial_name = _load_initial_theme()

BG_COLOR        = _initial_theme["bg"]
MAIN_CARD_COLOR = _initial_theme["main_card"]
SEC_CARD_COLOR  = _initial_theme["sec_card"]
HOVER_COLOR     = _initial_theme["hover"]
BORDER_COLOR    = _initial_theme["border"]
SELECTED_THEME  = _initial_name

# Accent & semantic colors (accent stays independent of the theme)
ACCENT_COLOR    = config.load_accent_color("#0A84FF")
SUCCESS_COLOR   = "#45D483"

# Dark themes keep near-white text; a light theme ships its own pair.
DARK_TEXT_PRIMARY   = "#F2F4F8"
DARK_TEXT_SECONDARY = "#9AA3B2"
TEXT_PRIMARY   = _initial_theme.get("text_primary", DARK_TEXT_PRIMARY)
TEXT_SECONDARY = _initial_theme.get("text_secondary", DARK_TEXT_SECONDARY)

# Accent presets shared by Settings and the first-run onboarding
ACCENT_PRESETS = [
    "#22D3EE",  # Cyan
    "#3D7BFD",  # Blue
    "#5E5CE6",  # Indigo
    "#BF5AF2",  # Violet
    "#FF6FB5",  # Pink
    "#FF7A5C",  # Coral
    "#FF453A",  # Red
    "#FF9F0A",  # Orange
    "#FFD60A",  # Yellow
    "#A3E635",  # Lime
    "#30D158",  # Green
    "#6EE7B7",  # Mint
    "#00C9A7",  # Teal
    "#E8EAED",  # Soft White
]

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
    global BG_COLOR, MAIN_CARD_COLOR, SEC_CARD_COLOR, HOVER_COLOR, BORDER_COLOR
    global TEXT_PRIMARY, TEXT_SECONDARY, SELECTED_THEME
    t = THEMES.get(theme_name, THEMES["Amoled Pure"])
    BG_COLOR        = t["bg"]
    MAIN_CARD_COLOR = t["main_card"]
    SEC_CARD_COLOR  = t["sec_card"]
    HOVER_COLOR     = t["hover"]
    BORDER_COLOR    = t["border"]
    TEXT_PRIMARY    = t.get("text_primary", DARK_TEXT_PRIMARY)
    TEXT_SECONDARY  = t.get("text_secondary", DARK_TEXT_SECONDARY)
    SELECTED_THEME  = theme_name
    config.save_theme(theme_name)


# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------
SELECTED_FONT       = config.load_font_family("DM Sans")
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
