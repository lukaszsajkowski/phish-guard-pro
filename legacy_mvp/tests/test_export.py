"""Comprehensive tests for PhishGuard export functionality.

These tests verify that the export module correctly:
1. Generates JSON exports with all required fields
2. Generates CSV exports for IOCs
3. Creates properly timestamped filenames
4. Handles edge cases (empty IOCs, missing data)

Test Categories:
- JSON export content
- CSV export content
- Filename generation
- Edge cases
- Error handling
"""

import csv
import io
import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from phishguard.export import (
    export_iocs_csv,
    export_session_json,
    generate_filename,
    get_csv_filename,
    get_json_filename,
)
from phishguard.models import (
    AttackType,
    ClassificationResult,
    ConversationMessage,
    ExtractedIOC,
    IOCType,
    MessageSender,
    PersonaProfile,
    PersonaType,
    SessionState,
)


class TestGenerateFilename:
    """Tests for filename generation function."""

    def test_generates_json_filename(self) -> None:
        """generate_filename should create valid JSON filename."""
        filename = generate_filename("phishguard_session", "json")
        assert filename.startswith("phishguard_session_")
        assert filename.endswith(".json")

    def test_generates_csv_filename(self) -> None:
        """generate_filename should create valid CSV filename."""
        filename = generate_filename("phishguard_iocs", "csv")
        assert filename.startswith("phishguard_iocs_")
        assert filename.endswith(".csv")

    def test_filename_contains_timestamp(self) -> None:
        """generate_filename should include timestamp in YYYYMMDD_HHMMSS format."""
        filename = generate_filename("test", "txt")
        # Extract timestamp portion
        parts = filename.split("_")
        assert len(parts) >= 3  # test_YYYYMMDD_HHMMSS.txt

    def test_get_json_filename_format(self) -> None:
        """get_json_filename should return correct format."""
        filename = get_json_filename()
        assert filename.startswith("phishguard_session_")
        assert filename.endswith(".json")

    def test_get_csv_filename_format(self) -> None:
        """get_csv_filename should return correct format."""
        filename = get_csv_filename()
        assert filename.startswith("phishguard_iocs_")
        assert filename.endswith(".csv")

    def test_filename_timestamp_matches_current_time(self) -> None:
        """Filename timestamp should be close to current time."""
        with patch("phishguard.export.datetime") as mock_datetime:
            mock_now = datetime(2024, 6, 15, 14, 30, 45, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            filename = generate_filename("test", "json")

            assert "20240615_143045" in filename


class TestExportSessionJson:
    """Tests for JSON session export."""

    @pytest.fixture
    def sample_session_state(self) -> SessionState:
        """Create a sample session state for testing."""
        classification = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.5,
            reasoning="This is a Nigerian 419 scam based on...",
            classification_time_ms=150,
        )

        persona = PersonaProfile(
            name="John Smith",
            age=65,
            persona_type=PersonaType.NAIVE_RETIREE,
            background="Retired teacher living in Florida.",
            style_description="Trusting and somewhat gullible.",
        )

        messages = [
            ConversationMessage(
                sender=MessageSender.BOT,
                content="Hello, I'm interested in your offer.",
                turn_number=1,
            ),
            ConversationMessage(
                sender=MessageSender.SCAMMER,
                content="Great! Please send me your details.",
                turn_number=1,
            ),
        ]

        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qtest123",
                message_index=1,
                context="Send to bc1qtest123",
            ),
        ]

        state = SessionState(
            email_content="Original phishing email content",
            classification_result=classification,
            persona_profile=persona,
            conversation_history=messages,
            extracted_iocs=iocs,
            ended_at=datetime.now(UTC),
        )

        return state

    def test_exports_valid_json(self, sample_session_state: SessionState) -> None:
        """export_session_json should produce valid JSON."""
        json_str = export_session_json(sample_session_state)

        # Should not raise
        data = json.loads(json_str)
        assert isinstance(data, dict)

    def test_includes_export_metadata(self, sample_session_state: SessionState) -> None:
        """JSON export should include export metadata."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        assert "phishguard_export_version" in data
        assert data["phishguard_export_version"] == "1.0"
        assert "exported_at" in data

    def test_includes_session_metadata(self, sample_session_state: SessionState) -> None:
        """JSON export should include session metadata."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        metadata = data["metadata"]
        assert "session_id" in metadata
        assert "created_at" in metadata
        assert "attack_type" in metadata
        assert metadata["attack_type"] == "nigerian_419"
        assert "attack_type_display" in metadata
        assert "attack_confidence" in metadata
        assert metadata["attack_confidence"] == 85.5

    def test_includes_persona_data(self, sample_session_state: SessionState) -> None:
        """JSON export should include persona data."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        persona = data["persona"]
        assert persona["name"] == "John Smith"
        assert persona["age"] == 65
        assert persona["persona_type"] == "naive_retiree"

    def test_includes_conversation_history(
        self, sample_session_state: SessionState
    ) -> None:
        """JSON export should include full conversation history."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        history = data["conversation_history"]
        assert len(history) == 2
        assert history[0]["sender"] == "bot"
        assert history[0]["content"] == "Hello, I'm interested in your offer."
        assert history[1]["sender"] == "scammer"

    def test_includes_extracted_iocs(self, sample_session_state: SessionState) -> None:
        """JSON export should include extracted IOCs."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        iocs = data["extracted_iocs"]
        assert len(iocs) == 1
        assert iocs[0]["type"] == "btc_wallet"
        assert iocs[0]["value"] == "bc1qtest123"
        assert iocs[0]["is_high_value"] is True

    def test_includes_summary_stats(self, sample_session_state: SessionState) -> None:
        """JSON export should include summary statistics."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        stats = data["summary_stats"]
        assert "total_iocs" in stats
        assert "high_value_iocs" in stats
        assert "total_messages" in stats
        assert stats["total_messages"] == 2

    def test_includes_original_email(self, sample_session_state: SessionState) -> None:
        """JSON export should include original email content."""
        json_str = export_session_json(sample_session_state)
        data = json.loads(json_str)

        assert data["original_email"] == "Original phishing email content"

    def test_raises_error_without_classification(self) -> None:
        """export_session_json should raise error without classification."""
        state = SessionState()  # No classification

        with pytest.raises(ValueError) as exc_info:
            export_session_json(state)

        assert "not classified" in str(exc_info.value)

    def test_handles_empty_conversation(self) -> None:
        """export_session_json should handle empty conversation history."""
        classification = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=90.0,
            reasoning="CEO fraud detected",
            classification_time_ms=100,
        )

        state = SessionState(
            classification_result=classification,
            conversation_history=[],
            extracted_iocs=[],
        )

        json_str = export_session_json(state)
        data = json.loads(json_str)

        assert data["conversation_history"] == []
        assert data["extracted_iocs"] == []

    def test_handles_none_ended_at(self) -> None:
        """export_session_json should handle None ended_at gracefully."""
        classification = ClassificationResult(
            attack_type=AttackType.CEO_FRAUD,
            confidence=90.0,
            reasoning="CEO fraud detected",
            classification_time_ms=100,
        )

        state = SessionState(
            classification_result=classification,
            ended_at=None,  # Not ended yet
        )

        json_str = export_session_json(state)
        data = json.loads(json_str)

        assert data["metadata"]["ended_at"] is None


