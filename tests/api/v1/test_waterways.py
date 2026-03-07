from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_read_root():
    # Root redirects to /frontend/index.html
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/frontend/index.html"

from unittest.mock import patch, MagicMock, AsyncMock
from app.db.session import get_db

@patch("app.api.v1.endpoints.waterways.get_db")
def test_read_waterways_status(mock_get_db):
    # Mocking db dependency because there is no test db setup easily available
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().all.return_value = []
    mock_db.execute.return_value = mock_result

    # We use a mocked app dependency to bypass db connection
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        # Verify the actual API status endpoint
        response = client.get(f"{settings.API_V1_STR}/waterways/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    finally:
        # Clean up the override
        app.dependency_overrides = {}
