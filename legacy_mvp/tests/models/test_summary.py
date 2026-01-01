"""Comprehensive tests for SessionSummary Pydantic model.

These tests verify that the SessionSummary model correctly:
1. Stores session metrics (exchange count, duration, attack type)
2. Computes derived properties (duration, safety score)
3. Handles IOC collection and high-value counting
4. Serializes/deserializes properly

Test Categories:
- Default initialization
- Computed properties
- IOC handling
- Edge cases
- Serialization
"""

from datetime import UTC, datetime, timedelta

import pytest

from phishguard.models import AttackType, ExtractedIOC, IOCType
from phishguard.models.summary import SessionSummary


class TestSessionSummaryInitialization:
    """Tests for SessionSummary initialization and field validation."""

    def test_creates_with_required_fields(self) -> None:
        """SessionSummary should be creatable with all required fields."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.5,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.exchange_count == 5
        assert summary.session_start == start
        assert summary.session_end == end
        assert summary.attack_type == AttackType.NIGERIAN_419
        assert summary.attack_confidence == 85.5

    def test_iocs_default_to_empty_tuple(self) -> None:
        """IOCs should default to empty tuple if not provided."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.CEO_FRAUD,
            attack_confidence=90.0,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.iocs == ()
        assert summary.ioc_count == 0

    def test_exchange_count_must_be_non_negative(self) -> None:
        """exchange_count should not accept negative values."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        with pytest.raises(ValueError):
            SessionSummary(
                exchange_count=-1,
                session_start=start,
                session_end=end,
                attack_type=AttackType.NIGERIAN_419,
                attack_confidence=85.0,
                total_responses=0,
                safe_responses=0,
            )

    def test_confidence_must_be_in_range(self) -> None:
        """attack_confidence should be between 0 and 100."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        # Test above 100
        with pytest.raises(ValueError):
            SessionSummary(
                exchange_count=5,
                session_start=start,
                session_end=end,
                attack_type=AttackType.NIGERIAN_419,
                attack_confidence=150.0,
                total_responses=5,
                safe_responses=5,
            )

        # Test below 0
        with pytest.raises(ValueError):
            SessionSummary(
                exchange_count=5,
                session_start=start,
                session_end=end,
                attack_type=AttackType.NIGERIAN_419,
                attack_confidence=-10.0,
                total_responses=5,
                safe_responses=5,
            )

    def test_model_is_frozen(self) -> None:
        """SessionSummary should be immutable (frozen)."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        with pytest.raises(Exception):  # ValidationError for frozen model
            summary.exchange_count = 10


class TestSessionSummaryDuration:
    """Tests for duration computation properties."""

    def test_duration_seconds_computed_correctly(self) -> None:
        """duration_seconds should compute correct difference."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)  # 30 minutes = 1800 seconds

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.duration_seconds == 1800.0

    def test_duration_seconds_handles_sub_minute(self) -> None:
        """duration_seconds should handle sub-minute durations."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 0, 45, tzinfo=UTC)  # 45 seconds

        summary = SessionSummary(
            exchange_count=1,
            session_start=start,
            session_end=end,
            attack_type=AttackType.CEO_FRAUD,
            attack_confidence=90.0,
            total_responses=1,
            safe_responses=1,
        )

        assert summary.duration_seconds == 45.0

    def test_formatted_duration_shows_minutes_and_seconds(self) -> None:
        """formatted_duration should show 'Xm Ys' for durations >= 1 minute."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 5, 30, tzinfo=UTC)  # 5m 30s

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.formatted_duration == "5m 30s"

    def test_formatted_duration_shows_only_seconds_for_short(self) -> None:
        """formatted_duration should show 'Xs' for durations < 1 minute."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 0, 45, tzinfo=UTC)  # 45 seconds

        summary = SessionSummary(
            exchange_count=1,
            session_start=start,
            session_end=end,
            attack_type=AttackType.CEO_FRAUD,
            attack_confidence=90.0,
            total_responses=1,
            safe_responses=1,
        )

        assert summary.formatted_duration == "45s"

    def test_formatted_duration_with_zero_seconds(self) -> None:
        """formatted_duration should handle exact minute boundaries."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC)  # Exactly 5 minutes

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.formatted_duration == "5m 0s"


