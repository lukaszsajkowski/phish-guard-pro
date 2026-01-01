"""Demo scenario viewer component for PhishGuard.

This module provides the step-by-step demo browsing UI,
displaying the conversation and IOCs without making API calls.

Requirements: US-019 acceptance criteria
"""

import streamlit as st

from phishguard.models import SessionState
from phishguard.models.conversation import MessageSender
from phishguard.ui.components.agent_thinking import render_agent_thinking


def _handle_next_step() -> None:
    """Handle the Next Step button click.

    Advances to the next step in the demo scenario.
    """
    session: SessionState = st.session_state.app_state
    session.advance_demo_step()


def _handle_end_demo() -> None:
    """Handle the End Demo button click.

    Exits demo mode and returns to the start screen.
    """
    session: SessionState = st.session_state.app_state
    session.exit_demo()


def render_demo_viewer() -> None:
    """Render the demo scenario viewer.

    Displays the demo scenario step by step, including:
    - Header with scenario info and controls
    - Chat history up to current step
    - Agent thinking panel for bot messages
    - Next step and End demo buttons

    Note: This component does not make any API calls (FR-035).
    """
    session: SessionState = st.session_state.app_state

    if not session.is_demo_mode or session.demo_scenario is None:
        st.error("No demo scenario loaded.")
        if st.button("Return to Start"):
            session.exit_demo()
            st.rerun()
        return

    scenario = session.demo_scenario

    # Header with demo indicator and controls
    header_col, end_col = st.columns([3, 1])

    with header_col:
        # Show demo badge and scenario name
        st.markdown(
            f"### Demo: {scenario.scenario_type.display_name} "
            f":blue[Step {session.demo_step_index + 1}/{scenario.total_steps}]"
        )

    with end_col:
        # End demo button always visible (US-019)
        if st.button("End demo", type="secondary"):
            _handle_end_demo()
            st.rerun()

    # Show demo mode notice
    st.info(
        "You are viewing a pre-loaded demo scenario. "
        "No API calls are being made. Click 'Next' to advance through the conversation."
    )

    # Show the original phishing email in a collapsed expander
    with st.expander("Original Phishing Email", expanded=False):
        st.text(scenario.email_content)

    # Show classification summary
    with st.expander("Classification", expanded=False):
        result = scenario.classification
        st.markdown(f"**Attack Type:** {result.attack_type.display_name}")
        st.markdown(f"**Confidence:** {result.confidence:.1f}%")
        st.write(result.reasoning)

    # Show persona info
    with st.expander("Victim Persona", expanded=False):
        persona = scenario.persona
        st.markdown(f"**{persona.name}**, {persona.age}")
        st.markdown(f"*{persona.persona_type.display_name}*")
        st.write(persona.style_description)

    # Display Agent Thinking panel if current step is a bot message
    if session.demo_step_index >= 0:
        current_thinking = scenario.get_current_thinking(session.demo_step_index)
        if current_thinking:
            render_agent_thinking(current_thinking)

    st.divider()

    # Display chat history up to current step
    _render_demo_chat_history(session)

    st.divider()

    # Navigation controls
    _render_demo_controls(session)


def _render_demo_chat_history(session: SessionState) -> None:
    """Render the demo conversation history up to the current step.

    Args:
        session: Current session state with demo scenario.
    """
    if session.demo_scenario is None:
        st.caption("No demo scenario loaded.")
        return

    if session.demo_step_index < 0:
        st.caption(
            "Click 'Next' to start viewing the conversation. "
            "Each step shows one message exchange."
        )
        return

    scenario = session.demo_scenario
    messages_to_show = scenario.get_messages_up_to_step(session.demo_step_index)

    for idx, message in enumerate(messages_to_show):
        if message.sender == MessageSender.BOT:
            # Bot messages (our victim persona)
            with st.chat_message("assistant", avatar="\U0001f3ad"):  # Theater mask
                st.markdown(f"**{scenario.persona.name}:**")
                st.write(message.content)

                # Calculate turn number for bot messages
                turn = sum(
                    1
                    for m in messages_to_show[: idx + 1]
                    if m.sender == MessageSender.BOT
                )
                st.caption(f"Turn {turn}")
        else:
            # Scammer messages
            with st.chat_message("user", avatar="\U0001f4e7"):  # Envelope
                st.markdown("**Scammer:**")
                st.write(message.content)

                # Show IOCs extracted from this message
                if message.iocs_in_message:
                    with st.expander("IOCs detected in this message", expanded=False):
                        for ioc in message.iocs_in_message:
                            icon = ioc.ioc_type.icon
                            name = ioc.ioc_type.display_name
                            if ioc.is_high_value:
                                st.markdown(f":red[{icon} **{name}**]")
                            else:
                                st.markdown(f"{icon} **{name}**")
                            st.code(ioc.value, language=None)


def _render_demo_controls(session: SessionState) -> None:
    """Render demo navigation controls.

    Args:
        session: Current session state with demo scenario.
    """
    if session.demo_scenario is None:
        return

    col_next, col_end = st.columns([2, 1])

    with col_next:
        if session.can_advance_demo():
            if st.button("Next", type="primary", use_container_width=True):
                _handle_next_step()
                st.rerun()
        else:
            # Demo complete
            st.success(
                "Demo complete! You've seen all the exchanges in this scenario. "
                "In a real session, you would continue until the scammer stops "
                "responding or the conversation limit is reached."
            )

            if st.button("End Demo", type="primary", use_container_width=True):
                _handle_end_demo()
                st.rerun()

    with col_end:
        # Show progress
        if session.demo_step_index < 0:
            st.caption("Ready to start")
        else:
            progress = (session.demo_step_index + 1) / session.demo_total_steps
            step_text = f"{session.demo_step_index + 1}/{session.demo_total_steps}"
            st.progress(progress, text=step_text)
