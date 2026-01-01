"""Agent thinking models for displaying reasoning in the UI.

This module contains Pydantic models for representing agent thinking/reasoning
that can be displayed in the "Agent Thinking" panel of the PhishGuard UI.
"""

from pydantic import BaseModel, ConfigDict, Field


class AgentThinking(BaseModel):
    """Represents the agent's strategic thinking for a response.

    This model captures the agent's reasoning process, including what goal
    it's trying to achieve, what tactic it selected, and the detailed
    reasoning behind its response.

    Attributes:
        turn_goal: The specific objective for this conversation turn.
        selected_tactic: The engagement tactic chosen (e.g., "Build Trust").
        reasoning: Detailed explanation of the agent's thinking process.

    Example:
        >>> thinking = AgentThinking(
        ...     turn_goal="Extract payment method information",
        ...     selected_tactic="Ask Questions",
        ...     reasoning="Scammer mentioned wire transfer, asking for details."
        ... )
        >>> thinking.turn_goal
        'Extract payment method information'
    """

    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
    )

    turn_goal: str = Field(
        ...,
        description="The specific objective for this conversation turn.",
        min_length=1,
    )
    selected_tactic: str = Field(
        ...,
        description="The engagement tactic chosen for this response.",
        min_length=1,
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation of the agent's thinking process.",
        min_length=1,
    )
