"""Smoke tests for smart voice dictation helpers (no live mic required)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_dictation_state_machine_idle_guards():
    from PySide6.QtWidgets import QApplication
    from utils.dictation_service import DictationService, DictationState

    app = QApplication.instance() or QApplication([])
    svc = DictationService()
    assert svc.state == DictationState.IDLE
    assert not svc.is_active

    # cancel / complete while idle should be no-ops
    svc.cancel()
    assert svc.state == DictationState.IDLE
    svc.complete()
    assert svc.state == DictationState.IDLE
    print("[OK] idle state guards")


def test_text_inject_module_imports():
    from utils import text_inject

    assert hasattr(text_inject, "inject_text")
    assert hasattr(text_inject, "inject_backspaces")
    assert hasattr(text_inject, "get_foreground_hwnd")
    # Empty inject is always success
    assert text_inject.inject_text("") is True
    assert text_inject.inject_backspaces(0) is True
    print("[OK] text_inject helpers")


def test_shortcut_defaults_include_voice_dictation():
    from utils import config

    shortcuts = config.load_shortcuts()
    assert "voice_dictation" in shortcuts
    assert shortcuts["voice_dictation"]  # default Alt+D unless user cleared it
    print("[OK] voice_dictation shortcut default:", shortcuts["voice_dictation"])


def test_visualizer_bar_generation():
    from PySide6.QtWidgets import QApplication
    from utils.dictation_service import DictationService, BAR_COUNT

    app = QApplication.instance() or QApplication([])
    svc = DictationService()
    received = []

    svc.levels_updated.connect(lambda levels: received.append(list(levels)))
    svc._current_level = 0.6
    # Pretend we're listening so the visualizer tick emits
    from utils.dictation_service import DictationState
    svc._state = DictationState.LISTENING
    svc._tick_visualizer()
    assert received
    assert len(received[-1]) == BAR_COUNT
    assert all(0.0 <= v <= 1.5 for v in received[-1])
    print("[OK] visualizer bars", len(received[-1]))


if __name__ == "__main__":
    test_text_inject_module_imports()
    test_shortcut_defaults_include_voice_dictation()
    test_dictation_state_machine_idle_guards()
    test_visualizer_bar_generation()
    print("All dictation smoke tests passed.")
