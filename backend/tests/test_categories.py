import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_category(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/categories/",
        json={"name": "Food", "type": "EXPENSE"},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Food"
    assert data["type"] == "EXPENSE"

@pytest.mark.asyncio
async def test_category_hierarchy(client: AsyncClient, auth_headers: dict):
    # Create parent
    parent_res = await client.post(
        "/categories/",
        json={"name": "Groceries", "type": "EXPENSE"},
        headers=auth_headers
    )
    parent_id = parent_res.json()["id"]
    
    # Create child
    child_res = await client.post(
        "/categories/",
        json={"name": "Vegetables", "type": "EXPENSE", "parent_category_id": parent_id},
        headers=auth_headers
    )
    assert child_res.status_code == 200
    assert child_res.json()["parent_category_id"] == parent_id

@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, auth_headers: dict):
    await client.post(
        "/categories/",
        json={"name": "Salary", "type": "INCOME"},
        headers=auth_headers
    )
    
    response = await client.get("/categories/", headers=auth_headers)
    assert response.status_code == 200
    assert any(c["name"] == "Salary" for c in response.json())
