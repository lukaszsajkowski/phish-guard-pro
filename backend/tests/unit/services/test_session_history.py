"""Unit tests for session history list functionality (US-028)."""

import pytest
from unittest.mock import MagicMock, patch


class TestGetUserSessions:
    """Test cases for get_user_sessions function."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client with chainable methods."""
        mock_client = MagicMock()
        return mock_client

    def _setup_sessions_mock(self, mock_client, sessions_data, total_count):
        """Helper to setup mock for sessions query."""
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()

        mock_client.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = MagicMock(
            data=sessions_data,
            count=total_count,
        )

        return mock_table

    def _setup_messages_count_mock(self, mock_client, counts_by_session):
        """Helper to setup mock for messages count query."""
        original_table = mock_client.table.return_value

        def table_side_effect(table_name):
            if table_name == "messages":
                mock_messages_table = MagicMock()
                mock_select = MagicMock()
                mock_eq_session = MagicMock()
                mock_eq_role = MagicMock()

                mock_messages_table.select.return_value = mock_select
                mock_select.eq.return_value = mock_eq_session
                mock_eq_session.eq.return_value = mock_eq_role

                def execute_count(session_id=None):
                    # Default count if session_id not found
                    result = MagicMock()
                    result.count = counts_by_session.get(session_id, 0)
                    return result

                # Store the session_id from the eq call for later use
                def eq_session_side_effect(field, value):
                    mock_eq_role.execute.return_value = MagicMock(
                        count=counts_by_session.get(value, 0)
                    )
                    return mock_eq_role

                mock_select.eq.side_effect = eq_session_side_effect
                return mock_messages_table
            elif table_name == "ioc_extracted":
                mock_ioc_table = MagicMock()
                mock_select = MagicMock()
                mock_eq = MagicMock()

                mock_ioc_table.select.return_value = mock_select
                mock_select.eq.return_value = mock_eq
                mock_eq.execute.return_value = MagicMock(data=[])
                return mock_ioc_table
            return original_table

        mock_client.table.side_effect = table_side_effect

    @pytest.mark.asyncio
    async def test_get_user_sessions_returns_empty_list_for_no_sessions(
        self, mock_supabase
    ):
        """Test that get_user_sessions returns empty list when user has no sessions."""
        self._setup_sessions_mock(mock_supabase, [], 0)

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            sessions, total = await get_user_sessions("user-123")

            assert sessions == []
            assert total == 0

    @pytest.mark.asyncio
    async def test_get_user_sessions_returns_sessions_with_turn_counts(
        self, mock_supabase
    ):
        """Test that sessions are returned with turn counts."""
        sessions_data = [
            {
                "id": "session-1",
                "user_id": "user-123",
                "title": "Test session",
                "attack_type": "nigerian_419",
                "status": "active",
                "created_at": "2024-01-15T10:30:00Z",
                "persona": {"name": "John Doe"},
            }
        ]

        # First call returns sessions table
        mock_sessions_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()

        mock_sessions_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = MagicMock(data=sessions_data, count=1)

        # Messages table mock
        mock_messages_table = MagicMock()
        mock_msg_select = MagicMock()
        mock_msg_eq1 = MagicMock()
        mock_msg_eq2 = MagicMock()

        mock_messages_table.select.return_value = mock_msg_select
        mock_msg_select.eq.return_value = mock_msg_eq1
        mock_msg_eq1.eq.return_value = mock_msg_eq2
        mock_msg_eq2.execute.return_value = MagicMock(count=5)

        # IOC table mock
        mock_ioc_table = MagicMock()
        mock_ioc_select = MagicMock()
        mock_ioc_eq = MagicMock()

        mock_ioc_table.select.return_value = mock_ioc_select
        mock_ioc_select.eq.return_value = mock_ioc_eq
        mock_ioc_eq.execute.return_value = MagicMock(data=[])

        def table_side_effect(name):
            if name == "sessions":
                return mock_sessions_table
            elif name == "messages":
                return mock_messages_table
            elif name == "ioc_extracted":
                return mock_ioc_table

        mock_supabase.table.side_effect = table_side_effect

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            sessions, total = await get_user_sessions("user-123")

            assert len(sessions) == 1
            assert total == 1
            assert sessions[0]["turn_count"] == 5
            assert sessions[0]["risk_score"] >= 1

    @pytest.mark.asyncio
    async def test_get_user_sessions_pagination_page_1(self, mock_supabase):
        """Test pagination calculates correct offset for page 1."""
        self._setup_sessions_mock(mock_supabase, [], 0)

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            await get_user_sessions("user-123", page=1, per_page=20)

            # Verify range was called with correct offset (0, 19)
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.assert_called_once_with(
                0, 19
            )

    @pytest.mark.asyncio
    async def test_get_user_sessions_pagination_page_2(self, mock_supabase):
        """Test pagination calculates correct offset for page 2."""
        self._setup_sessions_mock(mock_supabase, [], 0)

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            await get_user_sessions("user-123", page=2, per_page=20)

            # Verify range was called with correct offset (20, 39)
            mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.range.assert_called_once_with(
                20, 39
            )

    @pytest.mark.asyncio
    async def test_get_user_sessions_invalid_page_raises_error(self, mock_supabase):
        """Test that page < 1 raises ValueError."""
        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            with pytest.raises(ValueError, match="Page must be >= 1"):
                await get_user_sessions("user-123", page=0)

    @pytest.mark.asyncio
    async def test_get_user_sessions_invalid_per_page_raises_error(self, mock_supabase):
        """Test that per_page outside range raises ValueError."""
        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            with pytest.raises(ValueError, match="per_page must be between 1 and 100"):
                await get_user_sessions("user-123", per_page=0)

            with pytest.raises(ValueError, match="per_page must be between 1 and 100"):
                await get_user_sessions("user-123", per_page=101)

    @pytest.mark.asyncio
    async def test_get_user_sessions_includes_risk_score(self, mock_supabase):
        """Test that sessions include calculated risk score."""
        sessions_data = [
            {
                "id": "session-1",
                "user_id": "user-123",
                "title": "CEO Fraud attempt",
                "attack_type": "ceo_fraud",  # High severity
                "status": "active",
                "created_at": "2024-01-15T10:30:00Z",
                "persona": None,
            }
        ]

        mock_sessions_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_order = MagicMock()
        mock_range = MagicMock()

        mock_sessions_table.select.return_value = mock_select
        mock_select.eq.return_value = mock_eq
        mock_eq.order.return_value = mock_order
        mock_order.range.return_value = mock_range
        mock_range.execute.return_value = MagicMock(data=sessions_data, count=1)

        mock_messages_table = MagicMock()
        mock_msg_select = MagicMock()
        mock_msg_eq1 = MagicMock()
        mock_msg_eq2 = MagicMock()

        mock_messages_table.select.return_value = mock_msg_select
        mock_msg_select.eq.return_value = mock_msg_eq1
        mock_msg_eq1.eq.return_value = mock_msg_eq2
        mock_msg_eq2.execute.return_value = MagicMock(count=0)

        # IOC table with high-value IOC
        mock_ioc_table = MagicMock()
        mock_ioc_select = MagicMock()
        mock_ioc_eq = MagicMock()

        mock_ioc_table.select.return_value = mock_ioc_select
        mock_ioc_select.eq.return_value = mock_ioc_eq
        mock_ioc_eq.execute.return_value = MagicMock(
            data=[{"type": "btc"}, {"type": "iban"}]
        )

        def table_side_effect(name):
            if name == "sessions":
                return mock_sessions_table
            elif name == "messages":
                return mock_messages_table
            elif name == "ioc_extracted":
                return mock_ioc_table

        mock_supabase.table.side_effect = table_side_effect

        with patch(
            "phishguard.services.session_service._get_supabase_client",
            return_value=mock_supabase,
        ):
            from phishguard.services.session_service import get_user_sessions

            sessions, _ = await get_user_sessions("user-123")

            # CEO fraud (4) + 2 IOCs (2) + 2 high-value IOCs (2) = 8
            assert sessions[0]["risk_score"] == 8


