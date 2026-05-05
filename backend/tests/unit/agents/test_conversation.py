import json
from unittest.mock import MagicMock
import pytest
from phishguard.agents.conversation import ConversationAgent
from phishguard.models.thinking import AgentThinking

class TestConversationAgentParsing:
    """Unit tests for ConversationAgent response parsing logic."""

    @pytest.fixture
    def agent(self):
        """Create a ConversationAgent with mocked dependencies."""
        return ConversationAgent(llm_client=MagicMock(), validator=MagicMock())

    def test_parse_structured_response_success(self, agent):
        """Test parsing a valid JSON response with thinking data."""
        data = {
            "response": "Hello there!",
            "thinking": {
                "turn_goal": "Friendly greeting",
                "selected_tactic": "Warmth",
                "reasoning": "Standard opening"
            }
        }
        raw = json.dumps(data)
        content, thinking = agent._parse_structured_response(raw)

        assert content == "Hello there!"
        assert isinstance(thinking, AgentThinking)
        assert thinking.turn_goal == "Friendly greeting"
        assert thinking.selected_tactic == "Warmth"
        assert thinking.reasoning == "Standard opening"

    def test_parse_structured_response_invalid_thinking(self, agent):
        """Test parsing when thinking data fails AgentThinking validation.

        AgentThinking fields have min_length=1, so empty strings should trigger
        a ValidationError (which is a subclass of ValueError).
        """
        data = {
            "response": "Hello there!",
            "thinking": {
                "turn_goal": "",  # Invalid: min_length=1
                "selected_tactic": "Warmth",
                "reasoning": "Standard opening"
            }
        }
        raw = json.dumps(data)
        content, thinking = agent._parse_structured_response(raw)

        # Should fall back to thinking=None but keep the content
        assert content == "Hello there!"
        assert thinking is None

    def test_parse_structured_response_no_json(self, agent):
        """Test parsing when response is not JSON at all."""
        raw = "This is not JSON at all."
        content, thinking = agent._parse_structured_response(raw)

        assert content == "This is not JSON at all."
        assert thinking is None

    def test_parse_structured_response_missing_response_field(self, agent):
        """Test parsing when 'response' field is missing in JSON."""
        data = {
            "thinking": {
                "turn_goal": "Goal",
                "selected_tactic": "Tactic",
                "reasoning": "Reason"
            }
        }
        raw = json.dumps(data)
        content, thinking = agent._parse_structured_response(raw)

        # Should return cleaned raw content and None for thinking
        assert content == raw.strip()
        assert thinking is None

    def test_parse_structured_response_markdown_json(self, agent):
        """Test parsing when JSON is wrapped in markdown code blocks (```json)."""
        data = {
            "response": "Hello!",
            "thinking": {
                "turn_goal": "Goal",
                "selected_tactic": "Tactic",
                "reasoning": "Reason"
            }
        }
        raw = f"Here is my response:\n```json\n{json.dumps(data)}\n```"
        content, thinking = agent._parse_structured_response(raw)

        assert content == "Hello!"
        assert thinking is not None
        assert thinking.turn_goal == "Goal"

    def test_parse_structured_response_markdown_plain(self, agent):
        """Test parsing when JSON is wrapped in plain markdown code blocks (```)."""
        data = {"response": "Hello plain markdown!"}
        raw = f"```\n{json.dumps(data)}\n```"
        content, thinking = agent._parse_structured_response(raw)

        assert content == "Hello plain markdown!"

    def test_parse_structured_response_malformed_json(self, agent):
        """Test parsing when JSON is syntactically invalid."""
        raw = '{"response": "Hello", "thinking": {'  # Unclosed brace
        content, thinking = agent._parse_structured_response(raw)

        assert content == raw.strip()
        assert thinking is None

    def test_parse_structured_response_not_a_dict(self, agent):
        """Test parsing when JSON is valid but not a dictionary."""
        raw = '["not", "a", "dict"]'
        content, thinking = agent._parse_structured_response(raw)

        assert content == raw.strip()
        assert thinking is None
