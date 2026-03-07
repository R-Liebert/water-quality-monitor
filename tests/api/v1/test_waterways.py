from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.main import app
from app.core.config import settings
from app.api.v1.endpoints.waterways import get_db

client = TestClient(app)

def test_read_root():
    # Root redirects to /frontend/index.html
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/frontend/index.html"

def test_read_waterways_status_empty():
    """Test that the endpoint correctly handles an empty list of records."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    # Return empty list from db
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = client.get(f"{settings.API_V1_STR}/waterways/status")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0
    finally:
        # Clean up
        app.dependency_overrides.clear()

def test_read_waterways_status_with_data():
    """Test that the endpoint correctly serializes database records."""
    class MockObservation:
        def __init__(self, id, name, idx, turb, risk, spill, ts):
            self.id = id
            self.location_name = name
            self.hydration_index = idx
            self.turbidity = turb
            self.runoff_risk_score = risk
            self.sewage_spill_active = spill
            self.timestamp = ts

    test_date = datetime(2023, 10, 25, 12, 0, 0)
    mock_obs = MockObservation(
        1, "Test River", 8.5, 12.0, 0.4, False, test_date
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_obs]
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = client.get(f"{settings.API_V1_STR}/waterways/status")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 1

        assert data[0]["id"] == 1
        assert data[0]["location_name"] == "Test River"
        assert data[0]["hydration_index"] == 8.5
        assert data[0]["turbidity"] == 12.0
        assert data[0]["runoff_risk_score"] == 0.4
        assert data[0]["sewage_spill_active"] is False
        assert data[0]["timestamp"] == test_date.isoformat()
    finally:
        # Clean up
        app.dependency_overrides.clear()

def test_read_waterways_status_pagination():
    """Test that skip and limit parameters are handled (though we just verify they don't crash and we get a 200)."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        # Send custom skip and limit
        response = client.get(f"{settings.API_V1_STR}/waterways/status?skip=10&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    finally:
        app.dependency_overrides.clear()

def test_read_waterways_viewport_sentinel_only():
    """Test the viewport endpoint with sentinel_only=True."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    # Mocking the scalar result returned by execute().scalar()
    mock_result.scalar.return_value = {
        "type": "FeatureCollection",
        "features": []
    }
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session
    try:
        response = client.get(f"{settings.API_V1_STR}/waterways/viewport?min_lat=50.0&max_lat=51.0&min_lng=-1.0&max_lng=0.0&zoom=10&sentinel_only=true")
        assert response.status_code == 200
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data
        
        # Verify execute was called
        mock_session.execute.assert_called_once()
    finally:
        app.dependency_overrides.clear()