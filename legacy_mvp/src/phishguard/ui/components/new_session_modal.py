"""New session confirmation modal component for PhishGuard.

This module provides a modal dialog to confirm starting a new session,
warning users that unsaved data will be lost.

Requirements: US-023 (New Session Confirmation)
"""

import streamlit as st

from phishguard.models import SessionState


@st.dialog("Start New Session")
def _new_session_dialog(session: SessionState) -> None:
    """Render the new session confirmation dialog content.

    This function is decorated with @st.dialog to create a modal overlay.
    It displays a warning message and confirmation/cancel buttons.

    Args:
        session: The current session state object.
    """
    st.warning(
        "Are you sure you want to start a new session? "
        "Any unsaved data will be lost."
    )

    # Button row using columns for horizontal layout
    col_cancel, col_confirm = st.columns(2)

    with col_cancel:
        if st.button("Cancel", type="secondary", use_container_width=True):
            session.show_new_session_confirmation = False
            st.rerun()

    with col_confirm:
        if st.button("Confirm", type="primary", use_container_width=True):
            session.reset()
            st.rerun()


def render_new_session_modal(session: SessionState) -> None:
    """Render the new session confirmation modal if triggered.

    This component checks the session state flag and displays a modal
    dialog asking the user to confirm they want to start a new session.
    The modal warns that unsaved data will be lost.

    The modal provides two actions:
    - Confirm: Calls session.reset() to clear all session data and restart
    - Cancel: Closes the modal without any changes

    Args:
        session: The current session state object. The modal only renders
            when session.show_new_session_confirmation is True.

    Example:
        >>> session = st.session_state.app_state
        >>> render_new_session_modal(session)
    """
    if session.show_new_session_confirmation:
        _new_session_dialog(session)
