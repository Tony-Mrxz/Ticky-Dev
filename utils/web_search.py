# utils/web_search.py
"""Helpers for opening a web search, or a URL the user typed, in the default browser."""

from __future__ import annotations

import re
import webbrowser
from urllib.parse import quote_plus

GOOGLE_SEARCH_URL = "https://www.google.com/search?q={query}"

# Bare text only counts as a website when its last label is one of these. Without the
# list "file.txt" and "notes.md" would hijack ordinary searches, and no scheme-free
# rule can tell a domain from a filename - browsers keep such a list for the same reason.
TLDS = frozenset("""
com org net info biz io dev app ai co me tv xyz site online store live tech cloud
page codes docs news world photo design studio center group media solutions network
space website link click email fun host zone wiki blog email pub chat nyc london
edu gov int
de fr jp cn ru br it nl se no fi dk pl es pt gr at ch be cz hu ro bg si sk lt lv ee
ie il ae sa tr ua kz za ng ke eg ma au nz ca mx ar cl pe ve ec uy py bo cr pa do cu
in pk bd lk np hk tw sg my th id vn ph uk us eu mt cy lu is md rs ba mk al ge am az
""".split())

# Last labels that mean "this is a file I am looking for", not a site.
FILE_SUFFIXES = frozenset("""
txt pdf doc docx xls xlsx ppt pptx odt md rst csv tsv json yaml yml toml ini conf env
log py js ts jsx tsx html htm css scss php rb go rs java kt swift c h cpp cs vb pl lua
sh bat ps1 png jpg jpeg gif bmp svg ico webp tiff mp3 mp4 avi mkv mov wav flac zip rar
7z tar gz bz2 xz exe msi dll so apk iso img dmg deb rpm ttf otf woff woff2 epub mobi
""".split())

_SCHEME = re.compile(r"^(https?)://", re.IGNORECASE)
_LABEL = r"[a-zA-Z0-9](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9])?"
_IPV4 = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")
_HOST = rf"(?:{_LABEL}(?:\.{_LABEL})+|\d+(?:\.\d+){{3}}|localhost)"
_AUTHORITY = re.compile(rf"^({_HOST})(:\d{{1,5}})?([/?#].*)?$")


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


def normalize_url(text: str) -> str | None:
    """The absolute URL a query means, or None when it is just search text.

    Accepts a typed scheme, a dotted domain, an IP or localhost, each optionally with a
    port and a path. Anything with whitespace is a phrase, never an address.
    """
    text = (text or "").strip()
    if not text or any(character.isspace() for character in text):
        return None

    typed_scheme = ""
    scheme_match = _SCHEME.match(text)
    if scheme_match:
        typed_scheme = scheme_match.group(1).lower()
        text = text[scheme_match.end():]

    match = _AUTHORITY.match(text)
    if not match:
        return None
    host, port, tail = match.group(1), match.group(2) or "", match.group(3) or ""
    host = host.lower()

    if _IPV4.match(host) or host == "localhost":
        if typed_scheme:
            return f"{typed_scheme}://{host}{port}{tail}"
        return f"http://{host}{port}{tail}"

    suffix = host.rsplit(".", 1)[-1]
    if suffix in FILE_SUFFIXES or suffix not in TLDS:
        return None
    return f"{typed_scheme or 'https'}://{host}{port}{tail}"


def open_url(url: str) -> bool:
    """Open an absolute URL; relative text is a search, not a destination."""
    if not _SCHEME.match(url or ""):
        return False
    try:
        return webbrowser.open(url)
    except Exception:
        return False
