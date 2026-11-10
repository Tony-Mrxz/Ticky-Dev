# utils/festivals.py
"""Offline festival/holiday dates for the notch calendar (python-holidays, India)."""

from functools import lru_cache

COUNTRY = "IN"


@lru_cache(maxsize=8)
def _year_holidays(year):
    import holidays
    return dict(holidays.country_holidays(COUNTRY, years=[year]))


def festivals_for_month(year, month):
    """[(datetime.date, name)] for the given month, sorted by date."""
    table = _year_holidays(year)
    return sorted((day, name) for day, name in table.items()
                  if day.month == month)