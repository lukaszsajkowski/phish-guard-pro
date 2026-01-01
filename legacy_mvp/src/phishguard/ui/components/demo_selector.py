"""Demo scenario selector component for PhishGuard.

This module provides the scenario selection UI for demo mode,
allowing users to choose from available pre-loaded scenarios.

Requirements: US-019 acceptance criteria
"""

import streamlit as st

from phishguard.demo import DEMO_SCENARIOS
from phishguard.models import SessionStage, SessionState
from phishguard.models.demo import DemoScenarioType


def _handle_scenario_select(scenario_type: DemoScenarioType) -> None:
    """Handle scenario selection.

    Loads the selected scenario and starts demo mode.

    Args:
        scenario_type: The type of scenario selected.
    """
    session: SessionState = st.session_state.app_state
    scenario = DEMO_SCENARIOS[scenario_type]
    session.start_demo(scenario)


def _handle_back_click() -> None:
    """Handle the Back button click.

    Returns to the main start screen.
    """
    session: SessionState = st.session_state.app_state
    session.stage = SessionStage.INPUT


def render_demo_selector() -> None:
    """Render the demo scenario selector.

    Displays available demo scenarios with descriptions and
    allows the user to select one to view or go back to the
    main input screen.
    """
    st.subheader("Select Demo Scenario")
    st.caption(
        "Choose a pre-loaded scenario to see how PhishGuard analyzes and "
        "responds to phishing emails. No API calls are made in demo mode."
    )

    st.divider()

    # Display available scenarios
    for scenario_type in DemoScenarioType:
        scenario = DEMO_SCENARIOS[scenario_type]

        # Create a card-like container for each scenario
        with st.container():
            col_icon, col_content = st.columns([1, 6])

            with col_icon:
                st.markdown(f"# {scenario_type.icon}")

            with col_content:
                st.markdown(f"### {scenario_type.display_name}")
                st.write(scenario_type.description)

                # Show some stats
                attack_name = scenario.classification.attack_type.display_name
                conf = scenario.classification.confidence
                persona_name = scenario.persona.persona_type.display_name
                st.caption(
                    f"Classification: {attack_name} ({conf:.0f}% confidence) | "
                    f"Persona: {persona_name} | "
                    f"{scenario.total_steps} exchanges | {scenario.total_iocs} IOCs"
                )

                # Select button
                if st.button(
                    f"View {scenario_type.display_name}",
                    key=f"select_{scenario_type.value}",
                    type="primary",
                ):
                    _handle_scenario_select(scenario_type)
                    st.rerun()

        st.divider()

    # Back button
    st.button(
        label="Back to Start",
        type="secondary",
        on_click=_handle_back_click,
        use_container_width=True,
    )