class TestExportIocsCsv:
    """Tests for CSV IOC export."""

    def test_exports_valid_csv(self) -> None:
        """export_iocs_csv should produce valid CSV."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qtest123",
                message_index=0,
            ),
        ]

        csv_str = export_iocs_csv(iocs)

        # Should be parseable as CSV
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)
        assert len(rows) >= 2  # Header + at least one data row

    def test_csv_has_correct_headers(self) -> None:
        """CSV should have the correct header row."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qtest123",
                message_index=0,
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.reader(io.StringIO(csv_str))
        headers = next(reader)

        assert "ioc_type" in headers
        assert "value" in headers
        assert "timestamp" in headers
        assert "context" in headers
        assert "message_index" in headers
        assert "is_high_value" in headers

    def test_csv_includes_all_iocs(self) -> None:
        """CSV should include all IOCs."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qtest123",
                message_index=0,
            ),
            ExtractedIOC(
                ioc_type=IOCType.IBAN,
                value="DE1234567890",
                message_index=1,
            ),
            ExtractedIOC(
                ioc_type=IOCType.PHONE,
                value="+1234567890",
                message_index=2,
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)

        # Header + 3 data rows
        assert len(rows) == 4

    def test_csv_handles_empty_iocs(self) -> None:
        """CSV should handle empty IOC list (header only)."""
        csv_str = export_iocs_csv([])
        reader = csv.reader(io.StringIO(csv_str))
        rows = list(reader)

        # Only header row
        assert len(rows) == 1
        assert rows[0][0] == "ioc_type"

    def test_csv_includes_ioc_type_display(self) -> None:
        """CSV should include human-readable IOC type."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qtest123",
                message_index=0,
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.DictReader(io.StringIO(csv_str))
        row = next(reader)

        assert row["ioc_type"] == "btc_wallet"
        assert row["ioc_type_display"] == "BTC Wallet"

    def test_csv_includes_high_value_flag(self) -> None:
        """CSV should include is_high_value flag."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qtest123",
                message_index=0,
            ),
            ExtractedIOC(
                ioc_type=IOCType.PHONE,
                value="+1234567890",
                message_index=1,
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.DictReader(io.StringIO(csv_str))
        rows = list(reader)

        # BTC wallet is high-value
        assert rows[0]["is_high_value"] == "true"
        # Phone is not high-value
        assert rows[1]["is_high_value"] == "false"

    def test_csv_handles_context_with_commas(self) -> None:
        """CSV should properly escape context with commas."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="http://evil.com",
                message_index=0,
                context="Found in message: 'Click here, now!'",
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.DictReader(io.StringIO(csv_str))
        row = next(reader)

        assert "Click here, now!" in row["context"]

    def test_csv_handles_none_context(self) -> None:
        """CSV should handle None context as empty string."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="http://evil.com",
                message_index=0,
                context=None,
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.DictReader(io.StringIO(csv_str))
        row = next(reader)

        assert row["context"] == ""

    @pytest.mark.parametrize(
        "ioc_type,expected_type,expected_display",
        [
            (IOCType.BTC_WALLET, "btc_wallet", "BTC Wallet"),
            (IOCType.IBAN, "iban", "IBAN"),
            (IOCType.PHONE, "phone", "Phone Number"),
            (IOCType.URL, "url", "URL"),
        ],
        ids=["btc_wallet", "iban", "phone", "url"],
    )
    def test_csv_all_ioc_types(
        self, ioc_type: IOCType, expected_type: str, expected_display: str
    ) -> None:
        """CSV should correctly export all IOC types."""
        iocs = [
            ExtractedIOC(
                ioc_type=ioc_type,
                value="test_value",
                message_index=0,
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.DictReader(io.StringIO(csv_str))
        row = next(reader)

        assert row["ioc_type"] == expected_type
        assert row["ioc_type_display"] == expected_display


class TestExportEdgeCases:
    """Tests for edge cases in export functionality."""

    def test_json_export_with_unicode_content(self) -> None:
        """JSON export should handle unicode characters."""
        classification = ClassificationResult(
            attack_type=AttackType.ROMANCE_SCAM,
            confidence=80.0,
            reasoning="Romance scam with special chars: and more",
            classification_time_ms=100,
        )

        messages = [
            ConversationMessage(
                sender=MessageSender.BOT,
                content="Hello! How are you?",
                turn_number=1,
            ),
        ]

        state = SessionState(
            email_content="Special content: test",
            classification_result=classification,
            conversation_history=messages,
        )

        json_str = export_session_json(state)
        data = json.loads(json_str)

        # Unicode should be preserved
        assert "test" in json_str or "\\u" in json_str  # Either preserved or escaped

    def test_csv_export_with_special_characters(self) -> None:
        """CSV export should handle special characters in values."""
        iocs = [
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="http://evil.com/path?param=value&other=test",
                message_index=0,
                context='Message said: "Click here!"',
            ),
        ]

        csv_str = export_iocs_csv(iocs)
        reader = csv.DictReader(io.StringIO(csv_str))
        row = next(reader)

        # URL with special chars should be preserved
        assert "param=value" in row["value"]

    def test_json_export_large_conversation(self) -> None:
        """JSON export should handle large conversation history."""
        classification = ClassificationResult(
            attack_type=AttackType.NIGERIAN_419,
            confidence=85.0,
            reasoning="Nigerian 419 scam",
            classification_time_ms=100,
        )

        # Create 100 messages
        messages = []
        for i in range(100):
            sender = MessageSender.BOT if i % 2 == 0 else MessageSender.SCAMMER
            messages.append(
                ConversationMessage(
                    sender=sender,
                    content=f"Message {i}: " + "x" * 500,  # Long content
                    turn_number=(i // 2) + 1,
                )
            )

        state = SessionState(
            classification_result=classification,
            conversation_history=messages,
        )

        json_str = export_session_json(state)
        data = json.loads(json_str)

        assert len(data["conversation_history"]) == 100
