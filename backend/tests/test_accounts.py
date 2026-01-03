import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_account(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/accounts/",
        json={"name": "Checking", "type": "ASSET", "sub_type": "CASH", "current_balance": 1000.0},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Checking"
    assert data["current_balance"] == 1000.0
    assert "id" in data

@pytest.mark.asyncio
async def test_list_accounts(client: AsyncClient, auth_headers: dict):
    # Create an account first
    await client.post(
        "/accounts/",
        json={"name": "Savings", "type": "ASSET", "current_balance": 5000.0},
        headers=auth_headers
    )
    
    response = await client.get("/accounts/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(a["name"] == "Savings" for a in data)

@pytest.mark.asyncio
async def test_account_user_isolation(client: AsyncClient, auth_headers: dict, auth_headers_other: dict):
    # User 1 creates an account
    await client.post(
        "/accounts/",
        json={"name": "User1 Asset", "type": "ASSET"},
        headers=auth_headers
    )
    
    # User 2 list accounts, should be empty
    response = await client.get("/accounts/", headers=auth_headers_other)
    assert response.status_code == 200
    assert len(response.json()) == 0

@pytest.mark.asyncio
async def test_update_account(client: AsyncClient, auth_headers: dict):
    # Create
    create_res = await client.post(
        "/accounts/",
        json={"name": "Old Name", "type": "ASSET"},
        headers=auth_headers
    )
    acc_id = create_res.json()["id"]
    
    # Update
    update_res = await client.patch(
        f"/accounts/{acc_id}",
        json={"name": "New Name", "current_balance": 200.0},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "New Name"
    assert update_res.json()["current_balance"] == 200.0

@pytest.mark.asyncio
async def test_delete_account(client: AsyncClient, auth_headers: dict):
    # Create
    create_res = await client.post(
        "/accounts/",
        json={"name": "To Delete", "type": "ASSET"},
        headers=auth_headers
    )
    acc_id = create_res.json()["id"]
    
    # Delete
    del_res = await client.delete(f"/accounts/{acc_id}", headers=auth_headers)
    assert del_res.status_code == 204
    
    # Verify deleted
    list_res = await client.get("/accounts/", headers=auth_headers)
    assert all(a["id"] != acc_id for a in list_res.json())

@pytest.mark.asyncio
async def test_update_account_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.patch("/accounts/non-existent", json={"name": "Fail"}, headers=auth_headers)
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_delete_account_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.delete("/accounts/non-existent", headers=auth_headers)
    assert res.status_code == 404
