# tests/test_local_llm.py
"""Tests for offline/local LLM providers (Ollama, LM Studio, OpenAI-compatible)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import requests

from utils import config


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    # Never touch the real ~/.ticky_config.json during tests.
    monkeypatch.setattr(config, "CONFIG_FILE", str(tmp_path / "ticky_config.json"))


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_local_provider_detection_is_case_insensitive():
    assert config.is_local_ai_provider("Ollama")
    assert config.is_local_ai_provider("ollama")
    assert config.is_local_ai_provider("LM Studio")
    assert config.is_local_ai_provider("Custom (OpenAI-compatible)")
    assert not config.is_local_ai_provider("Groq")
    assert not config.is_local_ai_provider("Gemini")
    assert not config.is_local_ai_provider("")
    assert not config.is_local_ai_provider(None)


def test_local_url_defaults_and_roundtrip():
    assert config.load_local_llm_url("Ollama") == "http://localhost:11434"
    assert config.load_local_llm_url("LM Studio") == "http://localhost:1234"
    assert config.load_local_llm_url("Groq") == ""

    config.save_local_llm_url("Ollama", "http://192.168.1.20:11434/")
    assert config.load_local_llm_url("Ollama") == "http://192.168.1.20:11434"
    # Other providers keep their defaults.
    assert config.load_local_llm_url("LM Studio") == "http://localhost:1234"

    config.save_local_llm_url("Ollama", "")
    assert config.load_local_llm_url("Ollama") == "http://localhost:11434"


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")


def _run_worker(monkeypatch, provider, model, api_key="", prompt="hello", base_url="", post=None):
    from widgets.ai_panel import AIWorker
    calls = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.update(url=url, headers=headers, json=json, timeout=timeout)
        if post is not None:
            return post()
        return FakeResponse({"choices": [{"message": {"content": "  local reply  "}}]})

    monkeypatch.setattr(requests, "post", fake_post)
    worker = AIWorker(provider, model, api_key, prompt, base_url=base_url)
    results = []
    worker.finished.connect(lambda ok, text: results.append((ok, text)))
    worker.run()
    return results[0], calls


def test_ollama_request_hits_local_openai_endpoint(qapp, monkeypatch):
    (ok, text), calls = _run_worker(monkeypatch, "Ollama", "llama3.2")
    assert ok and text == "local reply"
    assert calls["url"] == "http://localhost:11434/v1/chat/completions"
    assert "Authorization" not in calls["headers"]
    assert calls["json"]["model"] == "llama3.2"
    assert calls["json"]["messages"][0]["role"] == "system"
    assert calls["json"]["messages"][1] == {"role": "user", "content": "hello"}
    # Local inference gets a generous timeout compared to the 12s cloud calls.
    assert calls["timeout"] >= 60


def test_lm_studio_uses_saved_server_url(qapp, monkeypatch):
    config.save_local_llm_url("LM Studio", "http://127.0.0.1:9999/")
    (ok, _), calls = _run_worker(monkeypatch, "LM Studio", "my-local-model")
    assert ok
    assert calls["url"] == "http://127.0.0.1:9999/v1/chat/completions"


def test_explicit_base_url_overrides_config(qapp, monkeypatch):
    (ok, _), calls = _run_worker(
        monkeypatch, "Custom (OpenAI-compatible)", "model-x", base_url="http://10.0.0.5:8080/")
    assert ok
    assert calls["url"] == "http://10.0.0.5:8080/v1/chat/completions"


def test_local_connection_error_is_actionable(qapp, monkeypatch):
    def refuse():
        raise requests.exceptions.ConnectionError("connection refused")

    (ok, text), _ = _run_worker(monkeypatch, "Ollama", "llama3.2", post=refuse)
    assert not ok
    assert "Cannot reach Ollama" in text
    assert "http://localhost:11434" in text


def test_lm_studio_without_model_asks_for_one(qapp, monkeypatch):
    (ok, text), calls = _run_worker(monkeypatch, "LM Studio", "")
    assert not ok
    assert "No model set" in text
    assert calls == {}


def test_ollama_empty_model_falls_back_to_default(qapp, monkeypatch):
    (ok, _), calls = _run_worker(monkeypatch, "Ollama", "")
    assert ok
    assert calls["json"]["model"] == "llama3.2"


def test_fetch_local_models_lists_ids(monkeypatch):
    from widgets.ai_panel import fetch_local_models

    def fake_get(url, timeout=None):
        assert url == "http://localhost:11434/v1/models"
        return FakeResponse({"data": [{"id": "llama3.2:latest"}, {"id": "qwen2.5:7b"}]})

    monkeypatch.setattr(requests, "get", fake_get)
    models, error = fetch_local_models("Ollama")
    assert error == ""
    assert models == ["llama3.2:latest", "qwen2.5:7b"]


def test_fetch_local_models_reports_unreachable(monkeypatch):
    from widgets.ai_panel import fetch_local_models

    def fake_get(url, timeout=None):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", fake_get)
    models, error = fetch_local_models("LM Studio")
    assert models == []
    assert "Cannot reach" in error


def test_voice_transcription_rejects_local_providers(qapp):
    from widgets.notch_ai_chat import VoiceTranscribeWorker
    worker = VoiceTranscribeWorker("unused.wav", "Ollama", "")
    results = []
    worker.finished.connect(lambda ok, text: results.append((ok, text)))
    worker.run()
    assert results[0][0] is False
    assert "cloud provider" in results[0][1]


def test_provider_lists_include_local_options():
    from ui.onboarding_window import AI_PROVIDERS
    for name in config.LOCAL_AI_PROVIDERS:
        assert name in AI_PROVIDERS