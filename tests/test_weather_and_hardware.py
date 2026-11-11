# tests/test_weather_and_hardware.py
"""
Unit tests for Weather and Hardware Monitor integration in Ticky notch:
- State 2 multi-page system (Page 0: Tasks/Time, Page 1: Weather, Page 2: System Stats)
- Bottom page indicator dots
- Wheel scroll logic (pages cycle vs task rotation over task card)
- Streamlined compact weather (no UV index/precipitation bloat, manual city support)
- Streamlined hardware monitor (TITLE and live usage %, network speed, GPU %, top consumers)
- Clean Sub-Pill (reverted to 6 original buttons, unbloated 256px width)
"""

import os
import sys
import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import config
from utils.weather_service import (
    WMO_CODE_MAP,
    get_wmo_info,
    c_to_f,
    format_temp,
    WeatherService
)
from utils.hardware_service import (
    format_speed,
    get_gpu_model_cached,
    HardwareService
)
from widgets.notch_weather import (
    NotchWeatherWidget,
    WEATHER_NOTCH_WIDTH,
    WEATHER_NOTCH_HEIGHT
)
from widgets.notch_hardware import (
    NotchHardwareWidget,
    HARDWARE_NOTCH_WIDTH,
    HARDWARE_NOTCH_HEIGHT
)
from widgets.notch_sub_pill import NotchSubPill
from widgets.notch_widget import NotchWidget


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def cleanup_services():
    yield
    HardwareService.get_instance().stop_monitoring()
    app = QApplication.instance()
    if app:
        app.processEvents()


# ---------------------------------------------------------------------------
# Weather Service Tests
# ---------------------------------------------------------------------------
def test_wmo_code_map_resolves_known_conditions():
    cond, icon = get_wmo_info(0)
    assert cond == "Clear Sky"
    assert icon == "sun"

    cond, icon = get_wmo_info(2)
    assert cond == "Partly Cloudy"
    assert icon == "cloud_sun"

    cond, icon = get_wmo_info(61)
    assert "Rain" in cond
    assert "rain" in icon

    cond, icon = get_wmo_info(95)
    assert cond == "Thunderstorm"
    assert icon == "thunder"


def test_temperature_conversion_and_formatting():
    assert c_to_f(0.0) == 32.0
    assert c_to_f(100.0) == 212.0
    assert format_temp(21.4, unit="C") == "21°C"
    assert format_temp(21.4, unit="F") == "71°F"
    assert format_temp(None) == "--°"


def test_weather_service_caching():
    service = WeatherService.get_instance()
    assert service is not None
    fresh = service.get_cached_weather()
    assert fresh is None or isinstance(fresh, dict)


def test_weather_manual_city_config():
    config.save_weather_city("Visakhapatnam")
    assert config.load_weather_city() == "Visakhapatnam"
    config.save_weather_city("")
    assert config.load_weather_city() == ""


# ---------------------------------------------------------------------------
# Hardware Service Tests
# ---------------------------------------------------------------------------
def test_format_speed_units():
    assert format_speed(500) == "500 B/s"
    assert format_speed(2048) == "2.0 KB/s"
    assert format_speed(5 * 1024 * 1024) == "5.0 MB/s"
    assert format_speed(2.5 * 1024 * 1024 * 1024) == "2.50 GB/s"


def test_hardware_service_gpu_and_monitoring():
    gpu = get_gpu_model_cached()
    assert isinstance(gpu, str)
    assert len(gpu) > 0

    service = HardwareService.get_instance()
    assert service is not None
    service.start_monitoring()
    assert service._worker is not None
    service.stop_monitoring()
    assert service._worker is None


# ---------------------------------------------------------------------------
# Weather Widget UI Tests
# ---------------------------------------------------------------------------
def test_notch_weather_widget_render(qapp):
    config.save_weather_unit("C")
    widget = NotchWeatherWidget(notch_widget=None)
    mock_data = {
        "city": "Visakhapatnam",
        "country": "IN",
        "temp_c": 28.0,
        "feels_like_c": 31.0,
        "humidity": 78,
        "wind_speed": 14.2,
        "code": 1,
        "condition": "Mainly Clear",
        "icon": "sun_cloud",
        "temp_max_c": 32.0,
        "temp_min_c": 24.0,
    }
    widget._render_weather(mock_data)

    assert "Visakhapatnam" in widget.lbl_location.text()
    assert "28°" in widget.lbl_temp.text()
    assert widget.lbl_hum_val.text() == "78%"
    assert "14.2 km/h" in widget.lbl_wind_val.text()

    # Toggle unit to Fahrenheit
    widget._toggle_unit()
    assert "°F" in widget.lbl_temp.text()
    config.save_weather_unit("C")


