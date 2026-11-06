"""Shared fixtures for Arena tests."""

import pytest


@pytest.fixture
def basal_off(monkeypatch):
    """Force the Basal decision cascade off so only the (fake) LLM decides."""
    from phishguard.core import get_settings

    monkeypatch.setenv("BASAL_URL", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
