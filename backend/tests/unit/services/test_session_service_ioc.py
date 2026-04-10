"""Unit tests for IOC-related session service functions."""

from unittest.mock import MagicMock, patch

import pytest


class TestSaveExtractedIOCs:
    """Test cases for save_extracted_iocs function."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table

    @pytest.mark.asyncio
    async def test_save_empty_iocs_returns_empty_list(self, mock_supabase):
        """Test that saving empty IOCs returns empty list without DB call."""
        mock_client, mock_table = mock_supabase

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_client,
        ):
            from phishguard.services.session_service import save_extracted_iocs

            result = await save_extracted_iocs("session-123", [])

            assert result == []
            # Should not call insert for empty list
            mock_table.insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_single_ioc(self, mock_supabase):
        """Test saving a single IOC."""
        mock_client, mock_table = mock_supabase
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(
            data=[{"id": "ioc-uuid-123", "type": "btc", "value": "bc1..."}]
        )

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_client,
        ):
            from phishguard.services.session_service import save_extracted_iocs

            iocs = [
                {
                    "type": "btc_wallet",
                    "value": "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                    "is_high_value": True,
                }
            ]
            result = await save_extracted_iocs("session-123", iocs)

            assert len(result) == 1
            assert result[0] == "ioc-uuid-123"

            # Verify insert was called with correct data
            mock_table.insert.assert_called_once()
            call_args = mock_table.insert.call_args[0][0]
            assert len(call_args) == 1
            assert call_args[0]["session_id"] == "session-123"
            assert call_args[0]["type"] == "btc"  # btc_wallet mapped to btc
            assert call_args[0]["confidence"] == 1.0  # high_value = 1.0

    @pytest.mark.asyncio
    async def test_save_multiple_iocs(self, mock_supabase):
        """Test saving multiple IOCs of different types."""
        mock_client, mock_table = mock_supabase
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(
            data=[
                {"id": "ioc-1", "type": "btc"},
                {"id": "ioc-2", "type": "iban"},
                {"id": "ioc-3", "type": "phone"},
            ]
        )

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_client,
        ):
            from phishguard.services.session_service import save_extracted_iocs

            iocs = [
                {"type": "btc_wallet", "value": "bc1...", "is_high_value": True},
                {"type": "iban", "value": "DE89...", "is_high_value": True},
                {"type": "phone", "value": "+1-555...", "is_high_value": False},
            ]
            result = await save_extracted_iocs("session-123", iocs)

            assert len(result) == 3
            mock_table.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_low_value_ioc_confidence(self, mock_supabase):
        """Test that low-value IOCs get 0.8 confidence."""
        mock_client, mock_table = mock_supabase
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(
            data=[{"id": "ioc-phone", "type": "phone"}]
        )

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_client,
        ):
            from phishguard.services.session_service import save_extracted_iocs

            iocs = [{"type": "phone", "value": "+1-555", "is_high_value": False}]
            await save_extracted_iocs("session-123", iocs)

            call_args = mock_table.insert.call_args[0][0]
            assert call_args[0]["confidence"] == 0.8  # low_value = 0.8


class TestGetSessionIOCs:
    """Test cases for get_session_iocs function."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client."""
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        return mock_client, mock_table

    @pytest.mark.asyncio
    async def test_get_iocs_returns_list(self, mock_supabase):
        """Test that get_session_iocs returns list of IOCs."""
        mock_client, mock_table = mock_supabase
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.execute.return_value = MagicMock(
            data=[
                {"id": "ioc-1", "type": "btc", "value": "bc1..."},
                {"id": "ioc-2", "type": "iban", "value": "DE89..."},
            ]
        )

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_client,
        ):
            from phishguard.services.session_service import get_session_iocs

            result = await get_session_iocs("session-123")

            assert len(result) == 2
            assert result[0]["type"] == "btc"
            assert result[1]["type"] == "iban"

    @pytest.mark.asyncio
    async def test_get_iocs_empty_session(self, mock_supabase):
        """Test that get_session_iocs returns empty list for session with no IOCs."""
        mock_client, mock_table = mock_supabase
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.execute.return_value = MagicMock(data=[])

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_client,
        ):
            from phishguard.services.session_service import get_session_iocs

            result = await get_session_iocs("session-no-iocs")

            assert result == []
