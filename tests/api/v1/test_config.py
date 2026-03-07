from fastapi.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_get_frontend_config_with_api_key():
    """Test the frontend config endpoint when GOOGLE_API_KEY is set."""
    # We use patch to override the settings.GOOGLE_API_KEY value temporarily
    with patch("app.api.v1.endpoints.config.settings.GOOGLE_API_KEY", "test_google_api_key_123"):
        response = client.get(f"{settings.API_V1_STR}/config/frontend-config")
        assert response.status_code == 200
        data = response.json()
        assert "google_maps_api_key" in data
        assert data["google_maps_api_key"] == "test_google_api_key_123"

def test_get_frontend_config_without_api_key():
    """Test the frontend config endpoint when GOOGLE_API_KEY is not set."""
    with patch("app.api.v1.endpoints.config.settings.GOOGLE_API_KEY", None):
        response = client.get(f"{settings.API_V1_STR}/config/frontend-config")
        assert response.status_code == 200
        data = response.json()
        assert "google_maps_api_key" in data
        assert data["google_maps_api_key"] is None

def test_get_frontend_config_empty_string_api_key():
    """Test the frontend config endpoint when GOOGLE_API_KEY is an empty string."""
    with patch("app.api.v1.endpoints.config.settings.GOOGLE_API_KEY", ""):
        response = client.get(f"{settings.API_V1_STR}/config/frontend-config")
        assert response.status_code == 200
        data = response.json()
        assert "google_maps_api_key" in data
        # Based on the code: "settings.GOOGLE_API_KEY if settings.GOOGLE_API_KEY else None"
        # An empty string evaluates to False, so it should return None.
        assert data["google_maps_api_key"] is None
