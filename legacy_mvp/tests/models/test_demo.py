"""Unit tests for demo scenario models.

Tests for the DemoScenario, DemoMessage, and DemoScenarioType models
used in demo mode (US-019).
"""


import pytest

from phishguard.models import (
    AgentThinking,
    AttackType,
    ClassificationResult,
    ExtractedIOC,
    IOCType,
    PersonaProfile,
    PersonaType,
)
from phishguard.models.conversation import MessageSender
from phishguard.models.demo import DemoMessage, DemoScenario, DemoScenarioType


class TestDemoScenarioType:
    """Tests for DemoScenarioType enum."""

    def test_all_scenario_types_exist(self) -> None:
        """All expected demo scenario types should exist."""
        assert DemoScenarioType.NIGERIAN_419.value == "nigerian_419"
        assert DemoScenarioType.CEO_FRAUD.value == "ceo_fraud"
        assert DemoScenarioType.CRYPTO_INVESTMENT.value == "crypto_investment"

    def test_display_name_property(self) -> None:
        """Each scenario type should have a display name."""
        assert DemoScenarioType.NIGERIAN_419.display_name == "Nigerian 419 Scam"
        assert DemoScenarioType.CEO_FRAUD.display_name == "CEO Fraud"
        crypto_name = "Crypto Investment Scam"
        assert DemoScenarioType.CRYPTO_INVESTMENT.display_name == crypto_name

    def test_description_property(self) -> None:
        """Each scenario type should have a description."""
        for scenario_type in DemoScenarioType:
            assert len(scenario_type.description) > 0

    def test_icon_property(self) -> None:
        """Each scenario type should have an icon."""
        for scenario_type in DemoScenarioType:
            assert len(scenario_type.icon) > 0


class TestDemoMessage:
    """Tests for DemoMessage model."""

    @pytest.fixture
    def bot_message(self) -> DemoMessage:
        """Create a sample bot message."""
        return DemoMessage(
            sender=MessageSender.BOT,
            content="Hello, I'm interested in your offer!",
            thinking=AgentThinking(
                turn_goal="Build trust",
                selected_tactic="Show Interest",
                reasoning="Initial engagement to draw out the scammer.",
            ),
            iocs_in_message=(),
        )

    @pytest.fixture
    def scammer_message(self) -> DemoMessage:
        """Create a sample scammer message with IOCs."""
        return DemoMessage(
            sender=MessageSender.SCAMMER,
            content="Send money to bc1qtest123wallet",
            thinking=None,
            iocs_in_message=(
                ExtractedIOC(
                    ioc_type=IOCType.BTC_WALLET,
                    value="bc1qtest123wallet",
                    message_index=1,
                ),
            ),
        )

    def test_bot_message_is_bot(self, bot_message: DemoMessage) -> None:
        """Bot messages should be identified correctly."""
        assert bot_message.is_bot_message is True
        assert bot_message.is_scammer_message is False

    def test_scammer_message_is_scammer(self, scammer_message: DemoMessage) -> None:
        """Scammer messages should be identified correctly."""
        assert scammer_message.is_scammer_message is True
        assert scammer_message.is_bot_message is False

    def test_bot_message_has_thinking(self, bot_message: DemoMessage) -> None:
        """Bot messages can have thinking attached."""
        assert bot_message.thinking is not None
        assert bot_message.thinking.turn_goal == "Build trust"

    def test_scammer_message_has_iocs(self, scammer_message: DemoMessage) -> None:
        """Scammer messages can have IOCs attached."""
        assert len(scammer_message.iocs_in_message) == 1
        assert scammer_message.iocs_in_message[0].ioc_type == IOCType.BTC_WALLET

    def test_message_content_required(self) -> None:
        """Message content must not be empty."""
        with pytest.raises(ValueError):
            DemoMessage(
                sender=MessageSender.BOT,
                content="",
            )


