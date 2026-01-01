"""Comprehensive unit tests for the Error Display UI component.

These tests verify that the error display component correctly:
1. Renders error messages using st.error()
2. Shows/hides help text based on configuration
3. Renders action buttons (retry, go back) conditionally
4. Handles button callbacks correctly when clicked
5. Uses proper button types (primary/secondary)
6. Handles various button combinations (both, retry only, go_back only, none)

Test Categories:
- Basic rendering tests
- Button configuration tests
- Callback execution tests
- Convenience function tests (render_api_error, render_configuration_error, render_rate_limit_error)
- Edge cases

Requirements: US-020 (API Error Handling)
"""

from unittest.mock import MagicMock, patch

import pytest

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_streamlit():
    """Mock all Streamlit functions used by the error display component."""
    with (
        patch("phishguard.ui.components.error_display.st") as mock_st,
    ):
        # Set up mock columns context manager
        mock_col_retry = MagicMock()
        mock_col_go_back = MagicMock()
        mock_st.columns.return_value = [mock_col_retry, mock_col_go_back]

        # Make columns usable as context managers
        mock_col_retry.__enter__ = MagicMock(return_value=mock_col_retry)
        mock_col_retry.__exit__ = MagicMock(return_value=False)
        mock_col_go_back.__enter__ = MagicMock(return_value=mock_col_go_back)
        mock_col_go_back.__exit__ = MagicMock(return_value=False)

        # Default button behavior - no click
        mock_st.button.return_value = False

        yield mock_st


@pytest.fixture
def mock_retry_callback() -> MagicMock:
    """Create a mock retry callback function."""
    return MagicMock()


