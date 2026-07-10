# main.py
"""Entry point for the Ticky desktop companion application."""

import sys

class NullStream:
    def write(self, text):
        pass
    def flush(self):
        pass

if sys.stdout is None:
    sys.stdout = NullStream()
if sys.stderr is None:
    sys.stderr = NullStream()

from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from ui.main_window import MainWindow
from utils.icon import create_ticky_icon

def main():
    # Set high-DPI scaling attributes if using older Qt versions, but PySide6 handles it natively
    QApplication.setStyle("fusion")
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Register all custom fonts from the fonts directory
    import os
    from PySide6.QtGui import QFontDatabase, QFont
    font_dir = os.path.join(os.path.dirname(__file__), "styles", "fonts")
    loaded = []
    for fname in os.listdir(font_dir):
        if fname.lower().endswith((".ttf", ".otf")):
            fid = QFontDatabase.addApplicationFont(os.path.join(font_dir, fname))
            families = QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
            if families:
                loaded.append(families[0])
    
    # Set default app font with antialiasing and quality hints
    from utils import config
    saved_font = config.load_font_family("Inter")
    app_font = QFont(saved_font)
    app_font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
    app_font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    app.setFont(app_font)
    
    # Set global application stylesheet for tooltips and menus
    from styles import theme
    app.setStyleSheet(f"""
        QToolTip {{
            background-color: {theme.MAIN_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 6px;
            font-family: {theme.FONT_FAMILY};
            font-size: 10px;
            padding: 3px 6px;
        }}
        QMenu {{
            background-color: {theme.MAIN_CARD_COLOR};
            color: {theme.TEXT_PRIMARY};
            border: 1px solid {theme.BORDER_COLOR};
            border-radius: 8px;
            padding: 4px 0px;
            font-family: {theme.FONT_FAMILY};
            font-size: 11px;
        }}
        QMenu::item {{
            background-color: transparent;
            padding: 6px 20px;
            border-radius: 4px;
            margin: 2px 4px;
        }}
        QMenu::item:selected {{
            background-color: {theme.HOVER_COLOR};
            color: {theme.ACCENT_COLOR};
        }}
        QMenu::separator {{
            height: 1px;
            background-color: {theme.BORDER_COLOR};
            margin: 4px 0px;
        }}
    """)
    
    # Initialize the main UI window
    window = MainWindow()
    window.show()
    
    # Create system tray icon
    tray_icon = QSystemTrayIcon(create_ticky_icon(), app)
    tray_icon.setToolTip("Ticky")
    
    # Create tray menu
    tray_menu = QMenu()
    
    show_hide_action = tray_menu.addAction("Show/Hide")
    show_hide_action.triggered.connect(lambda: window.setVisible(not window.isVisible()))
    
    minimize_ball_action = tray_menu.addAction("Minimize to Ball")
    def toggle_ball_minimize():
        if window.widget_state == "minimized_ball":
            window.restore_from_ball()
        else:
            window.minimize_to_ball()
    minimize_ball_action.triggered.connect(toggle_ball_minimize)
    
    settings_action = tray_menu.addAction("Settings")
    settings_action.triggered.connect(window.show_settings_menu)
    
    tray_menu.addSeparator()
    
    quit_action = tray_menu.addAction("Quit")
    quit_action.triggered.connect(app.quit)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # Double-click on tray icon to show/hide
    tray_icon.activated.connect(
        lambda reason: window.setVisible(not window.isVisible()) 
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
    )
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