# ---------------------------------------------------------------------------
# Hardware Widget UI Tests
# ---------------------------------------------------------------------------
def test_notch_hardware_widget_render(qapp):
    widget = NotchHardwareWidget(notch_widget=None)
    mock_stats = {
        "cpu": {"percent": 24.5},
        "memory": {"percent": 58.2},
        "network": {"speed_str": "3.4 MB/s"},
        "gpu": {"percent": 18.0},
        "top_processes": [
            {"name": "Code", "cpu_percent": 14.5},
            {"name": "Chrome", "cpu_percent": 8.2},
            {"name": "python", "cpu_percent": 4.1},
        ],
    }
    # When top consumers is hidden (default)
    widget.procs_container.setVisible(False)
    widget._render_stats(mock_stats)

    assert widget.card_cpu.lbl_val.text() == "24.5%"
    assert widget.card_mem.lbl_val.text() == "58.2%"
    assert widget.card_net.lbl_val.text() == "3.4 MB/s"
    assert widget.card_gpu.lbl_val.text() == "18.0%"

    # When top consumers is enabled
    widget.procs_container.setVisible(True)
    widget._render_stats(mock_stats)
    assert "Code 14.5%" in widget.lbl_proc_1.text()
    assert "Chrome 8.2%" in widget.lbl_proc_2.text()
    assert "python 4.1%" in widget.lbl_proc_3.text()
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


@pytest.fixture
def notch_instance(qapp):
    notch = NotchWidget()
    yield notch
    if hasattr(notch, "anim") and notch.anim:
        notch.anim.stop()
    notch.collapse_to_idle(force=True)
    notch.close()
    notch.deleteLater()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# Clean Sub-Pill Verification
# ---------------------------------------------------------------------------
def test_sub_pill_remains_clean_and_unbloated(notch_instance):
    notch = notch_instance
    sub_pill = notch.sub_pill
    # Sub-pill has 6 original core buttons: Notes, Reminders, AI, Timer, Music, Settings
    assert not hasattr(sub_pill, "btn_weather")
    assert not hasattr(sub_pill, "btn_hardware")
    assert sub_pill.toolbar.maximumWidth() == 256


# ---------------------------------------------------------------------------
# Notch State 2 Multi-Page System & Navigation Tests
# ---------------------------------------------------------------------------
def test_notch_state2_pages_and_dots(notch_instance):
    notch = notch_instance
    notch.show()
    assert notch.notch_page == 0
    assert notch.hover_h == 68
    assert notch.weather_widget.isHidden()
    assert notch.hardware_widget.isHidden()

    # Enter hover state (State 2)
    notch._is_hovered = True
    notch.resize(notch.hover_w, notch.hover_h)

    # Switch to Page 1: Weather (smooth dynamic expansion to 480x106)
    notch.set_notch_page(1)
    assert notch.notch_page == 1
    assert notch.hover_w == WEATHER_NOTCH_WIDTH
    assert notch.hover_h == WEATHER_NOTCH_HEIGHT
    assert notch.weather_in_notch is True
    assert notch.weather_widget.isVisible()
    assert notch.hardware_widget.isHidden()

    # Switch to Page 2: System Stats / Hardware
    # Compact height (76px) by default without top consumers
    config.save_hardware_show_top_consumers(False)
    notch.set_notch_page(2)
    assert notch.notch_page == 2
    assert notch.hover_w == HARDWARE_NOTCH_WIDTH
    assert notch.hover_h == 76
    assert notch.hardware_in_notch is True
    assert notch.hardware_widget.isVisible()
    assert notch.weather_widget.isHidden()

    # When top consumers is enabled, expands to 112px
    config.save_hardware_show_top_consumers(True)
    notch.set_notch_page(2)
    assert notch.hover_h == HARDWARE_NOTCH_HEIGHT

    # Switch back to Page 0: Tasks / Time (smooth return to 60px height)
    notch.set_notch_page(0)
    assert notch.notch_page == 0
    assert notch.hover_h == 68
    assert notch.weather_widget.isHidden()
    assert notch.hardware_widget.isHidden()

    # Collapse to idle
    notch.collapse_to_idle(force=True)
    assert notch.notch_page == 0
    assert notch.weather_widget.isHidden()
    assert notch.hardware_widget.isHidden()


