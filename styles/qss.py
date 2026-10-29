# styles/qss.py
"""Dynamic Qt StyleSheet templates using global theme tokens."""

from styles import theme

def get_main_style():
    return f"""
        QWidget#MainWindowContainer {{
            background-color: {theme.BG_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 20px;
        }}
    """

def get_clock_style():
    return f"""
        /* --- Classic / Minimal / Neon base time label --- */
        QLabel#ClockLabel {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: {theme.CLOCK_SIZE}px;
            font-weight: {theme.CLOCK_WEIGHT};
            background-color: transparent;
            border: none;
        }}
        QLabel#DateLabel {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 12px;
            font-weight: {theme.DATE_WEIGHT};
            background-color: transparent;
            border: none;
            letter-spacing: 0.5px;
        }}
        /* --- Casio / LED style labels --- */
        QLabel#CasioTimeLabel {{
            color: {theme.ACCENT_COLOR};
            font-family: "DSEG7 Classic";
            font-size: 20px;
            font-weight: 400;
            background-color: transparent;
            border: none;
            letter-spacing: 2px;
        }}
        QLabel#CasioDateLabel {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            background-color: transparent;
            border: none;
            letter-spacing: 2px;
        }}
        /* --- Neon style time label --- */
        QLabel#NeonClockLabel {{
            color: {theme.ACCENT_COLOR};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: {theme.CLOCK_SIZE}px;
            font-weight: {theme.CLOCK_WEIGHT};
            background-color: transparent;
            border: none;
        }}
    """

def get_task_card_style():
    return f"""
        QWidget#TaskCardContainer {{
            background-color: {theme.MAIN_CARD_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 12px;
        }}
        QLabel#TaskText {{
            font-family: {theme.FONT_FAMILY};
            font-size: {theme.TASK_SIZE}px;
            font-weight: {theme.TASK_WEIGHT};
            background-color: transparent;
            border: none;
        }}
        QPushButton#PlayTaskButton {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            font-size: 13px;
            font-weight: bold;
            border: none;
            padding: 0px;
            margin: 0px;
            width: 20px;
            height: 20px;
            min-width: 20px;
            min-height: 20px;
            max-width: 20px;
            max-height: 20px;
        }}
        QPushButton#PlayTaskButton:hover {{
            color: {theme.ACCENT_COLOR};
        }}
        QPushButton#PlayTaskButton[active="true"] {{
            color: #FF453A;
        }}
        QPushButton#PlayTaskButton[active="true"]:hover {{
            color: #FF6961;
        }}
    """

def get_toolbar_style():
    return f"""
        QWidget#ToolbarCapsule {{
            background-color: transparent;
            border: none;
        }}
        QPushButton#ToolbarButton {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            border: none;
            border-radius: 6px;
            font-size: 18px;
            min-width: 36px;
            min-height: 36px;
            max-width: 36px;
            max-height: 36px;
        }}
        QPushButton#StopwatchButton {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            border: none;
            border-radius: 6px;
            min-width: 36px;
            min-height: 36px;
            max-width: 36px;
            max-height: 36px;
        }}
        QLineEdit#StopwatchLabel, QLabel#StopwatchLabel {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 12px;
            font-weight: bold;
            background-color: transparent;
            border: none;
            padding: 0px;
            margin: 0px;
            min-width: 60px;
            max-width: 60px;
            selection-background-color: {theme.ACCENT_COLOR};
            selection-color: #FFFFFF;
        }}
    """

def get_header_add_button_style():
    return f"""
        QPushButton#HeaderAddTaskButton {{
            background-color: {theme.ACCENT_COLOR};
            color: #FFFFFF;
            border: none;
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 10px;
            font-weight: 800;
            letter-spacing: 0.5px;
            padding: 0px 14px;
            height: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QPushButton#HeaderAddTaskButton:hover {{
            background-color: {theme.TEXT_PRIMARY};
            color: {theme.SEC_CARD_COLOR};
        }}
    """

