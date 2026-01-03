import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings

client = TestClient(app)

def test_cors_disabled_by_default():
    # Since DEV_MODE is False by default, CORSMiddleware shouldn't be active
    origin = "http://localhost:3000"
    response = client.options(
        "/",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    # Should NOT have CORS headers because middleware didn't run
    assert "access-control-allow-origin" not in response.headers

def test_options_method_supported_on_endpoints():
    # Test OPTIONS on a root endpoint
    response = client.options("/")
    assert response.status_code == 200
    
    # Test OPTIONS on an API endpoint
    response = client.options("/accounts/")
    assert response.status_code == 200
