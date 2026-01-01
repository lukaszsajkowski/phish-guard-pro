import pytest
from fastapi.testclient import TestClient
from phishguard.main import app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

def test_analyze_email_success(client: TestClient):
    """Test successful submission of a suspicious email."""
    # Content > 10 chars
    payload = {"content": "Subject: Urgent Update\n\n" + "Please click here."}
    response = client.post("/api/v1/analysis/", json=payload)
    
    # 202 Accepted
    assert response.status_code == 202
    
    data = response.json()
    assert "analysis_id" in data
    assert data["status"] == "processing"
    assert "content_preview" in data

def test_analyze_email_validation_too_short(client: TestClient):
    """Test that email content too short is rejected."""
    payload = {"content": "Hi"}
    response = client.post("/api/v1/analysis/", json=payload)
    assert response.status_code == 422

def test_analyze_email_validation_too_long(client: TestClient):
    """Test that email content too long is rejected."""
    # 50001 chars
    payload = {"content": "A" * 50001}
    response = client.post("/api/v1/analysis/", json=payload)
    assert response.status_code == 422 
