import pytest
from httpx import AsyncClient
from backend.config import settings

@pytest.mark.asyncio
async def test_get_current_user_new_user(client: AsyncClient):
    # Test lazy registration
    email = "newuser@example.com"
    res = await client.get("/accounts/", headers={settings.AUTH_EMAIL_HEADER: email})
    assert res.status_code == 200
    # The user should have been created in the background
    accounts = res.json()
    assert len(accounts) == 1
    assert accounts[0]["name"] == "Petty Cash Account"
    assert accounts[0]["type"] == "ASSET"

@pytest.mark.asyncio
async def test_get_current_user_missing_header(client: AsyncClient):
    res = await client.get("/accounts/") # No header
    assert res.status_code == 401
    assert "Missing" in res.json()["detail"]

@pytest.mark.asyncio
async def test_get_current_user_empty_header(client: AsyncClient):
    res = await client.get("/accounts/", headers={settings.AUTH_EMAIL_HEADER: ""})
    assert res.status_code == 401
