"""LLM provider settings (phase 0, task 0.4)."""

import pytest
from pydantic import ValidationError

from phishguard.core import Settings

_LLM_ENV = [
    "LLM_PROVIDER",
    "LLM_PRIMARY_MODEL",
    "LLM_FALLBACK_MODEL",
    "OPENAI_PRIMARY_MODEL",
    "OPENAI_FALLBACK_MODEL",
    "ANTHROPIC_API_KEY",
    "OLLAMA_BASE_URL",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in _LLM_ENV:
        monkeypatch.delenv(name, raising=False)


def test_defaults():
    s = Settings(_env_file=None)
    assert s.llm_provider == "openai"
    assert s.llm_primary_model == ""
    assert s.llm_fallback_model == ""
    assert s.ollama_base_url == "http://localhost:11434/v1"


def test_legacy_openai_primary_model_env_is_honored(monkeypatch):
    monkeypatch.setenv("OPENAI_PRIMARY_MODEL", "gpt-4o")
    monkeypatch.setenv("OPENAI_FALLBACK_MODEL", "gpt-4o-mini")
    s = Settings(_env_file=None)
    assert s.llm_primary_model == "gpt-4o"
    assert s.llm_fallback_model == "gpt-4o-mini"


def test_llm_primary_model_wins_over_legacy(monkeypatch):
    monkeypatch.setenv("OPENAI_PRIMARY_MODEL", "gpt-4o")
    monkeypatch.setenv("LLM_PRIMARY_MODEL", "gpt-6-sol")
    assert Settings(_env_file=None).llm_primary_model == "gpt-6-sol"


def test_invalid_provider_rejected(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