class TestSessionSummarySafetyScore:
    """Tests for safety score computation."""

    def test_safety_score_100_when_all_safe(self) -> None:
        """safety_score should be 100% when all responses were safe."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        summary = SessionSummary(
            exchange_count=10,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=10,
            safe_responses=10,
        )

        assert summary.safety_score == 100.0
        assert summary.formatted_safety_score == "100.0%"

    def test_safety_score_50_when_half_safe(self) -> None:
        """safety_score should be 50% when half of responses were safe."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        summary = SessionSummary(
            exchange_count=10,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=10,
            safe_responses=5,
        )

        assert summary.safety_score == 50.0
        assert summary.formatted_safety_score == "50.0%"

    def test_safety_score_100_when_no_responses(self) -> None:
        """safety_score should be 100% when no responses (no opportunity for unsafe)."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=5)

        summary = SessionSummary(
            exchange_count=0,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=0,
            safe_responses=0,
        )

        assert summary.safety_score == 100.0

    def test_safety_score_0_when_none_safe(self) -> None:
        """safety_score should be 0% when no responses were safe."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=0,
        )

        assert summary.safety_score == 0.0
        assert summary.formatted_safety_score == "0.0%"


class TestSessionSummaryIOCs:
    """Tests for IOC handling and counting."""

    def test_ioc_count_returns_total(self) -> None:
        """ioc_count should return total number of IOCs."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        iocs = (
            ExtractedIOC(ioc_type=IOCType.BTC_WALLET, value="bc1test", message_index=0),
            ExtractedIOC(ioc_type=IOCType.PHONE, value="+1234567890", message_index=1),
            ExtractedIOC(ioc_type=IOCType.URL, value="http://evil.com", message_index=2),
        )

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            iocs=iocs,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.ioc_count == 3

    def test_high_value_ioc_count_only_btc_and_iban(self) -> None:
        """high_value_ioc_count should only count BTC wallets and IBANs."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        iocs = (
            ExtractedIOC(ioc_type=IOCType.BTC_WALLET, value="bc1test", message_index=0),
            ExtractedIOC(ioc_type=IOCType.IBAN, value="DE1234567", message_index=1),
            ExtractedIOC(ioc_type=IOCType.PHONE, value="+1234567890", message_index=2),
            ExtractedIOC(ioc_type=IOCType.URL, value="http://evil.com", message_index=3),
        )

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            iocs=iocs,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.high_value_ioc_count == 2  # BTC + IBAN
        assert summary.ioc_count == 4  # All IOCs

    def test_high_value_ioc_count_zero_when_no_financial(self) -> None:
        """high_value_ioc_count should be 0 when no financial IOCs."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        iocs = (
            ExtractedIOC(ioc_type=IOCType.PHONE, value="+1234567890", message_index=0),
            ExtractedIOC(ioc_type=IOCType.URL, value="http://evil.com", message_index=1),
        )

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.CEO_FRAUD,
            attack_confidence=90.0,
            iocs=iocs,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.high_value_ioc_count == 0
        assert summary.ioc_count == 2


class TestSessionSummarySerialization:
    """Tests for model serialization."""

    def test_model_dump_includes_all_fields(self) -> None:
        """model_dump() should include all fields including computed."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        data = summary.model_dump()

        assert "exchange_count" in data
        assert "session_start" in data
        assert "session_end" in data
        assert "attack_type" in data
        assert "attack_confidence" in data
        assert "duration_seconds" in data
        assert "formatted_duration" in data
        assert "safety_score" in data
        assert "formatted_safety_score" in data
        assert "high_value_ioc_count" in data

    def test_model_dump_json_valid(self) -> None:
        """model_dump_json() should produce valid JSON."""
        start = datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC)
        end = datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=AttackType.NIGERIAN_419,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        json_str = summary.model_dump_json()

        assert isinstance(json_str, str)
        assert "exchange_count" in json_str
        assert "nigerian_419" in json_str


class TestSessionSummaryAllAttackTypes:
    """Tests for all attack types in summary."""

    @pytest.mark.parametrize(
        "attack_type",
        [
            AttackType.NIGERIAN_419,
            AttackType.CEO_FRAUD,
            AttackType.FAKE_INVOICE,
            AttackType.ROMANCE_SCAM,
            AttackType.TECH_SUPPORT,
            AttackType.LOTTERY_PRIZE,
            AttackType.CRYPTO_INVESTMENT,
            AttackType.DELIVERY_SCAM,
            AttackType.NOT_PHISHING,
        ],
        ids=[
            "nigerian_419",
            "ceo_fraud",
            "fake_invoice",
            "romance_scam",
            "tech_support",
            "lottery_prize",
            "crypto_investment",
            "delivery_scam",
            "not_phishing",
        ],
    )
    def test_summary_accepts_all_attack_types(self, attack_type: AttackType) -> None:
        """SessionSummary should accept all AttackType values."""
        start = datetime.now(UTC)
        end = start + timedelta(minutes=30)

        summary = SessionSummary(
            exchange_count=5,
            session_start=start,
            session_end=end,
            attack_type=attack_type,
            attack_confidence=85.0,
            total_responses=5,
            safe_responses=5,
        )

        assert summary.attack_type == attack_type
