import pytest

from phishguard.core import Settings

URL = "http://basal.test/ask"
PROFILER = "profiler.attack_type"
IN_ROLE = "response.in_role"


def make_settings(**overrides) -> Settings:
    """Settings independent of .env/process env for every per-node Basal field."""
    fields = {
        "basal_url": URL,
        "basal_mode": "shadow",
        "basal_threshold": 0.9,
        "basal_mode_profiler": None,
        "basal_mode_in_role": None,
        "basal_threshold_profiler": None,
        "basal_threshold_in_role": None,
    }
    fields.update(overrides)
    return Settings(**fields)


@pytest.mark.parametrize(
    ("mode", "overrides", "url", "profiler", "in_role"),
    [
        ("live", {}, URL, "live", "live"),
        ("shadow", {}, URL, "shadow", "shadow"),
        ("live", {"basal_mode_profiler": "off"}, URL, "off", "live"),
        ("off", {"basal_mode_in_role": "live"}, URL, "off", "live"),
        ("shadow", {"basal_mode_profiler": "live"}, URL, "live", "shadow"),
        (
            "live",
            {"basal_mode_profiler": "live", "basal_mode_in_role": "live"},
            "",
            "off",
            "off",
        ),
        ("live", {}, "", "off", "off"),
    ],
)
def test_basal_mode_for_resolves_per_node(mode, overrides, url, profiler, in_role):
    settings = make_settings(basal_url=url, basal_mode=mode, **overrides)

    assert settings.basal_mode_for(PROFILER) == profiler
    assert settings.basal_mode_for(IN_ROLE) == in_role
    assert settings.basal_effective_mode == profiler


def test_in_role_threshold_override_beats_global():
    settings = make_settings(basal_threshold_in_role=0.8)

    assert settings.basal_threshold_for(IN_ROLE) == 0.8
    assert settings.basal_threshold_for(PROFILER) == 0.9


def test_threshold_falls_back_to_global():
    settings = make_settings()

    assert settings.basal_threshold_for(IN_ROLE) == 0.9
    assert settings.basal_threshold_for("unknown.node") == 0.9


def test_in_role_threshold_out_of_range_rejected():
    with pytest.raises(ValueError):
        make_settings(basal_threshold_in_role=1.5)


@pytest.mark.parametrize(
    "var", ["BASAL_MODE_IN_ROLE", "BASAL_THRESHOLD_IN_ROLE", "BASAL_MODE_PROFILER"]
)
def test_empty_per_node_env_falls_back_to_none(monkeypatch, var):
    monkeypatch.setenv(var, "")

    settings = Settings(_env_file=None)

    assert getattr(settings, var.lower()) is None
