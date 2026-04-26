"""Unit tests for session export functions (US-019, US-020, US-039).

Tests for:
- export_session_json(): Export full session data to JSON
- export_iocs_csv(): Export IOCs to CSV format (with enrichment columns)
- generate_export_filename(): Generate timestamped filenames
- _derive_threat_score(): IOC threat score derivation helper
"""

import csv
import io
from unittest.mock import AsyncMock, patch

import pytest

from phishguard.services import session_service as _ss
from phishguard.services.session_service import (
    _derive_threat_score,
    export_iocs_csv,
    generate_export_filename,
)


class TestDeriveThreatScore:
    """Tests for _derive_threat_score helper (US-039)."""

    def test_btc_malicious_with_high_report_count(self):
        score = _derive_threat_score(
            "btc", {"reputation": "malicious", "report_count": 20}
        )
        assert score == 100

    def test_btc_malicious_with_low_report_count(self):
        score = _derive_threat_score(
            "btc", {"reputation": "malicious", "report_count": 0}
        )
        assert score == 70

    def test_btc_suspicious(self):
        score = _derive_threat_score(
            "btc", {"reputation": "suspicious", "report_count": 2}
        )
        assert 40 <= score <= 69

    def test_btc_unknown_with_tx_activity(self):
        score = _derive_threat_score("btc", {"reputation": "unknown", "tx_count": 5})
        assert score == 15

    def test_btc_unknown_no_activity(self):
        score = _derive_threat_score("btc", {"reputation": "unknown", "tx_count": 0})
        assert score == 5

    def test_ip_returns_abuse_confidence_score(self):
        score = _derive_threat_score(
            "ip", {"abuse_confidence_score": 72, "reputation": "malicious"}
        )
        assert score == 72

    def test_generic_malicious_reputation(self):
        score = _derive_threat_score("url", {"reputation": "malicious"})
        assert score == 90

    def test_generic_suspicious_reputation(self):
        score = _derive_threat_score("url", {"reputation": "suspicious"})
        assert score == 50

    def test_generic_clean_reputation(self):
        score = _derive_threat_score("phone", {"reputation": "clean"})
        assert score == 10

    def test_generic_unknown_reputation(self):
        score = _derive_threat_score("iban", {"reputation": "unknown"})
        assert score == 0


_EXPECTED_HEADER = [
    "ioc_type",
    "value",
    "timestamp",
    "confidence",
    "is_high_value",
    "threat_score",
    "reputation",
    "source",
]


