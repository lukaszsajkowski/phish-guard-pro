# ruff: noqa: E402
"""PhishGuard - Main Streamlit Application.

This module provides the main entry point for the PhishGuard Streamlit
application. It handles page configuration, session state initialization,
and stage-based routing to appropriate UI components.

Run with: uv run streamlit run src/phishguard/ui/app.py
"""

import asyncio
import os

import streamlit as st
from dotenv import load_dotenv
from st_copy_to_clipboard import st_copy_to_clipboard

# Load environment variables from .env file
# This MUST be called before importing phishguard modules that use env vars
load_dotenv()

from phishguard.agents import (
    ClassificationError,
    ConversationAgent,
    IntelCollector,
    PersonaEngine,
    ProfilerAgent,
    ResponseGenerationError,
)
from phishguard.llm import LLMConfigurationError
from phishguard.models import (
    ConversationMessage,
    MessageSender,
    SessionStage,
    SessionState,
    create_initial_session_state,
)
from phishguard.safety import (
    InputSanitizer,
    OutputValidator,
    UnmaskingDetector,
    UnsafeInputError,
)
from phishguard.ui.components.agent_thinking import render_agent_thinking
from phishguard.ui.components.demo_selector import render_demo_selector
from phishguard.ui.components.demo_viewer import render_demo_viewer
from phishguard.ui.components.email_input import render_email_input
from phishguard.ui.components.error_display import (
    render_api_error,
    render_configuration_error,
    render_error_display,
    render_rate_limit_error,
)
from phishguard.ui.components.new_session_modal import render_new_session_modal

# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="PhishGuard",
    page_icon="\U0001f6e1\ufe0f",  # Shield emoji
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_custom_css() -> None:
    """Inject custom CSS for responsive interface styling (US-024).

    This function adds custom CSS rules to ensure the interface is
    responsive and works well on desktop screens (1024px+ width).
    Uses st.markdown with unsafe_allow_html=True for CSS injection.
    """
    st.markdown(
        """
        <style>
        /* US-024: Interface Responsiveness */

        /* Set minimum width for main content area */
        .main .block-container {
            min-width: 1024px;
            max-width: 100%;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        /* Prevent text overflow in all text elements */
        .stMarkdown, .stText, .stCaption, p, span, div {
            word-wrap: break-word;
            overflow-wrap: break-word;
            word-break: break-word;
        }

        /* Ensure chat messages are responsive and don't require horizontal scroll */
        .stChatMessage {
            max-width: 100%;
            overflow-x: hidden;
        }

        .stChatMessage [data-testid="stMarkdownContainer"] {
            max-width: 100%;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        /* Code blocks should wrap or scroll gracefully */
        .stChatMessage pre, .stChatMessage code {
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
            max-width: 100%;
        }

        /* Ensure code blocks in sidebar also handle overflow */
        [data-testid="stSidebar"] pre,
        [data-testid="stSidebar"] code {
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-x: auto;
            max-width: 100%;
        }

        /* Prevent button overlap on smaller screens */
        .stButton > button {
            white-space: nowrap;
            min-width: fit-content;
        }

        /* Button containers should wrap if needed */
        [data-testid="column"] {
            min-width: 0;
        }

        /* Sidebar styling for narrower screens */
        [data-testid="stSidebar"] {
            min-width: 250px;
            max-width: 350px;
        }

        [data-testid="stSidebar"] .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }

        /* Ensure sidebar content doesn't overflow */
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
            max-width: 100%;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        /* Metric values should not overflow */
        [data-testid="stMetricValue"] {
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        /* Text areas should be responsive */
        .stTextArea textarea {
            max-width: 100%;
        }

        /* Expander content should be responsive */
        .streamlit-expanderContent {
            max-width: 100%;
            overflow-x: auto;
        }

        /* Download buttons should not overflow */
        .stDownloadButton > button {
            max-width: 100%;
            white-space: normal;
            word-wrap: break-word;
        }

        /* Ensure columns don't cause horizontal scroll on main content */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        /* Long URLs and IOC values should wrap */
        .stCode {
            max-width: 100%;
            overflow-x: auto;
        }

        .stCode code {
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_session_state() -> None:
    """Initialize session state with default values if not present.

    This function ensures that the SessionState model is properly
    initialized in st.session_state before any UI components render.
    Must be called at the start of every Streamlit rerun.

    Also handles migration of old session state objects that may be
    missing newly added fields.
    """
    if "app_state" not in st.session_state:
        st.session_state.app_state = create_initial_session_state()
    else:
        # Handle migration: check if session state has all required fields
        # If not, create a fresh session state to avoid attribute errors
        current_state = st.session_state.app_state
        if not hasattr(current_state, "extracted_iocs"):
            st.session_state.app_state = create_initial_session_state()


def get_session_state() -> SessionState:
    """Retrieve the current session state.

    Returns:
        The current SessionState instance from st.session_state.
    """
    return st.session_state.app_state


def render_sidebar() -> None:
    """Render the sidebar with Intel Dashboard and classification info."""
    session_state = get_session_state()

    with st.sidebar:
        st.header("Intel Dashboard")

        # Show demo mode indicator (US-019)
        if session_state.is_demo_mode:
            st.info("Demo Mode - No API calls")

        # Attack Type section
        st.subheader("Attack Type")
        if session_state.classification_result is not None:
            result = session_state.classification_result

            # Display attack type with human-readable name
            st.markdown(f"**{result.attack_type.display_name}**")

            # Display confidence with color coding
            confidence = result.confidence
            confidence_text = f"{confidence:.1f}%"

            if confidence >= 70:
                st.success(f"Confidence: {confidence_text}")
            elif confidence >= 30:
                st.warning(f"Confidence: {confidence_text}")
            else:
                st.error(f"Confidence: {confidence_text}")

            # Display classification time
            st.caption(f"Classification time: {result.classification_time_ms}ms")

            # Show fallback model notice if used
            if session_state.used_fallback_model:
                st.info("Used fallback model due to primary model unavailability.")
        else:
            st.caption("Classification not yet available.")

        st.divider()

        # Collected IOC section
        st.subheader("Collected IOC")
        if session_state.extracted_iocs:
            # Display IOCs with icons
            for ioc in session_state.extracted_iocs:
                # Color coding: red for high-value, default for others
                if ioc.is_high_value:
                    st.markdown(
                        f":red[{ioc.ioc_type.icon} **{ioc.ioc_type.display_name}**]"
                    )
                    st.code(ioc.value, language=None)
                else:
                    st.markdown(f"{ioc.ioc_type.icon} **{ioc.ioc_type.display_name}**")
                    st.code(ioc.value, language=None)

            # Summary
            high_value = session_state.high_value_ioc_count
            total = len(session_state.extracted_iocs)
            if high_value > 0:
                st.success(f"Total: {total} IOCs ({high_value} high-value)")
            else:
                st.info(f"Total: {total} IOCs extracted")
        else:
            st.caption(
                "No IOCs extracted yet. Paste scammer responses to extract intel."
            )

        st.divider()

        # Risk Score section
        st.subheader("Risk Score")
        risk = session_state.risk_score
        risk_label = f"Risk Level: {risk.value}/10 - {risk.level.display_name}"

        if risk.level.color == "green":
            st.success(risk_label)
        elif risk.level.color == "yellow":
            st.warning(risk_label)
        else:  # red
            st.error(risk_label)

        # Risk factors in collapsed expander
        if risk.factors:
            with st.expander("Risk Factors", expanded=False):
                for factor in risk.factors:
                    st.write(f"- {factor}")
        else:
            st.caption("No risk factors identified yet.")

        st.divider()

        # Timeline section
        st.subheader("Timeline")
        if session_state.extracted_iocs:
            # Sort IOCs by timestamp, newest first
            sorted_iocs = sorted(
                session_state.extracted_iocs,
                key=lambda x: x.timestamp,
                reverse=True,
            )

            for ioc in sorted_iocs:
                # Format timestamp as HH:MM:SS
                time_str = ioc.timestamp.strftime("%H:%M:%S")
                icon = ioc.ioc_type.icon
                ioc_type_name = ioc.ioc_type.display_name

                # Display: icon **HH:MM:SS** - IOC Type
                st.markdown(f"{icon} **{time_str}** - {ioc_type_name}")

                # Truncate value to 20 chars with "..." if longer
                truncated_value = (
                    ioc.value[:20] + "..." if len(ioc.value) > 20 else ioc.value
                )
                turn_number = ioc.message_index + 1

                # Display: special character truncated_value (Turn N)
                st.caption(f"    {truncated_value} (Turn {turn_number})")
        else:
            st.caption("No extraction events yet.")

        # Export Data section (US-017, US-018)
        # Only show when session has been classified
        if session_state.is_classified:
            st.divider()
            st.subheader("Export Data")

            # Import export functions
            from phishguard.export import (
                export_iocs_csv,
                export_session_json,
                get_csv_filename,
                get_json_filename,
            )

            # Export JSON button (US-017)
            json_data = export_session_json(session_state)
            json_filename = get_json_filename()

            st.download_button(
                label="Export JSON",
                data=json_data,
                file_name=json_filename,
                mime="application/json",
                type="secondary",
                help="Download full session data including conversation history",
                key="sidebar_export_json",
            )

            # Export CSV button (US-018)
            if session_state.extracted_iocs:
                csv_data = export_iocs_csv(session_state.extracted_iocs)
                csv_filename = get_csv_filename()

                st.download_button(
                    label="Export IOCs (CSV)",
                    data=csv_data,
                    file_name=csv_filename,
                    mime="text/csv",
                    type="secondary",
                    help="Download IOCs in CSV format for import into security tools",
                    key="sidebar_export_csv",
                )
            else:
                st.button(
                    "Export IOCs (CSV)",
                    disabled=True,
                    help="No IOCs to export",
                    type="secondary",
                    key="sidebar_export_csv_disabled",
                )


def render_input_stage() -> None:
    """Render the email input stage UI.

    Displays the email input component for users to paste
    suspicious email content for analysis.
    """
    render_email_input()


def render_analyzing_stage() -> None:
    """Render the analyzing stage and perform classification.

    Calls the ProfilerAgent to classify the email content,
    updates session state with results, and transitions to
    the CLASSIFIED stage.

    Uses unified error display components (US-020) for consistent
    error handling UX without exposing raw stack traces.
    """
    session_state = get_session_state()

    def go_back_to_input() -> None:
        """Navigate back to the input stage."""
        session_state.stage = SessionStage.INPUT
        st.rerun()

    def retry_classification() -> None:
        """Retry the classification by triggering a rerun."""
        st.rerun()

    # Check for OPENAI_API_KEY before attempting classification
    if not os.environ.get("OPENAI_API_KEY"):
        render_configuration_error(on_go_back=go_back_to_input)
        return

    # Show analyzing UI
    with st.spinner("Analyzing email content..."):
        st.info("Profiler Agent is classifying the email...")

        try:
            # Create profiler agent and classify
            profiler = ProfilerAgent()
            result, used_fallback = asyncio.run(
                profiler.classify(session_state.email_content)
            )

            # Store results in session state
            session_state.classification_result = result
            session_state.used_fallback_model = used_fallback

            # Select persona based on attack type
            persona_engine = PersonaEngine(seed=session_state.faker_seed)
            session_state.persona_profile = persona_engine.select_persona(
                result.attack_type
            )

            # Transition to CLASSIFIED stage
            session_state.stage = SessionStage.CLASSIFIED
            st.rerun()

        except LLMConfigurationError:
            render_configuration_error(on_go_back=go_back_to_input)

        except ClassificationError:
            render_api_error(
                on_retry=retry_classification,
                on_go_back=go_back_to_input,
            )

        except Exception:
            render_api_error(
                on_retry=retry_classification,
                on_go_back=go_back_to_input,
            )


def render_classified_stage() -> None:
    """Render the classified stage with classification results.

    Displays the classification summary including attack type,
    confidence, and reasoning. Provides a button to continue
    to the conversation stage.
    """
    session_state = get_session_state()
    result = session_state.classification_result

    if result is None:
        st.error("No classification result available.")
        if st.button("Start Over"):
            session_state.stage = SessionStage.INPUT
            st.rerun()
        return

    # Display classification summary
    st.subheader("Classification Complete")

    # Create columns for layout
    col1, col2 = st.columns([2, 1])

    with col1:
        # Attack type display
        if result.is_phishing:
            st.error(f"Phishing Detected: {result.attack_type.display_name}")
        else:
            st.success("No Phishing Detected")

        # Confidence indicator
        confidence = result.confidence
        if confidence >= 70:
            confidence_status = "High"
        elif confidence >= 30:
            confidence_status = "Medium"
        else:
            confidence_status = "Low"

        st.metric(
            label="Confidence",
            value=f"{confidence:.1f}%",
            delta=confidence_status,
            delta_color="off",
        )

    with col2:
        st.metric(
            label="Classification Time",
            value=f"{result.classification_time_ms}ms",
        )

    # Display reasoning in an expander
    with st.expander("Classification Reasoning", expanded=True):
        st.write(result.reasoning)

    # Fallback model notice
    if session_state.used_fallback_model:
        st.info(
            "Note: Classification was performed using the fallback model "
            "due to primary model unavailability."
        )

    st.divider()

    # Display selected persona card
    if session_state.has_persona:
        st.subheader("Selected Persona")
        persona = session_state.persona_profile

        persona_col1, persona_col2 = st.columns([1, 2])

        with persona_col1:
            st.markdown(f"### {persona.name}")
            st.caption(f"Age {persona.age} | {persona.persona_type.display_name}")

        with persona_col2:
            st.markdown("**Communication Style:**")
            st.write(persona.style_description)

        with st.expander("Background", expanded=False):
            st.write(persona.background)

        st.divider()

    # Continue button
    if result.is_phishing:
        st.caption(
            "The Persona Engine has selected a believable victim profile. "
            "Ready to engage with the scammer."
        )
        if st.button("Continue to Conversation", type="primary"):
            session_state.stage = SessionStage.CONVERSATION
            st.rerun()
    else:
        # NOT_PHISHING warning UI
        st.warning(
            "This email doesn't appear to be phishing. "
            "Are you sure you want to continue?"
        )

        # Button layout using columns
        col_continue, col_reset = st.columns(2)

        with col_continue:
            if st.button("Continue anyway", type="secondary"):
                session_state.force_continue = True
                session_state.stage = SessionStage.CONVERSATION
                st.rerun()

        with col_reset:
            if st.button("Paste different email", type="primary"):
                st.session_state.app_state = create_initial_session_state()
                st.rerun()


def render_conversation_stage() -> None:
    """Render the conversation stage with chat interface.

    This stage shows the active chat interface with the scammer,
    including the Generate Response button, chat history, and
    message display.
    """
    session_state = get_session_state()

    # Validate that we have the required data
    if not session_state.has_persona or not session_state.is_classified:
        st.error("Missing required data. Please start over.")
        if st.button("Start Over"):
            st.session_state.app_state = create_initial_session_state()
            st.rerun()
        return

    # Check if end confirmation modal should be shown (US-015)
    if session_state.show_end_confirmation:
        _render_end_confirmation_modal(session_state)
        return

    # Header with turn counter and End button (US-015)
    header_col, end_col = st.columns([3, 1])

    with header_col:
        # Display turn counter with color coding (US-012, US-025)
        turn_display = session_state.turn_counter_display
        turn_color = session_state.turn_counter_color
        if turn_color == "red":
            st.subheader(f"Conversation - :red[{turn_display}]")
        elif turn_color == "yellow":
            st.subheader(f"Conversation - :orange[{turn_display}]")
        else:
            st.subheader(f"Conversation - {turn_display}")

    with end_col:
        # "End and summarize" button always visible (US-015)
        if st.button("End and summarize", type="secondary"):
            session_state.show_end_confirmation = True
            st.rerun()

    # Show the original phishing email in a collapsed expander
    with st.expander("Original Phishing Email", expanded=False):
        st.text(session_state.email_content)

    # Display Agent Thinking panel (collapsed by default per FR-024)
    render_agent_thinking(session_state.current_thinking)

    st.divider()

    # Display chat history
    _render_chat_history(session_state)

    # Show error message if there was a generation error (US-020)
    if session_state.generation_error:
        _render_generation_error(session_state)

    # Show Generate Response button if first response not yet generated
    if not session_state.has_first_response:
        st.divider()
        st.markdown("**Ready to engage with the scammer.**")
        st.caption(
            f"The bot will respond as **{session_state.persona_profile.name}** "
            f"({session_state.persona_profile.persona_type.display_name})."
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button(
                "Generate Response",
                type="primary",
                disabled=session_state.is_generating,
            ):
                _generate_first_response(session_state)

        # Show spinner while generating
        if session_state.is_generating:
            with st.spinner("Generating response in persona style..."):
                pass

    # Show scammer response input field after bot response is generated
    elif session_state.awaiting_scammer_response:
        st.divider()
        _render_scammer_input(session_state)

    # Show spinner while generating next response
    if session_state.is_generating and session_state.has_first_response:
        with st.spinner("Generating next response..."):
            pass


def _render_scammer_input(session_state: SessionState) -> None:
    """Render the scammer response input field.

    Displays a text area for pasting scammer responses with validation
    and a Send button to continue the conversation. Also shows modals
    for session limit (US-013) and unmasking detection (US-014).

    Args:
        session_state: Current session state.
    """
    # Check for unmasking warning (US-014) - takes priority
    if session_state.should_show_unmasking_warning:
        _render_unmasking_warning(session_state)
        return

    # Check for session limit warning (US-013)
    if session_state.should_show_limit_warning:
        _render_limit_warning(session_state)
        return

    st.markdown("**Paste Scammer Response**")
    st.caption(
        "Paste the scammer's reply below to continue the conversation. "
        "The Intel Collector will automatically scan for IOCs."
    )

    # Text area for scammer response
    scammer_input = st.text_area(
        "Scammer's response",
        height=150,
        max_chars=50000,
        key="scammer_response_input",
        label_visibility="collapsed",
        placeholder="Paste the scammer's response here...",
    )

    # Character count and validation
    char_count = len(scammer_input) if scammer_input else 0
    is_valid_length = 1 <= char_count <= 50000

    col_info, col_send = st.columns([3, 1])

    with col_info:
        if char_count == 0:
            st.caption("Enter scammer's response (1-50,000 characters)")
        elif not is_valid_length:
            st.error(f"Response must be 1-50,000 characters (currently {char_count:,})")
        else:
            st.caption(f"{char_count:,} characters")

    with col_send:
        send_disabled = not is_valid_length or session_state.is_generating
        if st.button("Send", type="primary", disabled=send_disabled):
            _handle_scammer_response(session_state, scammer_input)


def _render_limit_warning(session_state: SessionState) -> None:
    """Render the session limit reached warning (US-013).

    Displays a warning when the conversation reaches the turn limit,
    with options to extend or end the session.

    Args:
        session_state: Current session state.
    """
    st.warning(
        f"You have reached the conversation limit of {session_state.turn_limit} turns. "
        "Would you like to continue or end the session?"
    )

    col_continue, col_end = st.columns(2)

    with col_continue:
        if st.button("Continue (+10 turns)", type="secondary"):
            session_state.extend_limit(10)
            st.rerun()

    with col_end:
        if st.button("End and summarize", type="primary"):
            session_state.end_session()
            st.rerun()


def _render_unmasking_warning(session_state: SessionState) -> None:
    """Render the bot unmasking detection warning (US-014).

    Displays a warning when the scammer appears to have detected
    that they are talking to a bot, with options to summarize
    or continue anyway.

    Args:
        session_state: Current session state.
    """
    st.warning("It appears the scammer has ended the conversation.")

    # Show detected phrases in an expander
    if session_state.unmasking_phrases:
        with st.expander("Detected phrases", expanded=False):
            for phrase in session_state.unmasking_phrases:
                st.caption(f'- "{phrase}"')

    st.info(
        "The scammer may have realized they are talking to a bot. "
        "You can summarize the session or continue the conversation."
    )

    col_summarize, col_continue = st.columns(2)

    with col_summarize:
        if st.button("Summarize", type="primary"):
            session_state.end_session()
            st.rerun()

    with col_continue:
        if st.button("Continue anyway", type="secondary"):
            session_state.dismiss_unmasking_warning()
            st.rerun()


def _render_end_confirmation_modal(session_state: SessionState) -> None:
    """Render the end session confirmation modal (US-015).

    Displays a confirmation dialog when user clicks "End and summarize",
    allowing them to confirm or cancel the action.

    Args:
        session_state: Current session state.
    """
    st.subheader("End Session?")

    st.warning(
        "Are you sure you want to end this session? "
        "A summary report will be generated with all collected intelligence."
    )

    # Show current session stats
    st.info(
        f"Current session: {session_state.turn_count} turns, "
        f"{len(session_state.extracted_iocs)} IOCs extracted "
        f"({session_state.high_value_ioc_count} high-value)"
    )

    col_confirm, col_cancel = st.columns(2)

    with col_confirm:
        if st.button("Confirm End Session", type="primary"):
            session_state.end_session()
            st.rerun()

    with col_cancel:
        if st.button("Cancel", type="secondary"):
            session_state.show_end_confirmation = False
            st.rerun()


def _render_generation_error(session_state: SessionState) -> None:
    """Render generation error using the unified error display component (US-020).

    Determines the error type and renders the appropriate error display
    with retry and navigation options. Preserves conversation history.

    Args:
        session_state: Current session state with generation_error set.
    """
    error_msg = session_state.generation_error or ""

    def handle_retry() -> None:
        """Clear error and trigger regeneration."""
        session_state.generation_error = None
        # Regenerate based on conversation state
        if session_state.has_first_response:
            # Re-generate next response (scammer message already in history)
            _generate_next_response(session_state)
        else:
            # Re-generate first response
            _generate_first_response(session_state)

    def handle_go_back() -> None:
        """Clear error and stay in conversation (don't lose history)."""
        session_state.generation_error = None
        st.rerun()

    # Determine error type and render appropriate display
    if "configuration" in error_msg.lower() or "api key" in error_msg.lower():
        render_configuration_error(on_go_back=handle_go_back)
    elif "rate limit" in error_msg.lower():
        render_rate_limit_error(on_retry=handle_retry, on_go_back=handle_go_back)
    elif "connect" in error_msg.lower() or "api" in error_msg.lower():
        render_api_error(on_retry=handle_retry, on_go_back=handle_go_back)
    else:
        # Generic error with custom message
        render_error_display(
            error_message=f"Response generation failed: {error_msg}",
            on_retry=handle_retry,
            on_go_back=handle_go_back,
            retry_label="Try again",
            go_back_label="Dismiss",
        )


def _handle_scammer_response(session_state: SessionState, scammer_input: str) -> None:
    """Handle submission of a scammer response.

    Sanitizes input, adds to conversation history, extracts IOCs,
    checks for bot unmasking (US-014), and generates the next bot response.

    Args:
        session_state: Current session state.
        scammer_input: Raw scammer response text.
    """
    try:
        # Check for bot unmasking BEFORE sanitization (US-014)
        # This must run first because the sanitizer may remove phrases
        # that indicate unmasking (e.g., "stop playing games")
        unmasking_detector = UnmaskingDetector()
        unmasking_result = unmasking_detector.detect(scammer_input)

        if unmasking_result.is_unmasked:
            session_state.set_unmasking_detected(unmasking_result.matched_phrases)
            st.rerun()
            return

        # Sanitize the scammer input
        sanitizer = InputSanitizer()
        sanitized_content = sanitizer.sanitize(scammer_input)

        # Add scammer message to conversation history
        scammer_message = ConversationMessage(
            sender=MessageSender.SCAMMER,
            content=sanitized_content,
            turn_number=session_state.turn_count,
        )
        session_state.conversation_history.append(scammer_message)

        # Extract IOCs from scammer message
        collector = IntelCollector()
        message_index = len(session_state.conversation_history) - 1
        extraction_result = collector.extract(sanitized_content, message_index)

        # Add extracted IOCs to session
        if extraction_result.has_iocs:
            session_state.add_iocs(list(extraction_result.iocs))

        # Generate next bot response
        _generate_next_response(session_state)

    except UnsafeInputError as e:
        session_state.generation_error = f"Input rejected: {e}"
        st.rerun()

    except ValueError as e:
        session_state.generation_error = f"Invalid input: {e}"
        st.rerun()


def _generate_next_response(session_state: SessionState) -> None:
    """Generate the next bot response in the conversation.

    Args:
        session_state: Current session state with conversation history.
    """
    # Set generating flag
    session_state.is_generating = True
    session_state.generation_error = None

    try:
        # Create the conversation agent
        agent = ConversationAgent()

        # Generate the response with conversation history
        result = asyncio.run(
            agent.generate_response(
                persona=session_state.persona_profile,
                email_content=session_state.email_content,
                attack_type=session_state.classification_result.attack_type,
                conversation_history=session_state.conversation_history,
                is_first_response=False,
            )
        )

        # Store agent thinking for UI display
        session_state.current_thinking = result.thinking

        # Update fallback model flag if used
        if result.used_fallback_model:
            session_state.used_fallback_model = True

        # Add the bot message to conversation history
        bot_message = ConversationMessage(
            sender=MessageSender.BOT,
            content=result.content,
            turn_number=session_state.turn_count + 1,
        )
        session_state.conversation_history.append(bot_message)

        # Clear generating flag
        session_state.is_generating = False

        # Trigger rerun to show the response
        st.rerun()

    except LLMConfigurationError as e:
        session_state.is_generating = False
        session_state.generation_error = (
            f"API configuration error: {e}. Please check your OPENAI_API_KEY."
        )
        st.rerun()

    except ResponseGenerationError as e:
        session_state.is_generating = False
        session_state.generation_error = f"Failed to generate safe response: {e}"
        st.rerun()

    except Exception as e:
        session_state.is_generating = False
        session_state.generation_error = f"Unexpected error: {e}"
        st.rerun()


def _render_chat_history(session_state: SessionState) -> None:
    """Render the conversation history as a chat interface.

    Args:
        session_state: Current session state with conversation history.
    """
    if not session_state.conversation_history:
        st.caption("No messages yet. Click 'Generate Response' to start.")
        return

    for idx, message in enumerate(session_state.conversation_history):
        if message.is_bot_message:
            # Bot messages (our victim persona)
            with st.chat_message("assistant", avatar="\U0001f3ad"):  # Theater mask
                st.markdown(f"**{session_state.persona_profile.name}:**")

                # Check if this message is being edited
                if session_state.editing_message_index == idx:
                    # Editing mode - show textarea
                    edited_text = st.text_area(
                        "Edit response",
                        value=session_state.editing_content,
                        height=150,
                        key=f"edit_textarea_{idx}",
                        label_visibility="collapsed",
                    )

                    col_save, col_cancel = st.columns(2)
                    with col_save:
                        if st.button("Save", key=f"save_{idx}", type="primary"):
                            # Validate edited content
                            validator = OutputValidator()
                            result = validator.validate(edited_text)

                            if result.is_safe:
                                # Update the message
                                session_state.update_message_content(idx, edited_text)
                                session_state.clear_editing_state()
                                st.rerun()
                            else:
                                # Show error with violation details
                                st.error(
                                    f"Cannot save: Content failed safety check. "
                                    f"Violations: {result.violation_summary}"
                                )

                    with col_cancel:
                        if st.button("Cancel", key=f"cancel_{idx}"):
                            session_state.clear_editing_state()
                            st.rerun()
                else:
                    # Normal display mode
                    st.write(message.content)
                    st.caption(f"Turn {message.turn_number}")

                    # Button row with Edit and Copy (only show if not editing)
                    if not session_state.is_editing:
                        col_edit, col_copy = st.columns([1, 1])

                        with col_edit:
                            if st.button("Edit", key=f"edit_{idx}"):
                                session_state.editing_message_index = idx
                                session_state.editing_content = message.content
                                st.rerun()

                        with col_copy:
                            # st_copy_to_clipboard handles button, copy, and feedback
                            st_copy_to_clipboard(
                                message.content,
                                before_copy_label="Copy",
                                after_copy_label="Copied!",
                                key=f"copy_{idx}",
                            )
        else:
            # Scammer messages
            with st.chat_message("user", avatar="\U0001f4e7"):  # Envelope
                st.markdown("**Scammer:**")
                st.write(message.content)


def _generate_first_response(session_state: SessionState) -> None:
    """Generate the first response to the phishing email.

    Args:
        session_state: Current session state.
    """
    # Set generating flag
    session_state.is_generating = True
    session_state.generation_error = None

    try:
        # Create the conversation agent
        agent = ConversationAgent()

        # Generate the response
        result = asyncio.run(
            agent.generate_response(
                persona=session_state.persona_profile,
                email_content=session_state.email_content,
                attack_type=session_state.classification_result.attack_type,
                is_first_response=True,
            )
        )

        # Store the response
        session_state.current_response = result.content

        # Store agent thinking for UI display
        session_state.current_thinking = result.thinking

        # Update fallback model flag if used
        if result.used_fallback_model:
            session_state.used_fallback_model = True

        # Add the bot message to conversation history
        bot_message = ConversationMessage(
            sender=MessageSender.BOT,
            content=result.content,
            turn_number=1,
        )
        session_state.conversation_history = [bot_message]

        # Clear generating flag
        session_state.is_generating = False

        # Trigger rerun to show the response
        st.rerun()

    except LLMConfigurationError as e:
        session_state.is_generating = False
        session_state.generation_error = (
            f"API configuration error: {e}. Please check your OPENAI_API_KEY."
        )
        st.rerun()

    except ResponseGenerationError as e:
        session_state.is_generating = False
        session_state.generation_error = f"Failed to generate safe response: {e}"
        st.rerun()

    except Exception as e:
        session_state.is_generating = False
        session_state.generation_error = f"Unexpected error: {e}"
        st.rerun()


def render_summary_stage() -> None:
    """Render the session summary stage (US-016).

    This stage shows the session summary including:
    - Session metrics (exchanges, duration, attack type)
    - All collected IOCs
    - Safety Score (% safe responses)
    - Export buttons (JSON, CSV)
    - New session button
    """
    from phishguard.export import (
        export_iocs_csv,
        export_session_json,
        get_csv_filename,
        get_json_filename,
    )

    session_state = get_session_state()

    # Generate summary
    try:
        summary = session_state.generate_summary()
    except ValueError as e:
        st.error(f"Unable to generate summary: {e}")
        if st.button("Start New Session"):
            st.session_state.app_state = create_initial_session_state()
            st.rerun()
        return

    st.subheader("Session Summary")
    st.success("Session complete! Review the collected intelligence below.")

    st.divider()

    # Session Metrics Section
    st.markdown("### Session Metrics")

    # Use columns for metrics display
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Message Exchanges",
            value=summary.exchange_count,
        )

    with col2:
        st.metric(
            label="Duration",
            value=summary.formatted_duration,
        )

    with col3:
        st.metric(
            label="Attack Type",
            value=summary.attack_type.display_name,
        )

    # Second row of metrics
    col4, col5, col6 = st.columns(3)

    with col4:
        st.metric(
            label="Confidence",
            value=f"{summary.attack_confidence:.1f}%",
        )

    with col5:
        st.metric(
            label="Safety Score",
            value=summary.formatted_safety_score,
            help="Percentage of responses that passed safety validation",
        )

    with col6:
        delta_text = (
            f"{summary.high_value_ioc_count} high-value"
            if summary.high_value_ioc_count > 0
            else None
        )
        st.metric(
            label="IOCs Extracted",
            value=summary.ioc_count,
            delta=delta_text,
            delta_color="off",
        )

    st.divider()

    # Collected IOCs Section
    st.markdown("### Collected IOCs")

    if summary.iocs:
        for ioc in summary.iocs:
            # Color coding: red for high-value, default for others
            if ioc.is_high_value:
                st.markdown(
                    f":red[{ioc.ioc_type.icon} **{ioc.ioc_type.display_name}**]"
                )
                st.code(ioc.value, language=None)
            else:
                st.markdown(f"{ioc.ioc_type.icon} **{ioc.ioc_type.display_name}**")
                st.code(ioc.value, language=None)

            # Show context if available
            if ioc.context:
                with st.expander("Context", expanded=False):
                    st.caption(ioc.context)
    else:
        st.info("No IOCs were extracted during this session.")

    st.divider()

    # Conversation History (collapsed)
    st.markdown("### Conversation History")
    with st.expander("View full conversation", expanded=False):
        if session_state.conversation_history:
            for msg in session_state.conversation_history:
                if msg.is_bot_message:
                    persona_name = session_state.persona_profile.name
                    st.markdown(f"**{persona_name}** (Turn {msg.turn_number}):")
                    st.write(msg.content)
                else:
                    st.markdown(f"**Scammer** (Turn {msg.turn_number}):")
                    st.write(msg.content)
                st.caption("---")
        else:
            st.caption("No messages in conversation history.")

    st.divider()

    # Export Buttons
    st.markdown("### Export Data")

    col_json, col_csv = st.columns(2)

    with col_json:
        # Generate JSON export
        json_data = export_session_json(session_state)
        json_filename = get_json_filename()

        st.download_button(
            label="Export JSON",
            data=json_data,
            file_name=json_filename,
            mime="application/json",
            type="secondary",
            help="Download full session data including conversation history",
            key="summary_export_json",
        )

    with col_csv:
        # Generate CSV export
        if summary.iocs:
            csv_data = export_iocs_csv(list(summary.iocs))
            csv_filename = get_csv_filename()

            st.download_button(
                label="Export IOCs (CSV)",
                data=csv_data,
                file_name=csv_filename,
                mime="text/csv",
                type="secondary",
                help="Download IOCs in CSV format for import into security tools",
                key="summary_export_csv",
            )
        else:
            st.button(
                "Export IOCs (CSV)",
                disabled=True,
                help="No IOCs to export",
                type="secondary",
                key="summary_export_csv_disabled",
            )

    st.divider()

    # New Session Button
    if st.button("Start New Session", type="primary"):
        st.session_state.app_state = create_initial_session_state()
        st.rerun()


def render_demo_select_stage() -> None:
    """Render the demo scenario selection stage (US-019).

    Displays available demo scenarios for the user to choose from.
    """
    render_demo_selector()


def render_demo_stage() -> None:
    """Render the demo viewing stage (US-019).

    Displays the selected demo scenario for step-by-step browsing.
    """
    render_demo_viewer()


def render_main_content(session_state: SessionState) -> None:
    """Route to the appropriate stage component based on session state.

    Args:
        session_state: The current session state with stage information.
    """
    stage_renderers = {
        SessionStage.INPUT: render_input_stage,
        SessionStage.ANALYZING: render_analyzing_stage,
        SessionStage.CLASSIFIED: render_classified_stage,
        SessionStage.CONVERSATION: render_conversation_stage,
        SessionStage.SUMMARY: render_summary_stage,
        SessionStage.DEMO_SELECT: render_demo_select_stage,
        SessionStage.DEMO: render_demo_stage,
    }

    renderer = stage_renderers.get(session_state.stage)
    if renderer:
        renderer()
    else:
        st.error(f"Unknown session stage: {session_state.stage}")


def main() -> None:
    """Main application entry point.

    Initializes session state, renders the header and sidebar,
    and routes to the appropriate stage component.
    """
    # Initialize session state first (before any UI components)
    initialize_session_state()

    # Inject custom CSS for responsive styling (US-024)
    inject_custom_css()

    # Get current session state
    session_state = get_session_state()

    # Render application header with "New session" button (US-023)
    # Only show button when user is in a session (not on INPUT stage)
    if session_state.stage != SessionStage.INPUT:
        header_col, button_col = st.columns([6, 1])
        with header_col:
            st.title("PhishGuard")
        with button_col:
            # Add vertical spacing to align with title
            st.write("")
            if st.button("New session", type="secondary"):
                session_state.show_new_session_confirmation = True
                st.rerun()
    else:
        st.title("PhishGuard")

    st.caption("Autonomous Agent-Based Phishing Defense System")

    # Render new session confirmation modal (US-023)
    render_new_session_modal(session_state)

    # Render sidebar
    render_sidebar()

    # Render main content based on current stage
    render_main_content(session_state)


if __name__ == "__main__":
    main()