def get_pagination_style():
    return f"""
        QPushButton#PageButton {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            border: none;
            font-size: 14px;
            font-weight: bold;
            min-width: 24px;
            min-height: 24px;
        }}
        QPushButton#PageButton:hover {{
            color: {theme.TEXT_PRIMARY};
        }}
        QPushButton#PageButton:disabled {{
            color: rgba(255, 255, 255, 0.1);
        }}
        QLabel#PageIndicator {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            background-color: transparent;
        }}
    """

def get_settings_style():
    # Convert hex colors dynamically to translucent RGBA values
    accent_hex = theme.ACCENT_COLOR.lstrip('#')
    ar = int(accent_hex[0:2], 16)
    ag = int(accent_hex[2:4], 16)
    ab = int(accent_hex[4:6], 16)
    rgba_accent_bg = f"rgba({ar}, {ag}, {ab}, 0.1)"
    
    return f"""
        QWidget#SettingsWindowContainer {{
            background-color: {theme.BG_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 16px;
        }}
        QWidget#SettingsSidebar {{
            background-color: rgba(255, 255, 255, 0.015);
            border-right: 1px solid rgba(255, 255, 255, 0.04);
            border-top-left-radius: 15px;
            border-bottom-left-radius: 15px;
        }}
        QLabel#SidebarTitle {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 12px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            background-color: transparent;
            padding-left: 12px;
            padding-top: 4px;
            padding-bottom: 10px;
        }}
        QLineEdit#SidebarSearch {{
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 12px;
            padding: 4px 8px;
        }}
        QLineEdit#SidebarSearch:focus {{
            border: 1px solid {theme.ACCENT_COLOR};
            background-color: rgba(255, 255, 255, 0.08);
        }}
        QListWidget#SidebarSearchResults {{
            background-color: transparent;
            border: none;
            outline: none;
        }}
        QListWidget#SidebarSearchResults::item {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 12px;
            padding: 7px 10px;
            border-radius: 6px;
        }}
        QListWidget#SidebarSearchResults::item:hover {{
            background-color: {theme.HOVER_COLOR};
            color: {theme.TEXT_PRIMARY};
        }}
        QListWidget#SidebarSearchResults::item:selected {{
            background-color: {rgba_accent_bg};
            color: {theme.ACCENT_COLOR};
        }}
        QPushButton#SidebarButton {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            border: none;
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 13px;
            font-weight: 600;
            padding: 8px 12px;
            text-align: left;
            margin: 0px;
        }}
        QPushButton#SidebarButton:hover {{
            background-color: {theme.HOVER_COLOR};
            color: {theme.TEXT_PRIMARY};
        }}
        QPushButton#SidebarButton[active="true"] {{
            background-color: {rgba_accent_bg};
            color: {theme.ACCENT_COLOR};
            border-left: 3px solid {theme.ACCENT_COLOR};
            border-top-left-radius: 0px;
            border-bottom-left-radius: 0px;
            font-weight: 700;
            padding-left: 9px;
        }}
        QFrame#PageTitlePill {{
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 10px;
        }}
        QLabel#SettingsTitle {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 16px;
            font-weight: bold;
            background-color: transparent;
        }}
        QPushButton#SettingsCloseButton {{
            background-color: rgba(255, 255, 255, 0.04);
            color: {theme.TEXT_SECONDARY};
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 8px;
            font-size: 20px;
            font-weight: bold;
        }}
        QPushButton#SettingsCloseButton:hover {{
            background-color: rgba(255, 80, 80, 0.15);
            border: 1px solid rgba(255, 80, 80, 0.4);
            color: {theme.TEXT_PRIMARY};
        }}
        QLabel#SettingLabel {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 13px;
            font-weight: 600;
            background-color: transparent;
        }}
        QLabel#SettingLabel:disabled {{
            color: rgba(255, 255, 255, 0.25);
        }}
        QLabel#SettingDescription {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            background-color: transparent;
        }}
        QLabel#SettingDescription:disabled {{
            color: rgba(255, 255, 255, 0.15);
        }}
        QLabel#SettingSectionTitle {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background-color: transparent;
            padding-top: 8px;
            padding-bottom: 4px;
        }}
        QFrame#SettingSection {{
            background-color: {theme.MAIN_CARD_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 10px;
        }}
        QFrame#SettingRowDivider {{
            background-color: {theme.BORDER_COLOR};
            border: none;
            max-height: 1px;
        }}
        QWidget#CardsRow {{
            background: transparent;
        }}
        QWidget#ClockScrollContent {{
            background: transparent;
        }}
        QWidget#GeneralScrollContent {{
            background: transparent;
        }}
        QWidget#TasksScrollContent {{
            background: transparent;
        }}
        QWidget#SpotifyScrollContent {{
            background: transparent;
        }}
        QLineEdit#SpotifyInput {{
            background-color: {theme.MAIN_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 13px;
            padding: 6px 10px;
        }}
        QLineEdit#SpotifyInput:focus {{
            border: 1px solid {theme.ACCENT_COLOR};
        }}
        QSlider::groove:horizontal {{
            border: none;
            height: 4px;
            background: {theme.HOVER_COLOR};
            border-radius: 2px;
        }}
        QSlider::sub-page:horizontal {{
            background: {theme.ACCENT_COLOR};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {theme.TEXT_PRIMARY};
            border: none;
            width: 12px;
            height: 12px;
            margin: -4px 0;
            border-radius: 6px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {theme.ACCENT_COLOR};
        }}
        QPushButton#ExitButton {{
            background-color: rgba(255, 69, 58, 0.06);
            color: #FF453A;
            border: 1px solid rgba(255, 69, 58, 0.12);
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            height: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QPushButton#ExitButton:hover {{
            background-color: rgba(255, 69, 58, 0.12);
            border: 1px solid rgba(255, 69, 58, 0.22);
        }}
        QPushButton#FontItemButton {{
            background-color: {theme.MAIN_CARD_COLOR};
            color: {theme.TEXT_SECONDARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 6px;
            padding: 8px 12px;
            text-align: left;
        }}
        QPushButton#FontItemButton:hover {{
            background-color: {theme.HOVER_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        QPushButton#FontItemButton[active="true"] {{
            background-color: {rgba_accent_bg};
            border: 1px solid {theme.ACCENT_COLOR};
            color: {theme.TEXT_PRIMARY};
        }}
        QPushButton#ClockWeightButton {{
            background-color: {theme.SEC_CARD_COLOR};
            color: {theme.TEXT_SECONDARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            padding: 6px 14px;
        }}
        QPushButton#ClockWeightButton:hover {{
            background-color: {theme.HOVER_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        QPushButton#ClockWeightButton[active="true"] {{
            background-color: {rgba_accent_bg};
            border: 1px solid {theme.ACCENT_COLOR};
            color: {theme.ACCENT_COLOR};
        }}
        QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
            background: transparent;
            background-color: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 6px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.12);
            min-height: 20px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {theme.ACCENT_COLOR};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
            background-color: transparent;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 6px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: rgba(255, 255, 255, 0.12);
            min-width: 20px;
            border-radius: 3px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {theme.ACCENT_COLOR};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            border: none;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
            background-color: transparent;
        }}
    """