class TestExportIocsCsv:
    """Tests for export_iocs_csv function (US-020, US-039)."""

    def test_export_csv_with_multiple_iocs(self):
        """CSV export should include all IOCs with correct columns."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qtest123456789",
                "confidence": 1.0,
                "created_at": "2026-01-07T18:00:00Z",
            },
            {
                "id": "ioc-2",
                "type": "iban",
                "value": "DE89370400440532013000",
                "confidence": 0.95,
                "created_at": "2026-01-07T18:01:00Z",
            },
            {
                "id": "ioc-3",
                "type": "url",
                "value": "https://phishing.example.com",
                "confidence": 0.8,
                "created_at": "2026-01-07T18:02:00Z",
            },
        ]

        csv_content = export_iocs_csv(iocs)

        # Parse CSV to verify structure
        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Verify header row
        assert rows[0] == _EXPECTED_HEADER

        # Verify data rows
        assert len(rows) == 4  # Header + 3 IOCs

        # Verify BTC row (high value)
        assert rows[1][0] == "btc"
        assert rows[1][1] == "bc1qtest123456789"
        assert rows[1][4] == "true"  # is_high_value

        # Verify IBAN row (high value)
        assert rows[2][0] == "iban"
        assert rows[2][4] == "true"  # is_high_value

        # Verify URL row (not high value)
        assert rows[3][0] == "url"
        assert rows[3][4] == "false"  # is_high_value

    def test_export_csv_empty_iocs(self):
        """CSV export with empty IOC list should return header only."""
        csv_content = export_iocs_csv([])

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        # Should have only header row
        assert len(rows) == 1
        assert rows[0] == _EXPECTED_HEADER

    def test_export_csv_phone_ioc(self):
        """CSV export should correctly mark phone IOCs as not high value."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "phone",
                "value": "+1-555-123-4567",
                "confidence": 0.9,
                "created_at": "2026-01-07T18:00:00Z",
            },
        ]

        csv_content = export_iocs_csv(iocs)

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[1][0] == "phone"
        assert rows[1][4] == "false"  # Phone is not high value

    def test_export_csv_btc_wallet_variant(self):
        """CSV export should mark btc_wallet type as high value."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "btc_wallet",
                "value": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",
                "confidence": 1.0,
                "created_at": "2026-01-07T18:00:00Z",
            },
        ]

        csv_content = export_iocs_csv(iocs)

        reader = csv.reader(io.StringIO(csv_content))
        rows = list(reader)

        assert rows[1][0] == "btc_wallet"
        assert rows[1][4] == "true"  # btc_wallet is high value

    def test_export_csv_valid_format(self):
        """CSV export should produce valid CSV that can be parsed."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "url",
                "value": "https://example.com/path?query=value&other=test",
                "confidence": 0.85,
                "created_at": "2026-01-07T18:00:00Z",
            },
        ]

        csv_content = export_iocs_csv(iocs)

        # Should be valid CSV (no exceptions when parsing)
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["ioc_type"] == "url"
        assert rows[0]["value"] == "https://example.com/path?query=value&other=test"

    # ------------------------------------------------------------------
    # US-039: enrichment columns
    # ------------------------------------------------------------------

    def test_export_csv_unenriched_iocs_have_empty_enrichment_fields(self):
        """Unenriched IOCs must export with empty threat_score/reputation/source."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qtest",
                "confidence": 1.0,
                "created_at": "2026-01-07T18:00:00Z",
            },
        ]

        csv_content = export_iocs_csv(iocs)  # no enrichment_by_id
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["threat_score"] == ""
        assert row["reputation"] == ""
        assert row["source"] == ""

    def test_export_csv_enriched_ioc_populates_columns(self):
        """Enriched IOC should have threat_score, reputation, source in CSV."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qmalicious",
                "confidence": 1.0,
                "created_at": "2026-01-07T18:00:00Z",
            },
        ]
        enrichment_by_id = {
            "ioc-1": {
                "threat_score": 85,
                "reputation": "malicious",
                "source": "btc_mempool",
            },
        }

        csv_content = export_iocs_csv(iocs, enrichment_by_id)
        reader = csv.DictReader(io.StringIO(csv_content))
        row = next(reader)

        assert row["threat_score"] == "85"
        assert row["reputation"] == "malicious"
        assert row["source"] == "btc_mempool"

    def test_export_csv_mixed_enriched_and_plain_iocs(self):
        """CSV export covers both enriched and plain IOCs without errors (US-039)."""
        iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qmalicious",
                "confidence": 1.0,
                "created_at": "2026-01-07T18:00:00Z",
            },
            {
                "id": "ioc-2",
                "type": "url",
                "value": "https://phishing.example.com",
                "confidence": 0.8,
                "created_at": "2026-01-07T18:01:00Z",
            },
        ]
        enrichment_by_id = {
            "ioc-1": {
                "threat_score": 90,
                "reputation": "malicious",
                "source": "btc_mempool",
            },
            # ioc-2 has no enrichment
        }

        csv_content = export_iocs_csv(iocs, enrichment_by_id)
        reader = csv.DictReader(io.StringIO(csv_content))
        rows = list(reader)

        assert len(rows) == 2
        # Enriched row
        assert rows[0]["threat_score"] == "90"
        assert rows[0]["reputation"] == "malicious"
        assert rows[0]["source"] == "btc_mempool"
        # Plain row
        assert rows[1]["threat_score"] == ""
        assert rows[1]["reputation"] == ""
        assert rows[1]["source"] == ""


