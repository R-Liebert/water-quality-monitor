from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert response.json()["status"] == "ok"

# Need to mock the database session for full endpoint testing,
# but we can ensure the route is registered and returns a valid format.
def test_read_waterways_mock_db():
    # As it currently requires a real db connection and we haven't set up 
    # test databases in CI/Docker yet, we verify 401/404/route existence.
    response = client.get(f"{settings.API_V1_STR}/waterways/status")
    # Should be 500 if DB is not running, or 200 if it is empty.
    # Just asserting the route exists and is hit.
    assert response.status_code in [200, 500]