def get_spotify_panel_style():
    # Convert hex to RGBA with 60% opacity (152/255) to match toolbar glass background
    card_color = theme.SEC_CARD_COLOR.lstrip('#')
    r = int(card_color[0:2], 16)
    g = int(card_color[2:4], 16)
    b = int(card_color[4:6], 16)
    rgba_bg = f"rgba({r}, {g}, {b}, 0.6)"
    
    return f"""
        QWidget#SpotifyPanelContainer {{
            background-color: {rgba_bg};
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
        QLabel#SpotifySongTitle {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            font-weight: bold;
            background-color: transparent;
        }}
        QLabel#SpotifySongArtist {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 9px;
            background-color: transparent;
        }}
        QLabel#SpotifyTimeLabel {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 8px;
            background-color: transparent;
        }}
        QSlider#SpotifyTimeline::groove:horizontal {{
            border: none;
            height: 2px;
            background: {theme.HOVER_COLOR};
            border-radius: 1px;
        }}
        QSlider#SpotifyTimeline::sub-page:horizontal {{
            background: {theme.ACCENT_COLOR};
            border-radius: 1px;
        }}
        QSlider#SpotifyTimeline::handle:horizontal {{
            background: {theme.TEXT_PRIMARY};
            border: none;
            width: 6px;
            height: 6px;
            margin: -2px 0;
            border-radius: 3px;
        }}
        QSlider#SpotifyTimeline::handle:horizontal:hover {{
            background: {theme.ACCENT_COLOR};
        }}
    """

