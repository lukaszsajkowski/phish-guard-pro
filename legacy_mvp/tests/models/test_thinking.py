"""Unit tests for AgentThinking model.

These tests verify that the AgentThinking Pydantic model works correctly:
1. Creation with valid data
2. Immutability (frozen model)
3. Field validation
4. Serialization/deserialization
"""

import pytest

from phishguard.models import AgentThinking


class TestAgentThinking:
    """Tests for AgentThinking model."""

    def test_create_valid_thinking(self) -> None:
        """Should create a valid AgentThinking instance."""
        thinking = AgentThinking(
            turn_goal="Extract payment method information",
            selected_tactic="Ask Questions",
            reasoning="The scammer mentioned a wire transfer, so I'll ask for details.",
        )

        assert thinking.turn_goal == "Extract payment method information"
        assert thinking.selected_tactic == "Ask Questions"
        assert thinking.reasoning == (
            "The scammer mentioned a wire transfer, so I'll ask for details."
        )

    def test_create_with_all_tactics(self) -> None:
        """Should accept all valid tactic values."""
        tactics = [
            "Show Interest",
            "Ask Questions",
            "Build Trust",
            "Extend Conversation",
            "Extract Intel",
        ]

        for tactic in tactics:
            thinking = AgentThinking(
                turn_goal="Test goal",
                selected_tactic=tactic,
                reasoning="Test reasoning",
            )
            assert thinking.selected_tactic == tactic

    def test_thinking_is_frozen(self) -> None:
        """AgentThinking should be immutable."""
        thinking = AgentThinking(
            turn_goal="Test goal",
            selected_tactic="Ask Questions",
            reasoning="Test reasoning",
        )

        with pytest.raises((TypeError, ValueError)):
            thinking.turn_goal = "Modified goal"

    def test_turn_goal_min_length(self) -> None:
        """turn_goal must have at least 1 character."""
        with pytest.raises(ValueError):
            AgentThinking(
                turn_goal="",
                selected_tactic="Ask Questions",
                reasoning="Test reasoning",
            )

    def test_selected_tactic_min_length(self) -> None:
        """selected_tactic must have at least 1 character."""
        with pytest.raises(ValueError):
            AgentThinking(
                turn_goal="Test goal",
                selected_tactic="",
                reasoning="Test reasoning",
            )

    def test_reasoning_min_length(self) -> None:
        """reasoning must have at least 1 character."""
        with pytest.raises(ValueError):
            AgentThinking(
                turn_goal="Test goal",
                selected_tactic="Ask Questions",
                reasoning="",
            )

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        thinking = AgentThinking(
            turn_goal="Build rapport",
            selected_tactic="Build Trust",
            reasoning="Establishing connection before asking for intel.",
        )

        data = thinking.model_dump()

        assert data["turn_goal"] == "Build rapport"
        assert data["selected_tactic"] == "Build Trust"
        assert data["reasoning"] == "Establishing connection before asking for intel."

    def test_deserialization(self) -> None:
        """Should deserialize from dict correctly."""
        data = {
            "turn_goal": "Gather contact details",
            "selected_tactic": "Extract Intel",
            "reasoning": "Scammer offered alternative contact method.",
        }

        thinking = AgentThinking.model_validate(data)

        assert thinking.turn_goal == "Gather contact details"
        assert thinking.selected_tactic == "Extract Intel"
        assert thinking.reasoning == "Scammer offered alternative contact method."

    def test_json_serialization(self) -> None:
        """Should serialize to JSON and back."""
        thinking = AgentThinking(
            turn_goal="Test goal",
            selected_tactic="Show Interest",
            reasoning="Testing JSON round-trip.",
        )

        json_str = thinking.model_dump_json()
        restored = AgentThinking.model_validate_json(json_str)

        assert restored.turn_goal == thinking.turn_goal
        assert restored.selected_tactic == thinking.selected_tactic
        assert restored.reasoning == thinking.reasoning
