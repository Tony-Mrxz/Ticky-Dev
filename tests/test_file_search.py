# tests/test_file_search.py
"""Tests for file/folder indexing, matching, and mixed result composition."""

import os
import sys
import webbrowser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.app_indexer import AppItem
from utils.file_indexer import FileItem, build_index, search_items
from utils.web_search import google_search_url, open_google_search
from widgets.notch_app_search import compose_results


def _write(path: str, content: str = "x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def test_index_includes_the_root_folder_itself(tmp_path):
    root = tmp_path / "Documents"
    root.mkdir()

    items = build_index([str(root)])
    results = search_items(items, "documents")

    assert results[0].path == str(root)
    assert results[0].is_dir is True


def test_search_shows_a_folder_and_file_when_both_match(tmp_path):
    root = tmp_path / "BalancedDownloads"
    _write(str(root / "report.pdf"))
    _write(str(root / "report.txt"))
    _write(str(root / "annual report archive" / "data.csv"))

    items = build_index([str(root)])
    results = search_items(items, "report", limit=2)

    assert len(results) == 2
    assert results[0].is_dir is False
    assert results[0].name == "report.pdf"
    assert results[1].is_dir is True
    assert results[1].name == "annual report archive"


def test_index_skips_heavy_dirs_and_shell_noise(tmp_path):
    root = tmp_path / "Desktop"
    _write(str(root / "notes.txt"))
    _write(str(root / "Projects" / "alpha.md"))
    _write(str(root / "node_modules" / "package" / "index.js"))
    _write(str(root / ".git" / "config"))
    _write(str(root / "desktop.ini"))
    _write(str(root / "thumbs.db"))

    items = build_index([str(root)])
    names = {item.name for item in items}

    assert "notes.txt" in names
    assert "Projects" in names
    assert "alpha.md" in names
    assert "node_modules" not in names
    assert "index.js" not in names
    assert ".git" not in names
    assert "desktop.ini" not in names
    assert "thumbs.db" not in names


def test_index_respects_depth_and_entry_caps(tmp_path):
    root = tmp_path / "Documents"
    _write(str(root / "level1" / "level2" / "deep.txt"))
    _write(str(root / "top.txt"))

    shallow = build_index([str(root)], max_depth=0)
    shallow_names = {item.name for item in shallow}
    assert "top.txt" in shallow_names
    assert "level1" in shallow_names
    assert "deep.txt" not in shallow_names

    capped = build_index([str(root)], max_entries=1)
    assert len(capped) == 1


def test_file_search_prefers_exact_then_prefix_then_substring(tmp_path):
    root = str(tmp_path / "RankDownloads")
    _write(os.path.join(root, "report.pdf"))
    _write(os.path.join(root, "report-final.pdf"))
    _write(os.path.join(root, "annual-report.pdf"))
    _write(os.path.join(root, "unrelated.txt"))

    items = build_index([root])
    results = search_items(items, "report", limit=3)
    names = [item.name for item in results]

    assert names[0] == "report.pdf"
    assert set(names) == {"report.pdf", "report-final.pdf", "annual-report.pdf"}


def test_file_search_ignores_query_case(tmp_path):
    root = str(tmp_path / "Documents")
    _write(os.path.join(root, "Report.pdf"))

    items = build_index([root])
    results = search_items(items, "REPORT")

    assert [item.name for item in results] == ["Report.pdf"]


def test_file_search_matches_folders_and_multi_term_queries(tmp_path):
    root = str(tmp_path / "Documents")
    _write(os.path.join(root, "Final Report", "data.csv"))
    _write(os.path.join(root, "Report Final", "other.csv"))
    _write(os.path.join(root, "Final Report.pdf"))

    items = build_index([root])
    results = search_items(items, "final report", limit=2)
    names = [item.name for item in results]

    assert "Final Report" in names
    assert "Final Report.pdf" in names
    assert "Report Final" not in names


def test_file_search_falls_back_to_fuzzy_names(tmp_path):
    root = str(tmp_path / "FuzzyDownloads")
    _write(os.path.join(root, "notes.txt"))
    _write(os.path.join(root, "holiday.jpg"))

    items = build_index([root])
    results = search_items(items, "nts", limit=2)

    assert [item.name for item in results] == ["notes.txt"]


def test_file_item_labels(tmp_path):
    folder = FileItem(str(tmp_path / "Projects"), True)
    document = FileItem(str(tmp_path / "assets" / "logo.svg"), False)
    archive = FileItem(str(tmp_path / "assets" / "backup.7z"), False)
    unknown = FileItem(str(tmp_path / "assets" / "notes.zzz"), False)

    assert folder.type_label() == "Folder"
    assert document.type_label() == "Image"
    assert archive.type_label() == "Archive"
    assert unknown.type_label() == "ZZZ file"


def test_google_search_url_escapes_query():
    assert (
        google_search_url("c++ tips & tricks")
        == "https://www.google.com/search?q=c%2B%2B+tips+%26+tricks"
    )
    assert open_google_search("   ") is False


def test_open_google_search_uses_default_browser(monkeypatch):
    opened = []
    monkeypatch.setattr(webbrowser, "open", lambda url: opened.append(url) or True)

    assert open_google_search("  ticky notes  ") is True
    assert opened == ["https://www.google.com/search?q=ticky+notes"]


def test_compose_results_orders_apps_google_then_files(tmp_path):
    app = AppItem("Notepad", r"C:\Windows\System32\notepad.exe")
    folder = FileItem(str(tmp_path / "Documents" / "Notes"), True)
    document = FileItem(str(tmp_path / "Documents" / "notes.txt"), False)

    results = compose_results([app], "notes", [folder, document])

    assert [result.kind for result in results] == ["app", "google", "file", "file"]
    assert results[0].title == "Notepad"
    assert results[1].payload == "notes"
    assert results[2].payload is folder
    assert results[3].payload is document


def test_compose_results_puts_google_first_without_app_matches(tmp_path):
    folder = FileItem(str(tmp_path / "Notes"), True)

    results = compose_results([], "notes", [folder])

    assert [result.kind for result in results] == ["google", "file"]
    assert results[0].hint == "Search ↵"
    assert results[1].hint == "Open ↵"


def _run_all():
    import tempfile
    from pathlib import Path

    test_google_search_url_escapes_query()

    with tempfile.TemporaryDirectory() as temporary:
        tmp_path = Path(temporary)
        test_index_includes_the_root_folder_itself(tmp_path)
        test_search_shows_a_folder_and_file_when_both_match(tmp_path)
        test_index_skips_heavy_dirs_and_shell_noise(tmp_path)
        test_index_respects_depth_and_entry_caps(tmp_path)
        test_file_search_prefers_exact_then_prefix_then_substring(tmp_path)
        test_file_search_ignores_query_case(tmp_path)
        test_file_search_matches_folders_and_multi_term_queries(tmp_path)
        test_file_search_falls_back_to_fuzzy_names(tmp_path)
        test_file_item_labels(tmp_path)
        test_compose_results_orders_apps_google_then_files(tmp_path)
        test_compose_results_puts_google_first_without_app_matches(tmp_path)
    print("All file search tests passed.")


if __name__ == "__main__":
    _run_all()