class TestExportSessionStix:
    """Tests for STIX 2.1 IOC export."""

    @pytest.mark.asyncio
    async def test_export_stix_bundle_contains_indicator_objects(self):
        mock_session = {"id": "session-123", "user_id": "user-456"}
        mock_iocs = [
            {
                "id": "ioc-1",
                "type": "url",
                "value": "https://phishing.example.com/login",
                "confidence": 0.8,
                "created_at": "2026-01-07T17:02:00Z",
            },
            {
                "id": "ioc-2",
                "type": "btc_wallet",
                "value": "bc1qtest",
                "confidence": 1.0,
                "created_at": "2026-01-07T17:03:00Z",
            },
        ]

        with (
            patch.object(_ss, "get_session", new_callable=AsyncMock) as m_sess,
            patch.object(_ss, "get_session_iocs", new_callable=AsyncMock) as m_iocs,
        ):
            m_sess.return_value = mock_session
            m_iocs.return_value = mock_iocs

            result = await _ss.export_session_stix("session-123")

        assert result["type"] == "bundle"
        assert result["id"].startswith("bundle--")
        assert len(result["objects"]) == 2

        url_indicator = result["objects"][0]
        assert url_indicator["type"] == "indicator"
        assert url_indicator["spec_version"] == "2.1"
        assert url_indicator["indicator_types"] == ["malicious-activity"]
        assert url_indicator["x_phishguard_ioc_type"] == "url"
        assert url_indicator["pattern"] == (
            "[url:value = 'https://phishing.example.com/login']"
        )
        assert url_indicator["confidence"] == 80

        wallet_indicator = result["objects"][1]
        assert wallet_indicator["indicator_types"] == ["malicious-activity"]
        assert wallet_indicator["x_phishguard_ioc_type"] == "btc_wallet"
        assert wallet_indicator["pattern"] == "[x-phishguard-ioc:value = 'bc1qtest']"

    @pytest.mark.asyncio
    async def test_export_stix_session_not_found(self):
        with patch.object(
            _ss,
            "get_session",
            new_callable=AsyncMock,
        ) as m_sess:
            m_sess.return_value = None

            with pytest.raises(Exception, match="not found"):
                await _ss.export_session_stix("missing-session")


class TestGenerateExportFilename:
    """Tests for generate_export_filename function."""

    def test_generate_json_filename(self):
        """Should generate filename with correct format for JSON."""
        filename = generate_export_filename("phishguard_session", "json")

        assert filename.startswith("phishguard_session_")
        assert filename.endswith(".json")
        # Should have format: prefix_YYYYMMDD_HHMMSS.extension
        parts = filename.replace(".json", "").split("_")
        assert len(parts) == 4  # phishguard, session, date, time

    def test_generate_csv_filename(self):
        """Should generate filename with correct format for CSV."""
        filename = generate_export_filename("phishguard_iocs", "csv")

        assert filename.startswith("phishguard_iocs_")
        assert filename.endswith(".csv")

    def test_generate_filename_contains_valid_timestamp(self):
        """Filename should contain valid timestamp that can be parsed."""
        filename = generate_export_filename("test", "txt")

        # Extract timestamp portion: test_YYYYMMDD_HHMMSS.txt
        timestamp_part = filename.replace("test_", "").replace(".txt", "")

        # Should be in format YYYYMMDD_HHMMSS
        assert len(timestamp_part) == 15  # 8 + 1 + 6

        # Should be parseable
        date_part, time_part = timestamp_part.split("_")
        assert len(date_part) == 8  # YYYYMMDD
        assert len(time_part) == 6  # HHMMSS

    def test_generate_filename_different_calls_produce_different_names(self):
        """Consecutive calls should produce unique filenames (within resolution)."""
        import time

        filename1 = generate_export_filename("test", "json")
        time.sleep(1.1)  # Wait just over 1 second
        filename2 = generate_export_filename("test", "json")

        assert filename1 != filename2


