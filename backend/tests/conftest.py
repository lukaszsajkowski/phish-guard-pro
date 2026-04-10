import pytest


@pytest.fixture(scope="session")
def check_db_connection():
    """Verify DB connection before tests (optional)."""
    # We don't necessarily want to fail if DB isn't reachable for unit tests
    # but for integration tests it's good to know.
    pass


@pytest.fixture(autouse=True)
def cleanup_test_user_data():
    """
    Fixture to clean up any data created by 'test-user-id' (common mock ID).
    This logic currently assumes tests might mock user_id but hit real DB.
    """
    yield
    # Teardown logic
    # In a real integration test suite hitting Supabase, we would:
    # 1. Inspect what data was created.
    # 2. Delete it via Supabase Admin client.

    # settings = get_settings()
    # if settings.supabase_service_role_key:
    #     supabase = create_client(
    #         settings.supabase_url, settings.supabase_service_role_key
    #     )
    #     # supabase.table("sessions").delete().eq("user_id", "test-user-id").execute()