class TestDemoScenario:
    """Tests for DemoScenario model."""

    @pytest.fixture
    def sample_classification(self) -> ClassificationResult:
        """Create a sample classification result."""
        return ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=95.0,
            reasoning="Classic 419 scam indicators detected.",
            classification_time_ms=1200,
        )

    @pytest.fixture
    def sample_persona(self) -> PersonaProfile:
        """Create a sample persona."""
        return PersonaProfile(
            persona_type=PersonaType.NAIVE_RETIREE,
            name="Margaret Thompson",
            age=72,
            style_description="Trusting elderly person",
            background="Retired teacher",
        )

    @pytest.fixture
    def sample_messages(self) -> tuple[DemoMessage, ...]:
        """Create sample demo messages."""
        return (
            DemoMessage(
                sender=MessageSender.BOT,
                content="Hello, how can I help?",
                thinking=AgentThinking(
                    turn_goal="Initial contact",
                    selected_tactic="Be friendly",
                    reasoning="Start the conversation.",
                ),
            ),
            DemoMessage(
                sender=MessageSender.SCAMMER,
                content="Send payment to bc1qtest",
                iocs_in_message=(
                    ExtractedIOC(
                        ioc_type=IOCType.BTC_WALLET,
                        value="bc1qtest",
                        message_index=1,
                    ),
                ),
            ),
            DemoMessage(
                sender=MessageSender.BOT,
                content="How do I send payment?",
                thinking=AgentThinking(
                    turn_goal="Get more details",
                    selected_tactic="Ask questions",
                    reasoning="Extract more IOCs.",
                ),
            ),
        )

    @pytest.fixture
    def sample_scenario(
        self,
        sample_classification: ClassificationResult,
        sample_persona: PersonaProfile,
        sample_messages: tuple[DemoMessage, ...],
    ) -> DemoScenario:
        """Create a sample demo scenario."""
        return DemoScenario(
            scenario_type=DemoScenarioType.NIGERIAN_419,
            email_content="Dear friend, I need your help...",
            classification=sample_classification,
            persona=sample_persona,
            messages=sample_messages,
        )

    def test_total_steps_property(self, sample_scenario: DemoScenario) -> None:
        """total_steps should return the number of messages."""
        assert sample_scenario.total_steps == 3

    def test_total_iocs_property(self, sample_scenario: DemoScenario) -> None:
        """total_iocs should count all IOCs across messages."""
        assert sample_scenario.total_iocs == 1

    def test_attack_type_property(self, sample_scenario: DemoScenario) -> None:
        """attack_type should return the classification attack type."""
        assert sample_scenario.attack_type == AttackType.NIGERIAN_419

    def test_get_messages_up_to_step(self, sample_scenario: DemoScenario) -> None:
        """Should return messages up to the specified step."""
        # Step 0: first message only
        msgs = sample_scenario.get_messages_up_to_step(0)
        assert len(msgs) == 1
        assert msgs[0].content == "Hello, how can I help?"

        # Step 1: first two messages
        msgs = sample_scenario.get_messages_up_to_step(1)
        assert len(msgs) == 2

        # Step 2: all messages
        msgs = sample_scenario.get_messages_up_to_step(2)
        assert len(msgs) == 3

    def test_get_iocs_up_to_step(self, sample_scenario: DemoScenario) -> None:
        """Should return IOCs extracted up to the specified step."""
        # Step 0: no IOCs yet
        iocs = sample_scenario.get_iocs_up_to_step(0)
        assert len(iocs) == 0

        # Step 1: one IOC from scammer message
        iocs = sample_scenario.get_iocs_up_to_step(1)
        assert len(iocs) == 1
        assert iocs[0].value == "bc1qtest"

        # Step 2: still one IOC (bot message has no IOCs)
        iocs = sample_scenario.get_iocs_up_to_step(2)
        assert len(iocs) == 1

    def test_get_current_thinking(self, sample_scenario: DemoScenario) -> None:
        """Should return thinking for bot messages only."""
        # Step 0: bot message with thinking
        thinking = sample_scenario.get_current_thinking(0)
        assert thinking is not None
        assert thinking.turn_goal == "Initial contact"

        # Step 1: scammer message, no thinking
        thinking = sample_scenario.get_current_thinking(1)
        assert thinking is None

        # Step 2: bot message with thinking
        thinking = sample_scenario.get_current_thinking(2)
        assert thinking is not None
        assert thinking.turn_goal == "Get more details"

    def test_can_advance(self, sample_scenario: DemoScenario) -> None:
        """Should correctly indicate if more steps are available."""
        assert sample_scenario.can_advance(0) is True  # Can go to step 1
        assert sample_scenario.can_advance(1) is True  # Can go to step 2
        assert sample_scenario.can_advance(2) is False  # At the end

    def test_get_current_thinking_out_of_bounds(
        self, sample_scenario: DemoScenario
    ) -> None:
        """Should return None for out of bounds step indices."""
        assert sample_scenario.get_current_thinking(-1) is None
        assert sample_scenario.get_current_thinking(100) is None


class TestDemoScenariosRegistry:
    """Tests for the demo scenarios registry."""

    def test_all_scenarios_available(self) -> None:
        """All demo scenarios should be available in the registry."""
        from phishguard.demo import DEMO_SCENARIOS

        assert DemoScenarioType.NIGERIAN_419 in DEMO_SCENARIOS
        assert DemoScenarioType.CEO_FRAUD in DEMO_SCENARIOS
        assert DemoScenarioType.CRYPTO_INVESTMENT in DEMO_SCENARIOS

    def test_get_scenario(self) -> None:
        """get_scenario should return the correct scenario."""
        from phishguard.demo import get_scenario

        scenario = get_scenario(DemoScenarioType.NIGERIAN_419)
        assert scenario.scenario_type == DemoScenarioType.NIGERIAN_419

    def test_get_scenario_by_type(self) -> None:
        """get_scenario_by_type should work with string values."""
        from phishguard.demo import get_scenario_by_type

        scenario = get_scenario_by_type("ceo_fraud")
        assert scenario is not None
        assert scenario.scenario_type == DemoScenarioType.CEO_FRAUD

    def test_get_scenario_by_type_invalid(self) -> None:
        """get_scenario_by_type should return None for invalid types."""
        from phishguard.demo import get_scenario_by_type

        scenario = get_scenario_by_type("invalid_type")
        assert scenario is None

    def test_scenarios_have_valid_structure(self) -> None:
        """All scenarios should have required data."""
        from phishguard.demo import DEMO_SCENARIOS

        for scenario_type, scenario in DEMO_SCENARIOS.items():
            assert scenario.scenario_type == scenario_type
            assert len(scenario.email_content) > 0
            assert scenario.classification is not None
            assert scenario.persona is not None
            assert scenario.total_steps >= 4  # At least 4 exchanges

    def test_scenarios_have_iocs(self) -> None:
        """All scenarios should have some IOCs to demonstrate."""
        from phishguard.demo import DEMO_SCENARIOS

        for scenario in DEMO_SCENARIOS.values():
            assert scenario.total_iocs > 0