def get_clock_preview_card_style(weight=None):
    accent_hex = theme.ACCENT_COLOR.lstrip('#')
    ar = int(accent_hex[0:2], 16)
    ag = int(accent_hex[2:4], 16)
    ab = int(accent_hex[4:6], 16)
    rgba_accent = f"rgba({ar}, {ag}, {ab}, 0.12)"
    preview_weight = weight or theme.CLOCK_WEIGHT
    return f"""
        QWidget#ClockStyleCard {{
            background: transparent;
            border: none;
        }}
        QFrame#ClockStylePreview {{
            background-color: {theme.MAIN_CARD_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 8px;
        }}
        QFrame#ClockStylePreview:hover,
        QWidget#ClockStyleCard:hover QFrame#ClockStylePreview {{
            background-color: {theme.HOVER_COLOR};
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        QFrame#ClockStylePreview[active="true"] {{
            background-color: {rgba_accent};
            border: 1px solid {theme.ACCENT_COLOR};
        }}
        QLabel#CardPreviewTime {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 15px;
            font-weight: {preview_weight};
            background: transparent;
            border: none;
        }}
        QLabel#CardPreviewTimeCasio {{
            color: {theme.ACCENT_COLOR};
            font-family: "DSEG7 Classic";
            font-size: 14px;
            font-weight: 400;
            background: transparent;
            border: none;
        }}
        QLabel#CardPreviewTimeNeon {{
            color: {theme.ACCENT_COLOR};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 15px;
            font-weight: {preview_weight};
            background: transparent;
            border: none;
        }}
        QLabel#CardPreviewDate {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 7px;
            font-weight: 600;
            letter-spacing: 0.3px;
            background: transparent;
            border: none;
        }}
        QLabel#CardStyleName {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 0.3px;
            background: transparent;
            border: none;
        }}
        QWidget#ClockStyleCard:hover QLabel#CardStyleName {{
            color: {theme.TEXT_PRIMARY};
        }}
        QWidget#ClockStyleCard[active="true"] QLabel#CardStyleName {{
            color: {theme.ACCENT_COLOR};
        }}
    """


def get_appearance_style():
    """Styles for the Appearance page: theme preview cards and the custom accent controls."""
    return f"""
        QWidget#ThemeStyleCard {{
            background: transparent;
            border: none;
        }}
        QPushButton#ThemeStylePreview {{
            background: transparent;
            border: none;
        }}
        QLabel#ThemeStyleName {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 9px;
            font-weight: 600;
            letter-spacing: 0.2px;
            background: transparent;
            border: none;
        }}
        QLabel#ThemeStyleName[active="true"] {{
            color: {theme.ACCENT_COLOR};
            font-weight: 700;
        }}
        QLineEdit#AccentHexInput {{
            background-color: {theme.SEC_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            padding: 2px 8px;
        }}
        QLineEdit#AccentHexInput:focus {{
            border: 1px solid {theme.ACCENT_COLOR};
        }}
        QLineEdit#AccentHexInput[invalid="true"] {{
            border: 1px solid #FF453A;
        }}
        QPushButton#AccentHexApply {{
            background-color: {theme.SEC_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            font-weight: 600;
            padding: 2px 12px;
        }}
        QPushButton#AccentHexApply:hover {{
            background-color: {theme.HOVER_COLOR};
            border: 1px solid {theme.ACCENT_COLOR};
        }}
    """


