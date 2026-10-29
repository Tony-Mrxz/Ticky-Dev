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
from PySide6.QtCore import QObject, QTimer
from ui.main_window import MainWindow
from utils.icon import create_ticky_icon, load_ticky_icon

lock_file = None


class UpdateWatcher(QObject):
    """Bridges the shared UpdateService to the notch update alert."""

    def __init__(self, notch, service, parent=None):
        super().__init__(parent)
        self.notch = notch
        self.service = service
        service.checked.connect(self._on_checked)
        service.download_changed.connect(self._on_download)
        notch.update_now_requested.connect(self._on_update_now)

    def _on_checked(self, info):
        # Any check that finds a release may raise the pill; failures stay silent
        # inside the service and never reach here.
        if info is not None and self.notch.isVisible():
            self.notch.show_update_alert(info)

    def _on_download(self, status):
        self.notch.set_update_state(status)

    def _on_update_now(self):
        self.service.download_and_install()


def start_update_flow(window, onboarding=None):
    """Wires the notch alert and schedules the launch-time release check."""
    from utils import config
    from utils.update_checker import UpdateService

    notch = getattr(window, "notch_widget", None)
    if notch is None:
        return
    service = UpdateService.get_instance()
    window.update_watcher = UpdateWatcher(notch, service, parent=window)

    if not config.load_check_for_updates():
        return
    if onboarding is not None and onboarding.isVisible():
        # Never compete with the wizard; check once it is put away.
        onboarding.finished.connect(lambda: QTimer.singleShot(4000, service.check))
        return
    QTimer.singleShot(4000, service.check)


def main():
    global lock_file
    import os
    # Ensure working directory is set to application folder when launched by Windows Registry on boot
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Enforce single instance application lock
    from PySide6.QtCore import QLockFile, QDir
    lock_file = QLockFile(QDir.temp().absoluteFilePath("ticky_application.lock"))
    if not lock_file.tryLock(100):
        print("Ticky is already running. Exiting.", flush=True)
        sys.exit(0)
        
    # Set high-DPI scaling attributes if using older Qt versions, but PySide6 handles it natively
    QApplication.setStyle("fusion")
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Branded icon for tray, taskbar buttons and all windows
    ticky_icon = load_ticky_icon()
    app.setWindowIcon(ticky_icon)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Ticky.DesktopApp")
        except Exception:
            pass

    # Build the app and file indexes off the GUI thread during startup so the
    # first Alt+W search is instant.
    from utils.app_indexer import AppIndexer
    from utils.file_indexer import FileIndexer
    AppIndexer.get_instance()
    FileIndexer.get_instance()
    
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
    saved_font = config.load_font_family("DM Sans")
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
    
    # Set default startup registry key if not already configured
    from utils import config
    if config.load_config().get("start_on_startup") is None:
        from utils.startup import set_startup
        set_startup(True)
        config.save_start_on_startup(True)

    # Initialize the main UI controller (Notch is the visible UI; classic window stays hidden)
    window = MainWindow()

    # First run: the wizard owns the screen until it closes, then the notch comes back
    from ui.onboarding_window import OnboardingWindow, ONBOARDING_VERSION
    onboarding = None
    if config.load_onboarding_version(0) < ONBOARDING_VERSION:
        if window.notch_widget:
            window.notch_widget.hide()
        onboarding = OnboardingWindow(window)
        onboarding.finished.connect(window.toggle_notch_visibility)
        onboarding.show()

    # Newer public build -> update alert in the notch
    start_update_flow(window, onboarding)

    # Create system tray icon
    tray_icon = QSystemTrayIcon(ticky_icon, app)
    tray_icon.setToolTip("Ticky")
    
    # Create tray menu
    tray_menu = QMenu()
    
    show_hide_action = tray_menu.addAction("Show/Hide")
    show_hide_action.triggered.connect(window.toggle_notch_visibility)
    
    settings_action = tray_menu.addAction("Settings")
    settings_action.triggered.connect(window.show_settings_menu)
    
    tray_menu.addSeparator()
    
    quit_action = tray_menu.addAction("Quit")
    quit_action.triggered.connect(app.quit)
    
    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()
    
    # Double-click on tray icon to show/hide
    tray_icon.activated.connect(
        lambda reason: window.toggle_notch_visibility()
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
    )
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
