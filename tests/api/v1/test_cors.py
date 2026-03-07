from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_cors_headers():
    # Test that an allowed origin gets the correct CORS headers
    allowed_origin = settings.BACKEND_CORS_ORIGINS[0]
    response = client.options(
        f"{settings.API_V1_STR}/waterways/status",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == allowed_origin

    # Optional: test an unauthorized origin does not get the header
    unauthorized_origin = "http://malicious.com"
    response_unauthorized = client.options(
        f"{settings.API_V1_STR}/waterways/status",
        headers={
            "Origin": unauthorized_origin,
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response_unauthorized.status_code == 400
