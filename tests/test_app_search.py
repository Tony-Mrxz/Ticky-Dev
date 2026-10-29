# tests/test_app_search.py
"""Tests for Flow-style app matching, ranking, and usage boosts."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.app_indexer import AppIndexer, AppItem
from utils.app_search import match_application, match_text, normalize_query
from utils.app_usage import AppUsageStore


def test_normalize_query_collapses_whitespace_and_case():
    assert normalize_query("  Visual   CODE ") == "visual code"


def test_acronym_matches_application_name():
    match = match_text("vsc", "Visual Studio Code")
    assert match is not None
    assert match.indices == [0, 7, 14]


def test_multi_term_search_requires_all_terms_in_order():
    assert match_text("studio code", "Visual Studio Code") is not None
    assert match_text("code studio", "Visual Studio Code") is None


def test_fuzzy_subsequence_matches():
    assert match_text("taskmgr", "Task Manager") is not None
    assert match_text("notep", "Notepad") is not None


def test_noise_names_are_filtered_out():
    assert match_text("code", "Windows Performance Recorder") is None
    assert match_text("code", "Steps Recorder") is None


def test_exe_stem_fallback_when_display_name_does_not_match():
    match = match_application("cmd", "Command Prompt", "cmd")
    assert match is not None

    match = match_application("notepad", "Text Editor", "notepad")
    assert match is not None


def test_search_ranks_exe_alias_first(tmp_path):
    indexer = AppIndexer()
    indexer._apps = [
        AppItem(name="Notepad", path=r"C:\Windows\System32\notepad.exe", category="System Software"),
        AppItem(name="Git CMD", path=r"C:\Program Files\Git\git-bash.exe"),
        AppItem(name="Command Prompt", path=r"C:\Windows\System32\cmd.exe", category="System Software"),
    ]

    results = indexer.search("cmd")
    assert [app.name for app in results][0] == "Command Prompt"


def test_usage_boost_reorders_results(tmp_path):
    store = AppUsageStore(str(tmp_path / "usage.json"))
    apps = [
        AppItem(name="Visual Studio Code", path=r"C:\Apps\Code.exe"),
        AppItem(name="Visual Studio Installer", path=r"C:\Apps\setup.exe"),
    ]
    indexer = AppIndexer()
    indexer._apps = list(apps)

    baseline = indexer.search("visual studio", usage=store)
    winner = baseline[-1]
    assert winner.name == "Visual Studio Installer"

    for _ in range(5):
        store.record("visual studio", winner.usage_key)

    boosted = indexer.search("visual studio", usage=store)
    assert boosted[0].name == "Visual Studio Installer"


def test_usage_store_persists(tmp_path):
    path = str(tmp_path / "usage.json")
    store = AppUsageStore(path)
    store.record("  VS  ", "path:c:\\apps\\code.exe")

    reloaded = AppUsageStore(path)
    assert reloaded.boost("vs", "path:c:\\apps\\code.exe") == 6
    assert reloaded.boost("other", "path:c:\\apps\\code.exe") == 1


def _run_all():
    import tempfile
    from pathlib import Path

    test_normalize_query_collapses_whitespace_and_case()
    test_acronym_matches_application_name()
    test_multi_term_search_requires_all_terms_in_order()
    test_fuzzy_subsequence_matches()
    test_noise_names_are_filtered_out()
    test_exe_stem_fallback_when_display_name_does_not_match()
    with tempfile.TemporaryDirectory() as temporary:
        tmp_path = Path(temporary)
        test_search_ranks_exe_alias_first(tmp_path)
        test_usage_boost_reorders_results(tmp_path)
        test_usage_store_persists(tmp_path)
    print("All app search tests passed.")


if __name__ == "__main__":
    _run_all()
