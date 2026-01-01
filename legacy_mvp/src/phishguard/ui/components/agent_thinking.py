"""Agent Thinking UI component for displaying agent reasoning.

This module provides a Streamlit component that renders a collapsible
"Agent Thinking" panel showing the agent's strategic reasoning, including
the turn goal, selected tactic, and detailed reasoning.
"""

import streamlit as st

from phishguard.models import AgentThinking


def render_agent_thinking(thinking: AgentThinking | None) -> None:
    """Render the Agent Thinking panel as a collapsible expander.

    Displays the agent's strategic thinking including turn goal,
    selected tactic, and reasoning. The panel is collapsed by default
    per PRD requirements (FR-024).

    Args:
        thinking: The AgentThinking data to display, or None if not available.

    Example:
        >>> thinking = AgentThinking(
        ...     turn_goal="Extract payment method",
        ...     selected_tactic="Ask Questions",
        ...     reasoning="The scammer mentioned wire transfer..."
        ... )
        >>> render_agent_thinking(thinking)
    """
    with st.expander("Agent Thinking", expanded=False):
        if thinking is None:
            st.caption(
                "No agent thinking available yet. "
                "Generate a response to see the agent's reasoning."
            )
            return

        # Turn Goal section
        st.markdown("**Turn Goal**")
        st.info(thinking.turn_goal)

        # Selected Tactic section
        st.markdown("**Selected Tactic**")
        # Map tactics to appropriate icons/colors
        tactic_icons = {
            "Show Interest": "eye",
            "Ask Questions": "question",
            "Build Trust": "handshake",
            "Extend Conversation": "clock",
            "Extract Intel": "search",
        }
        tactic_icon = tactic_icons.get(thinking.selected_tactic, "lightbulb")
        st.markdown(f":{tactic_icon}: {thinking.selected_tactic}")

        # Reasoning section
        st.markdown("**Reasoning**")
        st.write(thinking.reasoning)
