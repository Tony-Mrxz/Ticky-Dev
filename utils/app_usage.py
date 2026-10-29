# utils/app_usage.py
"""Persistent launch history used to boost frequently chosen apps."""

from __future__ import annotations

import json
import os
import threading

from utils.app_search import normalize_query

USAGE_FILE = os.path.join(os.path.expanduser("~"), ".ticky_app_usage.json")
_MAX_QUERIES = 200
_MAX_APPS = 1000


class AppUsageStore:
    _instance: "AppUsageStore | None" = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AppUsageStore":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self, path: str = USAGE_FILE):
        self._path = path
        self._lock = threading.RLock()
        self._total: dict[str, int] = {}
        self._queries: dict[str, dict[str, int]] = {}
        self._load()

    def record(self, query: str, app_key: str):
        normalized = normalize_query(query)
        if not normalized or not app_key:
            return

        with self._lock:
            self._total[app_key] = self._total.get(app_key, 0) + 1
            query_records = self._queries.setdefault(normalized, {})
            query_records[app_key] = query_records.get(app_key, 0) + 1
            self._prune()

        self._save()

    def boost(self, query: str, app_key: str) -> int:
        normalized = normalize_query(query)
        if not normalized:
            return 0
        with self._lock:
            return (
                self._queries.get(normalized, {}).get(app_key, 0) * 5
                + self._total.get(app_key, 0)
            )

    def _prune(self):
        if len(self._queries) > _MAX_QUERIES:
            for key in list(self._queries)[: len(self._queries) - _MAX_QUERIES]:
                del self._queries[key]
        if len(self._total) > _MAX_APPS:
            keep = sorted(self._total.items(), key=lambda item: item[1], reverse=True)[:_MAX_APPS]
            self._total = dict(keep)

    def _load(self):
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        total = data.get("total", {})
        queries = data.get("queries", {})
        if isinstance(total, dict):
            self._total = {
                str(key): int(value)
                for key, value in total.items()
                if isinstance(value, (int, float))
            }
        if isinstance(queries, dict):
            self._queries = {
                str(query): {
                    str(key): int(value)
                    for key, value in records.items()
                    if isinstance(value, (int, float))
                }
                for query, records in queries.items()
                if isinstance(records, dict)
            }

    def _save(self):
        with self._lock:
            data = {"total": dict(self._total), "queries": {k: dict(v) for k, v in self._queries.items()}}
        temporary = self._path + ".tmp"
        try:
            with open(temporary, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(temporary, self._path)
        except OSError:
            try:
                os.remove(temporary)
            except OSError:
                pass
