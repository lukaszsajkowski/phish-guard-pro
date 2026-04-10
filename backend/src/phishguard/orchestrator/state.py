"""State definitions for PhishGuard LangGraph workflow.

This module defines the TypedDict state schema used throughout the
LangGraph workflow, enabling type-safe state management across nodes.
"""

from operator import add
from typing import Annotated, TypedDict


class PersonaState(TypedDict, total=False):
    """Persona information in the workflow state."""

    persona_type: str
    name: str
    age: int
    style_description: str
    background: str


class ClassificationState(TypedDict, total=False):
    """Classification result in the workflow state."""

    attack_type: str
    confidence: float
    reasoning: str
    classification_time_ms: int


class IOCState(TypedDict, total=False):
    """Extracted IOC in the workflow state."""

    type: str
    value: str
    context: str | None
    is_high_value: bool


class MessageState(TypedDict, total=False):
    """Conversation message in the workflow state."""

    sender: str  # "bot" | "scammer"
    content: str


class ThinkingState(TypedDict, total=False):
    """Agent thinking metadata."""

    turn_goal: str
    selected_tactic: str
    reasoning: str


class PhishGuardState(TypedDict, total=False):
    """Main state schema for PhishGuard workflow.

    This TypedDict defines all state fields that flow through the LangGraph
    workflow. Fields use `total=False` to allow partial updates.

    Attributes:
        session_id: Unique session identifier for persistence.
        user_id: Authenticated user's ID.
        email_content: Original phishing email content.
        classification: Classification result from ProfilerAgent.
        persona: Selected persona from PersonaEngine.
        conversation_history: List of messages in the conversation.
        current_response: Latest generated response.
        current_thinking: Agent's thinking for current response.
        extracted_iocs: IOCs extracted from scammer messages.
        scammer_message: Latest scammer message (input for continuation).
        is_safe: Whether current response passed safety validation.
        safety_violations: List of safety violations if any.
        regeneration_count: Number of regeneration attempts.
        generation_time_ms: Time taken for response generation.
        used_fallback_model: Whether fallback LLM was used (US-023).
        error: Error message if workflow failed.
    """

    # Session info
    session_id: str
    user_id: str

    # Input
    email_content: str
    scammer_message: str | None

    # Classification
    classification: ClassificationState | None

    # Persona
    persona: PersonaState | None

    # Conversation
    conversation_history: Annotated[list[MessageState], add]
    current_response: str | None
    current_thinking: ThinkingState | None

    # Intel
    extracted_iocs: Annotated[list[IOCState], add]

    # Safety
    is_safe: bool
    safety_violations: list[str]
    regeneration_count: int

    # Metadata
    generation_time_ms: int
    used_fallback_model: bool
    error: str | None