def test_notch_wheel_scroll_page_navigation(notch_instance):
    notch = notch_instance
    notch._is_hovered = True
    notch.resize(notch.hover_w, notch.hover_h)
    notch.notch_page = 0

    # Simulate wheel event anywhere on notch (outside task card)
    event_down = QWheelEvent(
        QPointF(50, 50),
        QPointF(50, 50),
        QPoint(0, 0),
        QPoint(0, -120),  # Scroll down
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    notch.wheelEvent(event_down)
    assert notch.notch_page == 1  # Switched to page 1 (Weather)

    notch.wheelEvent(event_down)
    assert notch.notch_page == 2  # Switched to page 2 (Hardware)

    # Scrolling past last page (Page 2): boundary reached -> DO NOTHING (no collapse, no wrapping)
    notch.wheelEvent(event_down)
    assert notch.notch_page == 2
    assert notch._is_hovered is True

    # Scroll up (delta > 0)
    event_up = QWheelEvent(
        QPointF(50, 50),
        QPointF(50, 50),
        QPoint(0, 0),
        QPoint(0, 120),  # Scroll up
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    notch.wheelEvent(event_up)
    assert notch.notch_page == 1  # Switched back to page 1

    notch.wheelEvent(event_up)
    assert notch.notch_page == 0  # Switched back to page 0

    # Scrolling before first page (Page 0): boundary reached -> DO NOTHING (no collapse, no wrapping)
    notch.wheelEvent(event_up)
    assert notch.notch_page == 0
    assert notch._is_hovered is True


def test_notch_wheel_scroll_task_rotation_over_task_card(notch_instance):
    notch = notch_instance
    notch._is_hovered = True
    notch.resize(notch.hover_w, notch.hover_h)
    notch.notch_page = 0

    # Setup dummy tasks
    class DummyWindow:
        tasks = ["Buy Groceries", "Finish Report", "Workout"]
    notch.main_window = DummyWindow()
    notch.current_random_task = "Buy Groceries"
    from PySide6.QtCore import QRect
    notch.task_card_rect = QRect(100, 10, 200, 36)

    # Wheel event directly over the task card box
    event_over_task = QWheelEvent(
        QPointF(150, 25),  # Inside (100, 10, 200, 36)
        QPointF(150, 25),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    notch.wheelEvent(event_over_task)

    # Task must rotate! Notch page must NOT change!
    assert notch.notch_page == 0
    assert notch.current_random_task == "Finish Report"


# ---------------------------------------------------------------------------
# Mem Reduct Auto-Detection & RAM Card Hover Clean Tests
# ---------------------------------------------------------------------------
def test_memreduct_detection_and_ram_card_clean(qapp):
    from utils.memreduct import is_memreduct_available, find_memreduct_executable

    avail = is_memreduct_available()
    exe = find_memreduct_executable()
    assert isinstance(avail, bool)
    if avail:
        assert exe is not None and os.path.isfile(exe)

    # Test RAM card interactive clean button
    widget = NotchHardwareWidget(notch_widget=None)
    widget.show()
    card_mem = widget.card_mem
    card_mem.set_value("65.4%")

    # Action enabled
    card_mem.set_action_enabled(True)
    assert card_mem._action_enabled is True
    assert card_mem.btn_action.isHidden()

    # Enter event (mouse hover over RAM card)
    from PySide6.QtGui import QEnterEvent
    enter_ev = QEnterEvent(QPointF(20, 20), QPointF(20, 20), QPointF(20, 20))
    card_mem.enterEvent(enter_ev)
    assert card_mem.btn_action.isVisible()
    assert "65.4%" in card_mem.lbl_title.text()

    # Click clean button
    card_mem._on_action_clicked()
    assert card_mem._is_cleaning is True
    assert card_mem.btn_action.text() == "Cleaning..."

    # Leave event
    from PySide6.QtGui import QFocusEvent
    card_mem.leaveEvent(enter_ev)
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# Time Box Click Opens Calendar Stage Test
# ---------------------------------------------------------------------------
def test_time_box_click_opens_calendar(notch_instance, qapp):
    notch = notch_instance
    notch.show()
    notch._is_hovered = True
    notch.set_notch_page(0)
    notch.resize(notch.hover_w, notch.hover_h)

    from PySide6.QtCore import QRect
    from PySide6.QtGui import QMouseEvent

    notch.time_box_rect = QRect(20, 10, 80, 36)
    assert not getattr(notch, "calendar_in_notch", False)

    # Left click inside time_box_rect
    click_ev = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(40, 25),
        QPointF(40, 25),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier
    )
    notch.mousePressEvent(click_ev)
    qapp.processEvents()

    # Calendar stage must be open!
    assert notch.calendar_in_notch is True
    assert notch.calendar_widget.isVisible()

    # Click again or collapse -> toggles back
    notch.collapse_calendar()
    qapp.processEvents()
    assert notch.calendar_in_notch is False
    assert notch.calendar_widget.isHidden()


# ---------------------------------------------------------------------------
# Dedicated Weather & Hardware Settings Pages Test
# ---------------------------------------------------------------------------
def test_settings_window_weather_and_hardware_pages(qapp):
    from ui.settings_window import SettingsWindow
    win = SettingsWindow()
    win.show()

    # Index 5: Weather
    win.switch_page(5)
    assert win.stacked_widget.currentIndex() == 5
    assert win.lbl_page_title.text() == "Weather Settings"
    assert hasattr(win, "edit_weather_city")
    assert "Auto-detect" in win.edit_weather_city.placeholderText()

    # Index 6: Hardware Monitor
    win.switch_page(6)
    assert win.stacked_widget.currentIndex() == 6
    assert win.lbl_page_title.text() == "Hardware Monitor"
    assert hasattr(win, "switch_hw_top_consumers")
    assert hasattr(win, "lbl_memreduct_status")

    # Index 7: Shortcuts
    win.switch_page(7)
    assert win.stacked_widget.currentIndex() == 7
    assert win.lbl_page_title.text() == "Keyboard Shortcuts"

    win.close()
    win.deleteLater()
    qapp.processEvents()


# ---------------------------------------------------------------------------
# Music Notch Multi-Page Isolation Test
# ---------------------------------------------------------------------------
def test_music_notch_disables_multi_notch_pages_and_dots(notch_instance):
    notch = notch_instance
    notch.show()

    # Suppose user was on page 1 (Weather)
    notch.set_notch_page(1)
    assert notch.notch_page == 1

    # Now open media player in notch
    notch.show_media_in_notch()
    assert notch.media_in_notch is True
    assert notch.notch_page == 0
    assert len(notch.page_dot_rects) == 0
    assert notch.weather_widget.isHidden()
    assert notch.hardware_widget.isHidden()

    # Wheel scroll on music notch must NOT cycle pages
    event_down = QWheelEvent(
        QPointF(50, 50),
        QPointF(50, 50),
        QPoint(0, 0),
        QPoint(0, -120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False
    )
    notch.wheelEvent(event_down)
    assert notch.notch_page == 0
    assert notch.media_in_notch is True

    # set_notch_page must be ignored while in music notch
    notch.set_notch_page(1)
    assert notch.notch_page == 0
    assert notch.weather_widget.isHidden()

    notch.set_notch_page(2)
    assert notch.notch_page == 0
    assert notch.hardware_widget.isHidden()

    # Triggering paintEvent in media mode must NOT generate page dot rects
    notch.repaint()
    assert len(notch.page_dot_rects) == 0

    # Closing media notch restores standard idle
    notch.collapse_media_in_notch()
    assert notch.media_in_notch is False
    assert notch.notch_page == 0


# ---------------------------------------------------------------------------
# Dynamic Island Position Mode Test
# ---------------------------------------------------------------------------
def test_dynamic_island_position_and_offset(notch_instance):
    notch = notch_instance
    notch.show()

    # Dynamic Island position (Position 2: default floating 14px below top)
    notch.set_notch_position("dynamic_island")
    assert config.load_notch_position() == "dynamic_island"
    assert notch.get_notch_top_offset() == 14

    screen = notch.screen() or QApplication.primaryScreen()
    screen_geo = screen.geometry()
    notch.reposition_notch()
    assert notch.y() == screen_geo.y() + 14

    # Top Notch position (Position 1: flush at top y = screen_geo.y())
    notch.set_notch_position("top_notch")
    assert config.load_notch_position() == "top_notch"
    assert notch.get_notch_top_offset() == 0

    notch.reposition_notch()
    assert notch.y() == screen_geo.y()

    # Return to Dynamic Island
    notch.set_notch_position("dynamic_island")
    assert notch.get_notch_top_offset() == 14


def test_dynamic_island_pill_silhouette(notch_instance):
    notch = notch_instance
    notch.show()

    # Dynamic Island mode: Pill silhouette with border radius 50% in compact state
    notch.set_notch_position("dynamic_island")
    w, h = 160.0, 32.0
    path_pill = notch.get_notch_silhouette_path(w, h)

    # Center is filled
    assert path_pill.contains(QPointF(w / 2.0, h / 2.0))
    # Extreme corners (0,0) and (w-1, 0) are rounded off / transparent in a pill (no concave ears)
    assert not path_pill.contains(QPointF(0.0, 0.0))
    assert not path_pill.contains(QPointF(w - 0.5, 0.0))

    # Top Notch mode: Attached MacBook notch silhouette with ears flaring out to (0,0) and (w,0)
    notch.set_notch_position("top_notch")
    path_attached = notch.get_notch_silhouette_path(w, h)
    assert path_attached.elementAt(0).x == 0.0
    assert path_attached.elementAt(0).y == 0.0

    # Restore dynamic_island
    notch.set_notch_position("dynamic_island")


