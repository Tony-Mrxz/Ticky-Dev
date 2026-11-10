# tests/test_notch_calendar.py
"""Tests for the notch calendar stage: events, festivals, grid and mode wiring."""

import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from utils import config
from utils.festivals import festivals_for_month
from widgets.notch_calendar import (NotchCalendarWidget, collect_month_events,
                                    month_grid)


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    # Never touch the real ~/.ticky_config.json during tests.
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "ticky_config.json"))


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def widget(qapp):
    from PySide6.QtCore import Qt
    w = NotchCalendarWidget(None)
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    w.show()
    qapp.processEvents()
    yield w
    w.close()
    w.deleteLater()


# -- persistence ---------------------------------------------------------------

def test_events_roundtrip():
    assert config.load_events() == []
    events = [{"id": "a1", "title": "Standup", "date": "2026-11-10", "time": "09:30"},
              {"id": "b2", "title": "Dentist", "date": "2026-11-12", "time": ""}]
    config.save_events(events)
    assert config.load_events() == events
    config.save_events([])
    assert config.load_events() == []


# -- festivals -----------------------------------------------------------------

def test_festivals_fixed_dates():
    jan = festivals_for_month(2026, 1)
    assert (datetime.date(2026, 1, 26), "Republic Day") in jan
    aug = festivals_for_month(2026, 8)
    assert (datetime.date(2026, 8, 15), "Independence Day") in aug
    nov = festivals_for_month(2026, 11)
    assert any(day == datetime.date(2026, 11, 8) for day, _ in nov)  # Diwali
    assert all(day.month == 11 for day, _ in nov)


def test_festivals_empty_month_still_list():
    assert isinstance(festivals_for_month(2026, 6), list)


# -- month grid ----------------------------------------------------------------

def test_month_grid_november_2026_sunday_start():
    weeks = month_grid(2026, 11)
    assert weeks[0][0] == datetime.date(2026, 11, 1)  # Nov 1 2026 is a Sunday
    flat = [d for week in weeks for d in week if d is not None]
    assert flat == [datetime.date(2026, 11, d) for d in range(1, 31)]
    assert all(len(week) == 7 for week in weeks)


def test_month_grid_leading_blanks_and_december_rollover():
    weeks = month_grid(2026, 3)  # Mar 1 2026 is a Sunday too; use May (Friday)
    weeks = month_grid(2026, 5)
    assert weeks[0][:5] == [None] * 5  # May 1 2026 is a Friday
    assert weeks[0][5] == datetime.date(2026, 5, 1)
    dec = month_grid(2026, 12)
    flat = [d for week in dec for d in week if d is not None]
    assert flat[-1] == datetime.date(2026, 12, 31)


def test_month_grid_leap_february():
    weeks = month_grid(2028, 2)
    flat = [d for week in weeks for d in week if d is not None]
    assert len(flat) == 29
    assert flat[-1] == datetime.date(2028, 2, 29)


# -- merged event list ----------------------------------------------------------

def test_collect_month_events_merge_sort_and_filter():
    config.save_events([
        {"id": "u1", "title": "Late meeting", "date": "2026-11-10", "time": "18:00"},
        {"id": "u2", "title": "Early meeting", "date": "2026-11-10", "time": "09:00"},
        {"id": "u3", "title": "Diwali party", "date": "2026-11-08", "time": ""},
        {"id": "u4", "title": "Other month", "date": "2026-12-01", "time": ""},
        {"id": "u5", "title": "Broken date", "date": "not-a-date", "time": ""},
    ])
    items = collect_month_events(2026, 11)
    titles = [e["title"] for e in items]
    assert "Other month" not in titles
    assert "Broken date" not in titles
    dates = [e["date"] for e in items]
    assert dates == sorted(dates)
    same_day = [e["title"] for e in items if e["date"] == datetime.date(2026, 11, 10)]
    assert same_day == ["Early meeting", "Late meeting"]
    kinds = {e["kind"] for e in items}
    assert kinds == {"user", "festival"}
    fest = next(e for e in items if e["kind"] == "festival"
                and e["date"] == datetime.date(2026, 11, 8))
    assert fest["id"] == "fest-2026-11-08"