class TestSessionHistoryItemModel:
    """Test cases for SessionHistoryItem Pydantic model."""

    def test_session_history_item_valid_data(self):
        """Test creating SessionHistoryItem with valid data."""
        from phishguard.api.routers.session import SessionHistoryItem

        item = SessionHistoryItem(
            session_id="session-123",
            title="Test session",
            attack_type="nigerian_419",
            attack_type_display="Nigerian 419",
            persona_name="John Doe",
            turn_count=5,
            created_at="2024-01-15T10:30:00Z",
            risk_score=7,
            status="active",
        )

        assert item.session_id == "session-123"
        assert item.attack_type_display == "Nigerian 419"
        assert item.turn_count == 5
        assert item.risk_score == 7

    def test_session_history_item_optional_fields(self):
        """Test SessionHistoryItem with optional fields as None."""
        from phishguard.api.routers.session import SessionHistoryItem

        item = SessionHistoryItem(
            session_id="session-123",
            title=None,
            attack_type=None,
            attack_type_display="Pending Classification",
            persona_name=None,
            turn_count=0,
            created_at="2024-01-15T10:30:00Z",
            risk_score=1,
            status="active",
        )

        assert item.title is None
        assert item.attack_type is None
        assert item.persona_name is None

    def test_session_history_item_risk_score_validation(self):
        """Test that risk_score must be between 1 and 10."""
        from phishguard.api.routers.session import SessionHistoryItem
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SessionHistoryItem(
                session_id="session-123",
                attack_type_display="Test",
                turn_count=0,
                created_at="2024-01-15T10:30:00Z",
                risk_score=0,  # Invalid: must be >= 1
                status="active",
            )

        with pytest.raises(ValidationError):
            SessionHistoryItem(
                session_id="session-123",
                attack_type_display="Test",
                turn_count=0,
                created_at="2024-01-15T10:30:00Z",
                risk_score=11,  # Invalid: must be <= 10
                status="active",
            )


class TestPaginatedSessionsResponseModel:
    """Test cases for PaginatedSessionsResponse Pydantic model."""

    def test_paginated_response_valid_data(self):
        """Test creating PaginatedSessionsResponse with valid data."""
        from phishguard.api.routers.session import (
            PaginatedSessionsResponse,
            SessionHistoryItem,
        )

        item = SessionHistoryItem(
            session_id="session-123",
            attack_type_display="Nigerian 419",
            turn_count=5,
            created_at="2024-01-15T10:30:00Z",
            risk_score=7,
            status="active",
        )

        response = PaginatedSessionsResponse(
            items=[item],
            total=25,
            page=1,
            per_page=20,
            total_pages=2,
        )

        assert len(response.items) == 1
        assert response.total == 25
        assert response.page == 1
        assert response.per_page == 20
        assert response.total_pages == 2

    def test_paginated_response_empty_items(self):
        """Test PaginatedSessionsResponse with empty items list."""
        from phishguard.api.routers.session import PaginatedSessionsResponse

        response = PaginatedSessionsResponse(
            items=[],
            total=0,
            page=1,
            per_page=20,
            total_pages=0,
        )

        assert response.items == []
        assert response.total == 0
        assert response.total_pages == 0
