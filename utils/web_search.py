# utils/web_search.py
"""Helpers for opening a web search in the user's default browser."""

from __future__ import annotations

import webbrowser
from urllib.parse import quote_plus

GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"


def google_search_url(query: str) -> str:
    return GOOGLE_SEARCH_URL.format(query=quote_plus(query.strip()))


def open_google_search(query: str) -> bool:
    query = query.strip()
    if not query:
        return False
    try:
        return webbrowser.open(google_search_url(query))
    except Exception:
        return False