# -- widget behaviour -----------------------------------------------------------

def test_calendar_chrome_removed_and_svg_arrows(widget):
    assert not hasattr(widget, "today_card")
    assert not hasattr(widget, "lbl_card_date")
    assert not hasattr(widget, "btn_close")
    assert not widget.btn_prev.icon().isNull()
    assert not widget.btn_next.icon().isNull()


def test_month_navigation_and_year_rollover(widget):
    start_year, start_month = widget._year, widget._month
    widget.btn_next.click()
    expected = datetime.date(start_year, start_month, 1) + datetime.timedelta(days=32)
    assert (widget._year, widget._month) == (expected.year, expected.month)
    widget.btn_prev.click()
    assert (widget._year, widget._month) == (start_year, start_month)
    for _ in range(12):
        widget._shift_month(1)
    assert widget._year == start_year + 1
    assert widget._month == start_month


def test_picker_selects_month_and_year(widget):
    assert not widget.picker_row.isVisible()
    widget.btn_month_year.click()
    assert widget.picker_row.isVisible()
    widget.combo_month.setCurrentIndex(2)  # March
    target_year = widget._today.year + 1
    idx = widget.combo_year.findText(str(target_year))
    widget.combo_year.setCurrentIndex(idx)
    assert (widget._year, widget._month) == (target_year, 3)
    assert "March" in widget.btn_month_year.text()
    widget.btn_month_year.click()
    assert not widget.picker_row.isVisible()


