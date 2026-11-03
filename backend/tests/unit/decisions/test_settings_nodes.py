import pytest

from phishguard.core import Settings

URL = "http://basal.test/ask"
PROFILER = "profiler.attack_type"
IN_ROLE = "response.in_role"


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
    settings = Settings(basal_url=url, basal_mode=mode, **overrides)

    assert settings.basal_mode_for(PROFILER) == profiler
    assert settings.basal_mode_for(IN_ROLE) == in_role
    assert settings.basal_effective_mode == profiler


def test_in_role_threshold_override_beats_global():
    settings = Settings(
        basal_threshold=0.9,
        basal_threshold_profiler=None,
        basal_threshold_in_role=0.8,
    )

    assert settings.basal_threshold_for(IN_ROLE) == 0.8
    assert settings.basal_threshold_for(PROFILER) == 0.9


def test_threshold_falls_back_to_global():
    settings = Settings(
        basal_threshold=0.9,
        basal_threshold_profiler=None,
        basal_threshold_in_role=None,
    )

    assert settings.basal_threshold_for(IN_ROLE) == 0.9
    assert settings.basal_threshold_for("unknown.node") == 0.9


def test_in_role_threshold_out_of_range_rejected():
    with pytest.raises(ValueError):
        Settings(basal_threshold_in_role=1.5)
