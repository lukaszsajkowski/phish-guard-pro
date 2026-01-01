"""Demo scenarios for PhishGuard demonstration mode.

This module provides pre-loaded demo scenarios that can be browsed
without making API calls (US-019).
"""

from phishguard.demo.scenarios import (
    DEMO_SCENARIOS,
    get_scenario,
    get_scenario_by_type,
)

__all__ = [
    "DEMO_SCENARIOS",
    "get_scenario",
    "get_scenario_by_type",
]