def test_day_click_selects_date(widget):
    weeks = month_grid(widget._year, widget._month)
    target = datetime.date(widget._year, widget._month, 15)
    index = next(i for i in range(42)
                 if (lambda r, c: r < len(weeks) and weeks[r][c] == target)(i // 7, i % 7))
    widget._on_day_clicked(index)
    assert widget._selected == target


def test_add_event_saves_and_hides_creator(widget):
    widget._start_add()
    assert widget.creator.isVisible()
    assert not widget.scroll.isVisible()
    widget.input_title.setText("Team sync")
    widget.input_time.setText("14:30")
    widget.btn_save.click()
    events = config.load_events()
    assert len(events) == 1
    assert events[0]["title"] == "Team sync"
    assert events[0]["time"] == "14:30"
    assert events[0]["date"] == widget._selected.isoformat()
    assert events[0]["id"]
    assert not widget.creator.isVisible()
    assert widget.scroll.isVisible()


def test_add_event_rejects_bad_time_and_empty_title(widget):
    widget._start_add()
    widget.input_title.setText("Bad time")
    widget.input_time.setText("25:00")
    widget.btn_save.click()
    assert config.load_events() == []
    widget.input_time.setText("9:00")  # must be zero-padded HH:MM
    widget.btn_save.click()
    assert config.load_events() == []
    widget.input_title.setText("   ")
    widget.input_time.setText("09:00")
    widget.btn_save.click()
    assert config.load_events() == []
    widget.input_title.setText("Good event")
    widget.btn_save.click()
    assert len(config.load_events()) == 1


def test_cancel_add_keeps_events_untouched(widget):
    widget._start_add()
    widget.input_title.setText("Never saved")
    widget.btn_cancel.click()
    assert config.load_events() == []
    assert not widget.creator.isVisible()


def test_delete_event(widget):
    config.save_events([{"id": "del1", "title": "Remove me",
                         "date": widget._selected.isoformat(), "time": ""}])
    widget.reload()
    widget._delete_event("del1")
    assert config.load_events() == []


def test_event_rows_keep_chronological_order(widget):
    from PySide6.QtWidgets import QLabel
    widget._year, widget._month = 2026, 11
    base = datetime.date(2026, 11, 9)
    widget._today = base
    widget._selected = base
    config.save_events([
        {"id": "c", "title": "Third", "date": (base + datetime.timedelta(days=2)).isoformat(), "time": ""},
        {"id": "a", "title": "First", "date": base.isoformat(), "time": ""},
        {"id": "b", "title": "Second", "date": (base + datetime.timedelta(days=1)).isoformat(), "time": ""},
    ])
    widget.reload()
    badges = []
    for i in range(widget.events_layout.count()):
        item = widget.events_layout.itemAt(i)
        row = item.widget()
        if row is not None:
            badges.append(row.findChild(QLabel).text())
    assert badges == sorted(badges, key=int)
    user_badges = [b for b in badges if b in {"09", "10", "11"}]
    assert user_badges == ["09", "10", "11"]


def test_past_events_hidden_unless_selected(widget):
    widget._year, widget._month = 2026, 11
    widget._today = datetime.date(2026, 11, 9)
    widget._selected = None
    config.save_events([
        {"id": "past", "title": "Old meeting", "date": "2026-11-05", "time": ""},
        {"id": "today", "title": "Today meeting", "date": "2026-11-09", "time": ""},
        {"id": "future", "title": "Future meeting", "date": "2026-11-12", "time": ""},
    ])
    titles = [e["title"] for e in widget._visible_events()]
    assert "Old meeting" not in titles
    assert "Today meeting" in titles
    assert "Future meeting" in titles

    # Selecting the past day surfaces its events.
    widget._selected = datetime.date(2026, 11, 5)
    titles = [e["title"] for e in widget._visible_events()]
    assert "Old meeting" in titles


def test_calendar_unhover_collapses_to_idle(qapp):
    from PySide6.QtGui import QCursor
    from widgets.notch_widget import NotchWidget
    notch = NotchWidget()
    try:
        notch.show_calendar_in_notch()
        qapp.processEvents()
        assert notch.calendar_in_notch is True

        # Cursor away + grace timeout -> back to the idle ground state.
        QCursor.setPos(0, 0)
        qapp.processEvents()
        notch._on_calendar_unhover_timeout()
        assert notch.calendar_in_notch is False
        assert not notch.calendar_widget.isVisible()
    finally:
        notch.collapse_to_idle(force=True)
        notch.close()
        qapp.processEvents()


# -- notch integration -----------------------------------------------------------

def test_notch_calendar_mode_lifecycle(qapp):
    from widgets.notch_widget import NotchWidget
    notch = NotchWidget()
    try:
        notch.show_calendar_in_notch()
        assert notch.calendar_in_notch is True
        assert notch.calendar_widget.isVisible()
        qapp.processEvents()

        # Collapsing returns to the idle ground state.
        notch.collapse_calendar()
        qapp.processEvents()
        assert notch.calendar_in_notch is False
        assert not notch.calendar_widget.isVisible()

        # Opening another stage must evict the calendar cleanly.
        notch.show_calendar_in_notch()
        assert notch.calendar_in_notch is True
        notch.show_notes_in_notch()
        assert notch.calendar_in_notch is False
        assert not notch.calendar_widget.isVisible()
        assert notch.notes_in_notch is True
    finally:
        notch.collapse_to_idle(force=True)
        notch.close()
        qapp.processEvents()


def test_calendar_dividing_line_and_even_spacing(widget):
    from widgets.notch_calendar import (
        CALENDAR_W, EVENTS_W, DIVIDER_W, DIVIDER_GAP,
        NOTCH_PADDING_X, NOTCH_PADDING_Y, NOTCH_WIDTH,
        CALENDAR_UNHOVER_TIMEOUT_MS,
    )
    # Check unhover fallback timer is within the 1-2 second range (1200ms)
    assert 1000 <= CALENDAR_UNHOVER_TIMEOUT_MS <= 2000
    assert CALENDAR_UNHOVER_TIMEOUT_MS == 1200

    # Check dividing line exists between calendar and events box
    assert hasattr(widget, "divider")
    assert widget.divider is not None
    assert widget.calendar_box.width() == CALENDAR_W

    # Check even spacing equation
    expected_content_w = CALENDAR_W + (2 * DIVIDER_GAP) + DIVIDER_W + EVENTS_W
    assert expected_content_w == NOTCH_WIDTH - (NOTCH_PADDING_X * 2)

    # Check that day buttons have high contrast text
    for btn in widget._day_buttons:
        if btn.isVisible():
            style = btn.styleSheet()
            assert "#FFFFFF" in style
            assert "11px" in style
