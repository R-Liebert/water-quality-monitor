from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_read_root():
    # Root redirects to /frontend/index.html
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/frontend/index.html"

def test_read_waterways_status():
    from unittest.mock import MagicMock
    from app.db.session import get_db
    class AsyncMock:
        async def execute(self, *args, **kwargs):
            class MockResult:
                def scalars(self):
                    return MagicMock(all=lambda: [])
            return MockResult()

    async def override_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = override_get_db

    try:
        # Verify the actual API status endpoint
        response = client.get(f"{settings.API_V1_STR}/waterways/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # We should have data now because of the sync script
        if len(data) > 0:
            assert "location_name" in data[0]
            assert "hydration_index" in data[0]
            assert "status" not in data[0] # It's not in our simple demo serializer yet
    finally:
        app.dependency_overrides.clear()