from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_get_copernicus_config():
    """
    Test the Copernicus WMS configuration endpoint to ensure it returns
    the correct structure and expected proxy URL.
    """
    response = client.get(f"{settings.API_V1_STR}/copernicus/config")

    assert response.status_code == 200
    data = response.json()

    # Verify expected keys exist
    assert "enabled" in data
    assert "proxy_url" in data

    # Verify value types and values
    assert isinstance(data["enabled"], bool)
    assert data["proxy_url"] == "/api/v1/copernicus/wms"

    # Verify the 'enabled' logic based on settings
    expected_enabled = settings.COPERNICUS_CLIENT_ID is not None
    assert data["enabled"] == expected_enabled
