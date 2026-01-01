"""Email input component for PhishGuard.

This module provides the email input form for users to paste suspicious
email content for analysis. It handles validation, character counting,
and triggers the analysis flow.

Requirements: US-001 acceptance criteria, US-019 (Demo Mode button)
"""

import streamlit as st

from phishguard.models import SessionStage, SessionState, create_initial_session_state
from phishguard.safety import InputSanitizer, UnsafeInputError

# Validation constants
MIN_CHARS = 10
MAX_CHARS = 50_000


def _initialize_session_state() -> None:
    """Initialize session state if not already present.

    This ensures all required session state keys exist before
    any UI components attempt to access them.
    Note: email_input_text is managed by Streamlit's widget key system.
    """
    if "app_state" not in st.session_state:
        st.session_state.app_state = create_initial_session_state()


def _get_validation_message(text: str) -> str | None:
    """Get validation message for the current input text.

    Args:
        text: The current email input text.

    Returns:
        Validation error message if invalid, None if valid.
    """
    char_count = len(text)

    if char_count == 0:
        return None  # No message for empty input

    if char_count < MIN_CHARS:
        return f"Email must be at least {MIN_CHARS} characters"

    if char_count > MAX_CHARS:
        return f"Email must not exceed {MAX_CHARS:,} characters"

    return None


def _is_input_valid(text: str) -> bool:
    """Check if input text passes validation rules.

    Args:
        text: The email input text to validate.

    Returns:
        True if input is valid (10-50,000 chars), False otherwise.
    """
    char_count = len(text)
    return MIN_CHARS <= char_count <= MAX_CHARS


def _handle_analyze_click() -> None:
    """Handle the Analyze button click.

    This callback sanitizes the input and updates session state
    to trigger the analysis stage. Called via st.button on_click.
    """
    text = st.session_state.email_input_text

    if not _is_input_valid(text):
        return

    try:
        sanitizer = InputSanitizer()
        sanitized_content = sanitizer.sanitize(text)

        # Update session state for analysis
        session: SessionState = st.session_state.app_state
        session.email_content = sanitized_content
        session.stage = SessionStage.ANALYZING

    except UnsafeInputError as e:
        st.session_state.sanitization_error = str(e)
    except ValueError as e:
        st.session_state.sanitization_error = str(e)


def _handle_demo_mode_click() -> None:
    """Handle the Demo Mode button click.

    Transitions to the demo scenario selection stage (US-019).
    """
    session: SessionState = st.session_state.app_state
    session.stage = SessionStage.DEMO_SELECT


def render_email_input() -> None:
    """Render the email input component.

    This component provides:
    - A text area for pasting phishing email content
    - Character counter (current/max)
    - Validation messages for input length
    - Analyze button (disabled when invalid)
    - Spinner during analysis

    Updates st.session_state directly with:
    - session.email_content: sanitized email text
    - session.stage: transitions to ANALYZING on submit
    """
    _initialize_session_state()

    session: SessionState = st.session_state.app_state

    # Show spinner if currently analyzing
    if session.stage == SessionStage.ANALYZING:
        with st.spinner("Analyzing email content..."):
            # The actual analysis will be handled by the parent app
            # This spinner displays while stage is ANALYZING
            st.info("Analysis in progress. Please wait...")
        return

    # Only render input form during INPUT stage
    if session.stage != SessionStage.INPUT:
        return

    # Display any sanitization errors from previous attempt
    if "sanitization_error" in st.session_state and st.session_state.sanitization_error:
        st.error(st.session_state.sanitization_error)
        st.session_state.sanitization_error = None

    # Email input text area - capture return value for immediate use
    current_text = st.text_area(
        label="Email Content",
        placeholder="Paste phishing email content here...",
        height=300,
        key="email_input_text",
        label_visibility="collapsed",
    )

    # Calculate character count from the widget's return value
    char_count = len(current_text)

    # Character counter display
    counter_col, validation_col = st.columns([1, 3])

    with counter_col:
        st.caption(f"{char_count:,} / {MAX_CHARS:,}")

    # Validation message
    with validation_col:
        validation_message = _get_validation_message(current_text)
        if validation_message:
            st.warning(validation_message)

    # Analyze button
    is_valid = _is_input_valid(current_text)

    st.button(
        label="Analyze",
        type="primary",
        disabled=not is_valid,
        on_click=_handle_analyze_click,
        use_container_width=True,
    )

    # Demo Mode section (US-019)
    st.divider()
    st.caption("New to PhishGuard? Try a pre-loaded demo scenario:")

    st.button(
        label="Demo Mode",
        type="secondary",
        on_click=_handle_demo_mode_click,
        use_container_width=True,
        help="Browse pre-loaded scenarios without API calls",
    )