class TestExportSessionJson:
    """Tests for export_session_json function (US-019).

    These tests use mocks since the function interacts with the database.
    """

    @pytest.mark.asyncio
    async def test_export_json_structure(self):
        """Exported JSON should have correct top-level structure."""

        # Mock the dependent functions
        mock_session = {
            "id": "session-123",
            "user_id": "user-456",
            "attack_type": "nigerian_419",
            "persona": {"name": "John Doe", "age": 65},
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": "2026-01-07T18:00:00Z",
            "turn_limit": 20,
        }

        mock_messages = [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Original email",
                "metadata": {"type": "original_email"},
                "created_at": "2026-01-07T17:00:00Z",
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "Bot response",
                "metadata": {},
                "created_at": "2026-01-07T17:01:00Z",
            },
            {
                "id": "msg-3",
                "role": "scammer",
                "content": "Scammer reply",
                "metadata": {},
                "created_at": "2026-01-07T17:02:00Z",
            },
        ]

        mock_iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qtest",
                "confidence": 1.0,
                "created_at": "2026-01-07T17:02:00Z",
            },
        ]

        mock_summary = {
            "session_id": "session-123",
            "exchange_count": 1,
        }

        with (
            patch.object(
                _ss, "get_session", new_callable=AsyncMock
            ) as mock_get_session,
            patch.object(
                _ss, "get_session_messages", new_callable=AsyncMock
            ) as mock_get_messages,
            patch.object(
                _ss, "get_session_iocs", new_callable=AsyncMock
            ) as mock_get_iocs,
            patch.object(
                _ss, "get_session_summary", new_callable=AsyncMock
            ) as mock_get_summary,
        ):
            mock_get_session.return_value = mock_session
            mock_get_messages.return_value = mock_messages
            mock_get_iocs.return_value = mock_iocs
            mock_get_summary.return_value = mock_summary

            result = await _ss.export_session_json("session-123")

            # Verify top-level keys
            assert "phishguard_export_version" in result
            assert result["phishguard_export_version"] == "1.0"
            assert "exported_at" in result
            assert "metadata" in result
            assert "persona" in result
            assert "original_email" in result
            assert "conversation_history" in result
            assert "extracted_iocs" in result
            assert "summary_stats" in result

    @pytest.mark.asyncio
    async def test_export_json_metadata(self):
        """Exported JSON metadata should contain session info."""

        mock_session = {
            "id": "session-123",
            "attack_type": "ceo_fraud",
            "persona": None,
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": "2026-01-07T18:30:00Z",
            "turn_limit": 30,
        }

        mock_summary = {"session_id": "session-123", "exchange_count": 5}

        with (
            patch.object(
                _ss, "get_session", new_callable=AsyncMock
            ) as mock_get_session,
            patch.object(
                _ss, "get_session_messages", new_callable=AsyncMock
            ) as mock_get_messages,
            patch.object(
                _ss, "get_session_iocs", new_callable=AsyncMock
            ) as mock_get_iocs,
            patch.object(
                _ss, "get_session_summary", new_callable=AsyncMock
            ) as mock_get_summary,
        ):
            mock_get_session.return_value = mock_session
            mock_get_messages.return_value = []
            mock_get_iocs.return_value = []
            mock_get_summary.return_value = mock_summary

            result = await _ss.export_session_json("session-123")

            metadata = result["metadata"]
            assert metadata["session_id"] == "session-123"
            assert metadata["attack_type"] == "ceo_fraud"
            assert metadata["turn_count"] == 5
            assert metadata["turn_limit"] == 30

    @pytest.mark.asyncio
    async def test_export_json_excludes_original_email_from_history(self):
        """Conversation history should not include the original email."""

        mock_session = {
            "id": "session-123",
            "attack_type": "nigerian_419",
            "persona": None,
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": None,
            "turn_limit": 20,
        }

        mock_messages = [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Original phishing email content",
                "metadata": {"type": "original_email"},
                "created_at": "2026-01-07T17:00:00Z",
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "Hello, received your message",
                "metadata": {},
                "created_at": "2026-01-07T17:01:00Z",
            },
        ]

        with (
            patch.object(
                _ss, "get_session", new_callable=AsyncMock
            ) as mock_get_session,
            patch.object(
                _ss, "get_session_messages", new_callable=AsyncMock
            ) as mock_get_messages,
            patch.object(
                _ss, "get_session_iocs", new_callable=AsyncMock
            ) as mock_get_iocs,
            patch.object(
                _ss, "get_session_summary", new_callable=AsyncMock
            ) as mock_get_summary,
        ):
            mock_get_session.return_value = mock_session
            mock_get_messages.return_value = mock_messages
            mock_get_iocs.return_value = []
            mock_get_summary.return_value = {
                "session_id": "session-123",
                "exchange_count": 1,
            }

            result = await _ss.export_session_json("session-123")

            # Original email should be in dedicated field, not in conversation history
            assert result["original_email"] == "Original phishing email content"

            # Conversation history should only have the bot response
            history = result["conversation_history"]
            assert len(history) == 1
            assert history[0]["content"] == "Hello, received your message"

    @pytest.mark.asyncio
    async def test_export_json_summary_stats(self):
        """Exported JSON should include accurate summary statistics."""

        mock_session = {
            "id": "session-123",
            "attack_type": "crypto_investment",
            "persona": None,
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": "2026-01-07T18:00:00Z",
            "turn_limit": 20,
        }

        mock_messages = [
            {
                "id": "msg-1",
                "role": "user",
                "content": "Email",
                "metadata": {"type": "original_email"},
                "created_at": "2026-01-07T17:00:00Z",
            },
            {
                "id": "msg-2",
                "role": "assistant",
                "content": "Response 1",
                "metadata": {},
                "created_at": "2026-01-07T17:01:00Z",
            },
            {
                "id": "msg-3",
                "role": "scammer",
                "content": "Scammer 1",
                "metadata": {},
                "created_at": "2026-01-07T17:02:00Z",
            },
            {
                "id": "msg-4",
                "role": "assistant",
                "content": "Response 2",
                "metadata": {},
                "created_at": "2026-01-07T17:03:00Z",
            },
            {
                "id": "msg-5",
                "role": "scammer",
                "content": "Scammer 2",
                "metadata": {},
                "created_at": "2026-01-07T17:04:00Z",
            },
        ]

        mock_iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1q...",
                "confidence": 1.0,
                "created_at": "2026-01-07T17:02:00Z",
            },
            {
                "id": "ioc-2",
                "type": "iban",
                "value": "DE89...",
                "confidence": 0.95,
                "created_at": "2026-01-07T17:04:00Z",
            },
            {
                "id": "ioc-3",
                "type": "url",
                "value": "https://...",
                "confidence": 0.8,
                "created_at": "2026-01-07T17:04:00Z",
            },
        ]

        with (
            patch.object(
                _ss, "get_session", new_callable=AsyncMock
            ) as mock_get_session,
            patch.object(
                _ss, "get_session_messages", new_callable=AsyncMock
            ) as mock_get_messages,
            patch.object(
                _ss, "get_session_iocs", new_callable=AsyncMock
            ) as mock_get_iocs,
            patch.object(
                _ss, "get_session_summary", new_callable=AsyncMock
            ) as mock_get_summary,
        ):
            mock_get_session.return_value = mock_session
            mock_get_messages.return_value = mock_messages
            mock_get_iocs.return_value = mock_iocs
            mock_get_summary.return_value = {
                "session_id": "session-123",
                "exchange_count": 2,
            }

            result = await _ss.export_session_json("session-123")

            stats = result["summary_stats"]
            assert stats["total_iocs"] == 3
            assert stats["high_value_iocs"] == 2  # btc and iban
            assert stats["total_messages"] == 4  # Excludes original email
            assert stats["bot_messages"] == 2
            assert stats["scammer_messages"] == 2

    @pytest.mark.asyncio
    async def test_export_json_session_not_found(self):
        """Should raise exception when session not found."""

        with patch.object(
            _ss, "get_session", new_callable=AsyncMock
        ) as mock_get_session:
            mock_get_session.return_value = None

            with pytest.raises(Exception, match="not found"):
                await _ss.export_session_json("nonexistent-session")

    # ------------------------------------------------------------------
    # US-039: enrichment field in JSON export
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_export_json_enriched_ioc_has_enrichment_field(self):
        """Enriched IOC in extracted_iocs should include enrichment sub-dict."""
        mock_session = {
            "id": "session-123",
            "attack_type": "crypto_investment",
            "persona": None,
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": "2026-01-07T18:00:00Z",
            "turn_limit": 20,
        }
        mock_iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qmalicious",
                "confidence": 1.0,
                "created_at": "2026-01-07T17:00:00Z",
            },
        ]
        mock_enrichment = {
            "ioc-1": {
                "threat_score": 85,
                "reputation": "malicious",
                "source": "btc_mempool",
            },
        }

        with (
            patch.object(_ss, "get_session", new_callable=AsyncMock) as m_sess,
            patch.object(_ss, "get_session_messages", new_callable=AsyncMock) as m_msg,
            patch.object(_ss, "get_session_iocs", new_callable=AsyncMock) as m_iocs,
            patch.object(_ss, "get_session_summary", new_callable=AsyncMock) as m_sum,
            patch.object(_ss, "_fetch_iocs_enrichment", return_value=mock_enrichment),
        ):
            m_sess.return_value = mock_session
            m_msg.return_value = []
            m_iocs.return_value = mock_iocs
            m_sum.return_value = {"session_id": "session-123", "exchange_count": 0}

            result = await _ss.export_session_json("session-123")

        enriched_ioc = result["extracted_iocs"][0]
        assert enriched_ioc["enrichment"] == {
            "threat_score": 85,
            "reputation": "malicious",
            "source": "btc_mempool",
        }

    @pytest.mark.asyncio
    async def test_export_json_unenriched_ioc_has_none_enrichment(self):
        """Unenriched IOC in extracted_iocs should have enrichment=None."""
        mock_session = {
            "id": "session-123",
            "attack_type": "nigerian_419",
            "persona": None,
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": None,
            "turn_limit": 20,
        }
        mock_iocs = [
            {
                "id": "ioc-1",
                "type": "iban",
                "value": "DE89370400440532013000",
                "confidence": 0.95,
                "created_at": "2026-01-07T17:00:00Z",
            },
        ]

        with (
            patch.object(_ss, "get_session", new_callable=AsyncMock) as m_sess,
            patch.object(_ss, "get_session_messages", new_callable=AsyncMock) as m_msg,
            patch.object(_ss, "get_session_iocs", new_callable=AsyncMock) as m_iocs,
            patch.object(_ss, "get_session_summary", new_callable=AsyncMock) as m_sum,
            patch.object(_ss, "_fetch_iocs_enrichment", return_value={}),
        ):
            m_sess.return_value = mock_session
            m_msg.return_value = []
            m_iocs.return_value = mock_iocs
            m_sum.return_value = {"session_id": "session-123", "exchange_count": 0}

            result = await _ss.export_session_json("session-123")

        unenriched_ioc = result["extracted_iocs"][0]
        assert unenriched_ioc["enrichment"] is None

    @pytest.mark.asyncio
    async def test_export_json_mixed_enriched_and_plain_iocs(self):
        """JSON export covers both enriched and plain IOCs without errors (US-039)."""
        mock_session = {
            "id": "session-123",
            "attack_type": "crypto_investment",
            "persona": None,
            "created_at": "2026-01-07T17:00:00Z",
            "ended_at": "2026-01-07T18:00:00Z",
            "turn_limit": 20,
        }
        mock_iocs = [
            {
                "id": "ioc-1",
                "type": "btc",
                "value": "bc1qmalicious",
                "confidence": 1.0,
                "created_at": "2026-01-07T17:00:00Z",
            },
            {
                "id": "ioc-2",
                "type": "url",
                "value": "https://phishing.example.com",
                "confidence": 0.8,
                "created_at": "2026-01-07T17:01:00Z",
            },
        ]
        mock_enrichment = {
            "ioc-1": {
                "threat_score": 90,
                "reputation": "malicious",
                "source": "btc_mempool",
            },
            # ioc-2 intentionally absent — should get enrichment=None
        }

        with (
            patch.object(_ss, "get_session", new_callable=AsyncMock) as m_sess,
            patch.object(_ss, "get_session_messages", new_callable=AsyncMock) as m_msg,
            patch.object(_ss, "get_session_iocs", new_callable=AsyncMock) as m_iocs,
            patch.object(_ss, "get_session_summary", new_callable=AsyncMock) as m_sum,
            patch.object(_ss, "_fetch_iocs_enrichment", return_value=mock_enrichment),
        ):
            m_sess.return_value = mock_session
            m_msg.return_value = []
            m_iocs.return_value = mock_iocs
            m_sum.return_value = {"session_id": "session-123", "exchange_count": 0}

            result = await _ss.export_session_json("session-123")

        iocs_out = result["extracted_iocs"]
        assert len(iocs_out) == 2
        assert iocs_out[0]["enrichment"] == {
            "threat_score": 90,
            "reputation": "malicious",
            "source": "btc_mempool",
        }
        assert iocs_out[1]["enrichment"] is None