def get_onboarding_style():
    """Styles for the first-run onboarding wizard (all four pages)."""
    return f"""
        QWidget#OnbRoot {{
            background: transparent;
        }}
        QFrame#OnbContainer {{
            background-color: {theme.BG_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 18px;
        }}
        QLabel#OnbWordmark {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 2.4px;
            background: transparent;
            border: none;
        }}
        QLabel#OnbTitle {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 34px;
            font-weight: 700;
            background: transparent;
            border: none;
        }}
        QLabel#OnbSubtitle {{
            color: {theme.ACCENT_COLOR};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 3.2px;
            background: transparent;
            border: none;
        }}
        QLabel#OnbHeading {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.HEADER_FONT_FAMILY};
            font-size: 21px;
            font-weight: 700;
            background: transparent;
            border: none;
        }}
        QLabel#OnbBody, QLabel#OnbFeature {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 12px;
            background: transparent;
            border: none;
        }}
        QLabel#OnbFeature {{
            color: {theme.TEXT_PRIMARY};
            font-size: 12px;
        }}
        QFrame#OnbSection {{
            background-color: {theme.MAIN_CARD_COLOR};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 12px;
        }}
        QLabel#OnbSectionTitle {{
            color: {theme.TEXT_PRIMARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 12px;
            font-weight: 700;
            background: transparent;
            border: none;
        }}
        QLabel#OnbSectionDesc {{
            color: {theme.TEXT_SECONDARY};
            font-family: {theme.FONT_FAMILY};
            font-size: 10px;
            background: transparent;
            border: none;
        }}
        QLabel#OnbHero {{
            background: transparent;
            border: none;
        }}
        QPushButton#OnbPrimary {{
            background-color: {theme.ACCENT_COLOR};
            color: #06080B;
            border: none;
            border-radius: 9px;
            font-family: {theme.FONT_FAMILY};
            font-size: 12px;
            font-weight: 700;
            padding: 9px 20px;
        }}
        QPushButton#OnbPrimary:hover {{
            background-color: {theme.ACCENT_COLOR};
            border: 1px solid rgba(255, 255, 255, 0.55);
        }}
        QPushButton#OnbPrimary:disabled {{
            background-color: {theme.SEC_CARD_COLOR};
            color: {theme.TEXT_SECONDARY};
            border: 1px solid {theme.BORDER_COLOR};
        }}
        QPushButton#OnbGhost {{
            background-color: {theme.MAIN_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 9px;
            font-family: {theme.FONT_FAMILY};
            font-size: 12px;
            font-weight: 600;
            padding: 9px 18px;
        }}
        QPushButton#OnbGhost:hover {{
            background-color: {theme.HOVER_COLOR};
            border: 1px solid {theme.ACCENT_COLOR};
        }}
        QPushButton#OnbClose {{
            background-color: transparent;
            color: {theme.TEXT_SECONDARY};
            border: none;
            border-radius: 11px;
            font-size: 17px;
            font-weight: 500;
        }}
        QPushButton#OnbClose:hover {{
            background-color: {theme.HOVER_COLOR};
            color: {theme.TEXT_PRIMARY};
        }}
        QLineEdit#OnbInput, QComboBox#OnbInput {{
            background-color: {theme.SEC_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 8px;
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
            padding: 7px 10px;
        }}
        QLineEdit#OnbInput:focus, QComboBox#OnbInput:focus {{
            border: 1px solid {theme.ACCENT_COLOR};
        }}
        QComboBox#OnbInput::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox#OnbInput QAbstractItemView {{
            background-color: {theme.MAIN_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 8px;
            selection-background-color: {theme.HOVER_COLOR};
            outline: none;
        }}
    """




