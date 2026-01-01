"""Error Display UI component for PhishGuard.

This module provides a reusable Streamlit component for displaying
user-friendly error messages with optional retry and navigation actions.
It ensures consistent error handling UX across the application while
hiding technical details (stack traces) from end users.

Requirements: US-020 (API Error Handling)
"""

from collections.abc import Callable

import streamlit as st


def render_error_display(
    error_message: str,
    *,
    on_retry: Callable[[], None] | None = None,
    on_go_back: Callable[[], None] | None = None,
    retry_label: str = "Try again",
    go_back_label: str = "Go back",
    show_help_text: bool = True,
) -> None:
    """Render a user-friendly error display with optional action buttons.

    Displays an error message in a styled container with optional "Try again"
    and "Go back" buttons. The component is designed to provide helpful
    context without exposing technical details like stack traces.

    Args:
        error_message: A user-friendly error message describing what went wrong.
            Should NOT contain raw exception messages or stack traces.
        on_retry: Optional callback function to execute when "Try again" is clicked.
            If None, the retry button is not shown.
        on_go_back: Optional callback function to execute when "Go back" is clicked.
            If None, the go back button is not shown.
        retry_label: Custom label for the retry button. Defaults to "Try again".
        go_back_label: Custom label for the go back button. Defaults to "Go back".
        show_help_text: Whether to show helpful context below the error message.
            Defaults to True.

    Example:
        >>> def handle_retry():
        ...     st.session_state.should_retry = True
        ...     st.rerun()
        >>> def handle_go_back():
        ...     st.session_state.app_state.stage = SessionStage.INPUT
        ...     st.rerun()
        >>> render_error_display(
        ...     error_message="Unable to connect to the AI service.",
        ...     on_retry=handle_retry,
        ...     on_go_back=handle_go_back,
        ... )
    """
    # Display the error message
    st.error(error_message)

    # Show helpful context if enabled
    if show_help_text:
        st.caption(
            "If this issue persists, please check your internet connection "
            "or try again later."
        )

    # Render action buttons if any callbacks are provided
    has_retry = on_retry is not None
    has_go_back = on_go_back is not None

    if has_retry or has_go_back:
        # Use columns for horizontal button layout
        if has_retry and has_go_back:
            # Both buttons - equal width columns
            col_retry, col_go_back = st.columns(2)

            with col_retry:
                if st.button(retry_label, type="primary", use_container_width=True):
                    on_retry()

            with col_go_back:
                if st.button(go_back_label, type="secondary", use_container_width=True):
                    on_go_back()

        elif has_retry:
            # Only retry button
            if st.button(retry_label, type="primary"):
                on_retry()

        else:
            # Only go back button
            if st.button(go_back_label, type="secondary"):
                on_go_back()


def render_api_error(
    *,
    on_retry: Callable[[], None] | None = None,
    on_go_back: Callable[[], None] | None = None,
) -> None:
    """Render a standardized API error display.

    Convenience function for displaying API-related errors with
    pre-configured messaging appropriate for AI service failures.

    Args:
        on_retry: Optional callback for retry action.
        on_go_back: Optional callback for navigation action.

    Example:
        >>> render_api_error(
        ...     on_retry=lambda: st.rerun(),
        ...     on_go_back=lambda: reset_to_input_stage(),
        ... )
    """
    render_error_display(
        error_message="Unable to connect to the AI service. Please try again.",
        on_retry=on_retry,
        on_go_back=on_go_back,
        show_help_text=True,
    )


def render_configuration_error(
    *,
    on_go_back: Callable[[], None] | None = None,
) -> None:
    """Render a standardized configuration error display.

    Displays an error message indicating a configuration issue,
    typically related to missing or invalid API keys.

    Args:
        on_go_back: Optional callback for navigation action.

    Example:
        >>> render_configuration_error(
        ...     on_go_back=lambda: reset_to_input_stage(),
        ... )
    """
    st.error("Configuration Error")
    st.info(
        "The AI service is not properly configured. "
        "Please ensure the OPENAI_API_KEY environment variable is set correctly.\n\n"
        "You can configure this by:\n"
        "1. Creating a `.env` file with `OPENAI_API_KEY=your-key-here`\n"
        "2. Or setting it in your shell: `export OPENAI_API_KEY=your-key-here`"
    )

    if on_go_back is not None:
        if st.button("Go back", type="secondary"):
            on_go_back()


def render_rate_limit_error(
    *,
    on_retry: Callable[[], None] | None = None,
    on_go_back: Callable[[], None] | None = None,
) -> None:
    """Render a standardized rate limit error display.

    Displays an error message indicating the API rate limit has been reached,
    with appropriate guidance for the user.

    Args:
        on_retry: Optional callback for retry action.
        on_go_back: Optional callback for navigation action.

    Example:
        >>> render_rate_limit_error(
        ...     on_retry=lambda: st.rerun(),
        ... )
    """
    render_error_display(
        error_message="Rate limit reached. The AI service is temporarily unavailable.",
        on_retry=on_retry,
        on_go_back=on_go_back,
        retry_label="Try again (wait a moment)",
        show_help_text=False,
    )
    st.caption(
        "The service is experiencing high demand. "
        "Please wait a moment before trying again."
    )
