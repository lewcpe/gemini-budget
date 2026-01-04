import pytest
from httpx import AsyncClient
from backend.config import settings

@pytest.mark.asyncio
async def test_merchant_crud(client: AsyncClient, auth_headers: dict):
    # 1. Create a category for the merchant
    cat_res = await client.post(
        "/categories/",
        json={"name": "Retail", "type": "EXPENSE"},
        headers=auth_headers
    )
    cat_id = cat_res.json()["id"]
    
    # 2. Create Merchant
    merchant_res = await client.post(
        "/merchants/",
        json={"name": "Amazon", "default_category_id": cat_id},
        headers=auth_headers
    )
    assert merchant_res.status_code == 200
    merchant_data = merchant_res.json()
    assert merchant_data["name"] == "Amazon"
    merchant_id = merchant_data["id"]
    
    # 3. List Merchants (with search)
    list_res = await client.get("/merchants/?q=Amaz", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(m["id"] == merchant_id for m in list_res.json())
    
    # 4. Update Merchant
    update_res = await client.patch(
        f"/merchants/{merchant_id}",
        json={"name": "Amazon Prime"},
        headers=auth_headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Amazon Prime"
    
    # 5. Delete Merchant
    del_res = await client.delete(f"/merchants/{merchant_id}", headers=auth_headers)
    assert del_res.status_code == 204
    
    # Verify deleted
    list_res_final = await client.get("/merchants/", headers=auth_headers)
    assert all(m["id"] != merchant_id for m in list_res_final.json())

@pytest.mark.asyncio
async def test_category_initialization_on_registration(client: AsyncClient):
    # Test lazy registration triggers category creation
    email = "new_cat_user@example.com"
    res = await client.get("/categories/", headers={settings.AUTH_EMAIL_HEADER: email})
    assert res.status_code == 200
    categories = res.json()
    
    # Check for some default categories
    cat_names = [c["name"] for c in categories]
    assert "Food" in cat_names
    assert "Salary" in cat_names
    assert "Others" in cat_names
    assert len(categories) >= 8
