import json
from unittest.mock import AsyncMock, MagicMock, patch

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
                "reasoning": "Standard opening",
            },
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
                "reasoning": "Standard opening",
            },
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
                "reasoning": "Reason",
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
                "reasoning": "Reason",
            },
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


class TestConversationAgentUsageRecording:
    """Token usage is recorded per LLM attempt when a session is known."""

    @staticmethod
    def _agent():
        from phishguard.llm.client import LLMResponse

        llm = MagicMock()
        llm.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps({"response": "Hi there"}),
                model_used="gpt-4o",
                prompt_tokens=120,
                completion_tokens=40,
            )
        )
        validator = MagicMock()
        validator.validate.return_value = MagicMock(is_safe=True)
        return ConversationAgent(llm_client=llm, validator=validator)

    @staticmethod
    def _persona():
        from phishguard.models.persona import PersonaProfile

        return MagicMock(spec=PersonaProfile)

    async def _run(self, agent, **kwargs):
        from phishguard.models.classification import AttackType

        with patch(
            "phishguard.agents.conversation.get_conversation_system_prompt",
            return_value="sys",
        ):
            return await agent.generate_response(
                persona=self._persona(),
                email_content="hello",
                attack_type=AttackType.NIGERIAN_419,
                **kwargs,
            )

    @pytest.mark.asyncio
    async def test_generate_response_records_usage(self):
        agent = self._agent()
        with patch(
            "phishguard.agents.conversation.record_llm_usage",
            new_callable=AsyncMock,
        ) as rec:
            await self._run(agent, session_id="s-1")

        rec.assert_awaited_once()
        args = rec.await_args
        assert args.args[0] == "s-1"
        assert args.args[1] == "conversation"
        assert args.args[2] == "gpt-4o"
        assert args.args[3] == 120
        assert args.args[4] == 40
        assert isinstance(args.args[5], int)

    @pytest.mark.asyncio
    async def test_generate_response_without_session_skips_usage(self):
        agent = self._agent()
        with patch(
            "phishguard.agents.conversation.record_llm_usage",
            new_callable=AsyncMock,
        ) as rec:
            await self._run(agent)

        rec.assert_not_awaited()


class TestConversationAgentReplyLanguage:
    """The reply is written in the language of the scammer's latest message."""

    PL_EMAIL = (
        "Dzień dobry, wygrał Pan nagrodę w loterii. Aby ją odebrać, prosimy "
        "o przelew opłaty manipulacyjnej na wskazane konto bankowe."
    )
    EN_EMAIL = (
        "Hello, you have won a prize in our lottery. To claim it, please send "
        "the processing fee to the bank account below."
    )

    @staticmethod
    def _agent():
        from phishguard.llm.client import LLMResponse

        llm = MagicMock()
        llm.chat_completion = AsyncMock(
            return_value=LLMResponse(
                content=json.dumps({"response": "ok"}),
                model_used="gpt-4o",
                prompt_tokens=1,
                completion_tokens=1,
            )
        )
        validator = MagicMock()
        validator.validate.return_value = MagicMock(is_safe=True)
        return ConversationAgent(llm_client=llm, validator=validator), llm

    async def _user_prompt(self, email_content, history=None):
        from phishguard.models.classification import AttackType
        from phishguard.models.persona import PersonaProfile

        agent, llm = self._agent()
        with patch(
            "phishguard.agents.conversation.get_conversation_system_prompt",
            return_value="sys",
        ):
            await agent.generate_response(
                persona=MagicMock(spec=PersonaProfile),
                email_content=email_content,
                attack_type=AttackType.LOTTERY_PRIZE,
                conversation_history=history,
                is_first_response=history is None,
            )
        messages = llm.chat_completion.await_args.kwargs["messages"]
        return messages[-1]["content"]

    @pytest.mark.asyncio
    async def test_polish_email_asks_for_polish_reply(self):
        prompt = await self._user_prompt(self.PL_EMAIL)

        assert 'Write the "response" field in Polish' in prompt

    @pytest.mark.asyncio
    async def test_english_email_asks_for_english_reply(self):
        prompt = await self._user_prompt(self.EN_EMAIL)

        assert 'Write the "response" field in English' in prompt

    @pytest.mark.asyncio
    async def test_follow_up_uses_latest_scammer_message_language(self):
        from phishguard.models.conversation import ConversationMessage, MessageSender

        history = [
            ConversationMessage(
                sender=MessageSender.BOT, content="Oh my, really?", turn_number=1
            ),
            ConversationMessage(
                sender=MessageSender.SCAMMER, content=self.PL_EMAIL, turn_number=2
            ),
        ]

        prompt = await self._user_prompt(self.EN_EMAIL, history)

        assert 'Write the "response" field in Polish' in prompt

    @pytest.mark.asyncio
    async def test_unknown_language_asks_to_match_the_scammer(self):
        prompt = await self._user_prompt(
            "Guten Tag, Sie haben in unserer Lotterie einen Preis gewonnen. "
            "Bitte senden Sie die Bearbeitungsgebühr."
        )

        assert "same language as the scammer's latest message" in prompt