@pytest.fixture
def mock_go_back_callback() -> MagicMock:
    """Create a mock go_back callback function."""
    return MagicMock()


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestRenderErrorDisplayBasicRendering:
    """Tests for basic error display rendering."""

    def test_renders_error_message(self, mock_streamlit: MagicMock) -> None:
        """Error message should be displayed using st.error()."""
        from phishguard.ui.components.error_display import render_error_display

        error_message = "Something went wrong!"

        render_error_display(error_message)

        mock_streamlit.error.assert_called_once_with(error_message)

    def test_renders_help_text_by_default(self, mock_streamlit: MagicMock) -> None:
        """Help text should be shown by default."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("An error occurred")

        mock_streamlit.caption.assert_called_once()
        caption_text = mock_streamlit.caption.call_args[0][0]
        assert "internet connection" in caption_text.lower()
        assert "try again later" in caption_text.lower()

    def test_hides_help_text_when_disabled(self, mock_streamlit: MagicMock) -> None:
        """Help text should not be shown when show_help_text=False."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("An error occurred", show_help_text=False)

        mock_streamlit.caption.assert_not_called()

    def test_renders_without_buttons_when_no_callbacks(
        self, mock_streamlit: MagicMock
    ) -> None:
        """No buttons should be rendered when no callbacks are provided."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("An error occurred")

        mock_streamlit.button.assert_not_called()
        mock_streamlit.columns.assert_not_called()


class TestRenderErrorDisplayButtonConfiguration:
    """Tests for button configuration scenarios."""

    def test_renders_only_retry_button(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Only retry button should be rendered when only on_retry is provided."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("Error", on_retry=mock_retry_callback)

        # Should call button once with primary type
        mock_streamlit.button.assert_called_once()
        call_kwargs = mock_streamlit.button.call_args
        assert call_kwargs[0][0] == "Try again"
        assert call_kwargs[1]["type"] == "primary"

        # Should NOT use columns for single button
        mock_streamlit.columns.assert_not_called()

    def test_renders_only_go_back_button(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Only go_back button should be rendered when only on_go_back is provided."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("Error", on_go_back=mock_go_back_callback)

        # Should call button once with secondary type
        mock_streamlit.button.assert_called_once()
        call_kwargs = mock_streamlit.button.call_args
        assert call_kwargs[0][0] == "Go back"
        assert call_kwargs[1]["type"] == "secondary"

        # Should NOT use columns for single button
        mock_streamlit.columns.assert_not_called()

    def test_renders_both_buttons_in_columns(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Both buttons should be rendered in columns when both callbacks provided."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display(
            "Error",
            on_retry=mock_retry_callback,
            on_go_back=mock_go_back_callback,
        )

        # Should use columns for two buttons
        mock_streamlit.columns.assert_called_once_with(2)

        # Should call button twice
        assert mock_streamlit.button.call_count == 2

    def test_custom_retry_label(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Custom retry label should be used when provided."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display(
            "Error",
            on_retry=mock_retry_callback,
            retry_label="Retry operation",
        )

        call_args = mock_streamlit.button.call_args
        assert call_args[0][0] == "Retry operation"

    def test_custom_go_back_label(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Custom go_back label should be used when provided."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display(
            "Error",
            on_go_back=mock_go_back_callback,
            go_back_label="Return home",
        )

        call_args = mock_streamlit.button.call_args
        assert call_args[0][0] == "Return home"


class TestRenderErrorDisplayCallbackExecution:
    """Tests for callback execution when buttons are clicked."""

    def test_retry_callback_executed_on_click(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Retry callback should be executed when retry button is clicked."""
        from phishguard.ui.components.error_display import render_error_display

        # Simulate button click
        mock_streamlit.button.return_value = True

        render_error_display("Error", on_retry=mock_retry_callback)

        mock_retry_callback.assert_called_once()

    def test_go_back_callback_executed_on_click(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Go_back callback should be executed when go_back button is clicked."""
        from phishguard.ui.components.error_display import render_error_display

        # Simulate button click
        mock_streamlit.button.return_value = True

        render_error_display("Error", on_go_back=mock_go_back_callback)

        mock_go_back_callback.assert_called_once()

    def test_retry_callback_not_executed_without_click(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Retry callback should not be executed when button is not clicked."""
        from phishguard.ui.components.error_display import render_error_display

        # Button not clicked (default)
        mock_streamlit.button.return_value = False

        render_error_display("Error", on_retry=mock_retry_callback)

        mock_retry_callback.assert_not_called()

    def test_go_back_callback_not_executed_without_click(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Go_back callback should not be executed when button is not clicked."""
        from phishguard.ui.components.error_display import render_error_display

        # Button not clicked (default)
        mock_streamlit.button.return_value = False

        render_error_display("Error", on_go_back=mock_go_back_callback)

        mock_go_back_callback.assert_not_called()


class TestRenderApiError:
    """Tests for the render_api_error convenience function."""

    def test_displays_api_error_message(self, mock_streamlit: MagicMock) -> None:
        """Should display the standard API error message."""
        from phishguard.ui.components.error_display import render_api_error

        render_api_error()

        mock_streamlit.error.assert_called_once()
        error_message = mock_streamlit.error.call_args[0][0]
        assert "unable to connect" in error_message.lower()
        assert "ai service" in error_message.lower()

    def test_shows_help_text(self, mock_streamlit: MagicMock) -> None:
        """Should show help text for API errors."""
        from phishguard.ui.components.error_display import render_api_error

        render_api_error()

        mock_streamlit.caption.assert_called_once()

    def test_passes_retry_callback(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Should pass retry callback to render_error_display."""
        from phishguard.ui.components.error_display import render_api_error

        render_api_error(on_retry=mock_retry_callback)

        mock_streamlit.button.assert_called()

    def test_passes_go_back_callback(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Should pass go_back callback to render_error_display."""
        from phishguard.ui.components.error_display import render_api_error

        render_api_error(on_go_back=mock_go_back_callback)

        mock_streamlit.button.assert_called()


class TestRenderConfigurationError:
    """Tests for the render_configuration_error convenience function."""

    def test_displays_configuration_error_header(
        self, mock_streamlit: MagicMock
    ) -> None:
        """Should display 'Configuration Error' header."""
        from phishguard.ui.components.error_display import render_configuration_error

        render_configuration_error()

        mock_streamlit.error.assert_called_once_with("Configuration Error")

    def test_displays_configuration_info(self, mock_streamlit: MagicMock) -> None:
        """Should display configuration instructions."""
        from phishguard.ui.components.error_display import render_configuration_error

        render_configuration_error()

        mock_streamlit.info.assert_called_once()
        info_text = mock_streamlit.info.call_args[0][0]
        assert "OPENAI_API_KEY" in info_text
        assert ".env" in info_text

    def test_no_button_without_callback(self, mock_streamlit: MagicMock) -> None:
        """Should not render button when no callback is provided."""
        from phishguard.ui.components.error_display import render_configuration_error

        render_configuration_error()

        mock_streamlit.button.assert_not_called()

    def test_renders_go_back_button_with_callback(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Should render go_back button when callback is provided."""
        from phishguard.ui.components.error_display import render_configuration_error

        render_configuration_error(on_go_back=mock_go_back_callback)

        mock_streamlit.button.assert_called_once()
        call_args = mock_streamlit.button.call_args
        assert call_args[0][0] == "Go back"
        assert call_args[1]["type"] == "secondary"

    def test_go_back_callback_executed_on_click(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Go_back callback should be executed when button is clicked."""
        from phishguard.ui.components.error_display import render_configuration_error

        mock_streamlit.button.return_value = True

        render_configuration_error(on_go_back=mock_go_back_callback)

        mock_go_back_callback.assert_called_once()


class TestRenderRateLimitError:
    """Tests for the render_rate_limit_error convenience function."""

    def test_displays_rate_limit_error_message(
        self, mock_streamlit: MagicMock
    ) -> None:
        """Should display the standard rate limit error message."""
        from phishguard.ui.components.error_display import render_rate_limit_error

        render_rate_limit_error()

        mock_streamlit.error.assert_called_once()
        error_message = mock_streamlit.error.call_args[0][0]
        assert "rate limit" in error_message.lower()

    def test_uses_custom_retry_label(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Should use 'Try again (wait a moment)' as retry label."""
        from phishguard.ui.components.error_display import render_rate_limit_error

        render_rate_limit_error(on_retry=mock_retry_callback)

        call_args = mock_streamlit.button.call_args
        assert "wait a moment" in call_args[0][0].lower()

    def test_displays_rate_limit_specific_caption(
        self, mock_streamlit: MagicMock
    ) -> None:
        """Should display rate-limit specific help text."""
        from phishguard.ui.components.error_display import render_rate_limit_error

        render_rate_limit_error()

        # rate_limit_error calls caption directly (not through show_help_text)
        mock_streamlit.caption.assert_called()
        caption_text = mock_streamlit.caption.call_args[0][0]
        assert "high demand" in caption_text.lower()

    def test_passes_retry_callback(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Should pass retry callback to render_error_display."""
        from phishguard.ui.components.error_display import render_rate_limit_error

        render_rate_limit_error(on_retry=mock_retry_callback)

        mock_streamlit.button.assert_called()

    def test_passes_go_back_callback(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Should pass go_back callback to render_error_display."""
        from phishguard.ui.components.error_display import render_rate_limit_error

        render_rate_limit_error(on_go_back=mock_go_back_callback)

        mock_streamlit.button.assert_called()


class TestRenderErrorDisplayEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_error_message(self, mock_streamlit: MagicMock) -> None:
        """Should handle empty error message."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("")

        mock_streamlit.error.assert_called_once_with("")

    def test_long_error_message(self, mock_streamlit: MagicMock) -> None:
        """Should handle long error messages."""
        from phishguard.ui.components.error_display import render_error_display

        long_message = "Error: " + "x" * 1000

        render_error_display(long_message)

        mock_streamlit.error.assert_called_once_with(long_message)

    def test_unicode_error_message(self, mock_streamlit: MagicMock) -> None:
        """Should handle unicode characters in error message."""
        from phishguard.ui.components.error_display import render_error_display

        unicode_message = "Error occurred during processing"

        render_error_display(unicode_message)

        mock_streamlit.error.assert_called_once_with(unicode_message)

    def test_special_characters_in_error_message(
        self, mock_streamlit: MagicMock
    ) -> None:
        """Should handle special characters in error message."""
        from phishguard.ui.components.error_display import render_error_display

        special_message = "Error: <script>alert('xss')</script> & \"quotes\""

        render_error_display(special_message)

        mock_streamlit.error.assert_called_once_with(special_message)

    def test_callback_with_exception(
        self,
        mock_streamlit: MagicMock,
    ) -> None:
        """Should propagate exceptions from callbacks."""
        from phishguard.ui.components.error_display import render_error_display

        def failing_callback():
            raise ValueError("Callback failed")

        mock_streamlit.button.return_value = True

        with pytest.raises(ValueError, match="Callback failed"):
            render_error_display("Error", on_retry=failing_callback)

    def test_both_buttons_custom_labels(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Should use custom labels for both buttons."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display(
            "Error",
            on_retry=mock_retry_callback,
            on_go_back=mock_go_back_callback,
            retry_label="Retry now",
            go_back_label="Cancel",
        )

        # Both buttons should be called
        assert mock_streamlit.button.call_count == 2

        # Check that custom labels are used
        call_args_list = mock_streamlit.button.call_args_list
        labels = [call[0][0] for call in call_args_list]
        assert "Retry now" in labels
        assert "Cancel" in labels


class TestRenderErrorDisplayButtonTypes:
    """Tests for correct button type assignments."""

    def test_retry_button_is_primary_type(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
    ) -> None:
        """Retry button should use 'primary' type."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("Error", on_retry=mock_retry_callback)

        call_kwargs = mock_streamlit.button.call_args[1]
        assert call_kwargs["type"] == "primary"

    def test_go_back_button_is_secondary_type(
        self,
        mock_streamlit: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Go_back button should use 'secondary' type."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display("Error", on_go_back=mock_go_back_callback)

        call_kwargs = mock_streamlit.button.call_args[1]
        assert call_kwargs["type"] == "secondary"

    def test_both_buttons_use_full_container_width(
        self,
        mock_streamlit: MagicMock,
        mock_retry_callback: MagicMock,
        mock_go_back_callback: MagicMock,
    ) -> None:
        """Both buttons should use full container width when displayed together."""
        from phishguard.ui.components.error_display import render_error_display

        render_error_display(
            "Error",
            on_retry=mock_retry_callback,
            on_go_back=mock_go_back_callback,
        )

        # Both button calls should have use_container_width=True
        for call in mock_streamlit.button.call_args_list:
            assert call[1].get("use_container_width") is True
