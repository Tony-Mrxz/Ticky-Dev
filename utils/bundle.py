# utils/bundle.py
"""Locates read-only resources that ship inside the built app."""

import os
import sys


def bundle_root():
    """The application folder when frozen, the repository root in development."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def whisper_model_root():
    """download_root for a bundled speech model, or None to use the machine cache.

    The installer ships base.en so dictation works offline on first launch;
    a developer checkout without the model keeps the normal HuggingFace cache.
    """
    candidate = os.path.join(bundle_root(), "models", "whisper")
    return candidate if os.path.isdir(os.path.join(candidate, "models--Systran--faster-whisper-base.en")) else None
