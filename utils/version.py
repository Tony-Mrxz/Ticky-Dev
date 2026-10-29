# utils/version.py
"""The single version number the running app, the installer and the update check share."""

import re

APP_VERSION = "1.3.0"

# Releases are published here by .github/workflows/build.yml; the repository has
# to be public for the anonymous release check to answer.
RELEASE_REPO = "Tony-Mrxz/Ticky-Dev"


def parse_version(text):
    """(major, minor, patch) out of "1.3.0" or "Ticky-Setup-1.3.0.exe", None if unreadable."""
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(part) for part in match.groups()) if match else None


def is_newer(candidate, current=APP_VERSION):
    """True only when the candidate parses and is actually ahead of this build."""
    found, running = parse_version(candidate), parse_version(current)
    return bool(found and running and found > running)
