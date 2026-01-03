import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_create_transaction(client: AsyncClient, auth_headers: dict, sample_account, sample_category):
    tx_data = {
        "account_id": sample_account,
        "category_id": sample_category,
        "amount": 50.0,
        "type": "EXPENSE",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "merchant": "Supermarket"
    }
    response = await client.post("/transactions/", json=tx_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["amount"] == 50.0
    assert response.json()["merchant"] == "Supermarket"

@pytest.mark.asyncio
async def test_list_transactions_pagination(client: AsyncClient, auth_headers: dict, sample_account):
    # Create 5 transactions
    for i in range(5):
        await client.post(
            "/transactions/",
            json={
                "account_id": sample_account,
                "amount": float(i + 1),
                "type": "EXPENSE",
                "transaction_date": datetime.now(timezone.utc).isoformat()
            },
            headers=auth_headers
        )
    
    # Test limit
    response = await client.get("/transactions/?limit=2", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
    
    # Test skip
    response = await client.get("/transactions/?skip=3", headers=auth_headers)
    assert response.status_code == 200
    # There were already some transactions from previous tests or this one.
    # In this test we created 5. 
    # Skip 3 should leave at least 2 from this test.
    assert len(response.json()) >= 2

@pytest.mark.asyncio
async def test_list_transactions_search(client: AsyncClient, auth_headers: dict, sample_account):
    await client.post(
        "/transactions/",
        json={
            "account_id": sample_account,
            "amount": 10.0,
            "type": "EXPENSE",
            "transaction_date": datetime.now(timezone.utc).isoformat(),
            "merchant": "Unique Merchant",
            "note": "Secret note"
        },
        headers=auth_headers
    )
    
    # Search by merchant
    response = await client.get("/transactions/?q=Unique", headers=auth_headers)
    assert len(response.json()) == 1
    assert response.json()[0]["merchant"] == "Unique Merchant"
    
    # Search by note
    response = await client.get("/transactions/?q=Secret", headers=auth_headers)
    assert len(response.json()) == 1
    assert response.json()[0]["note"] == "Secret note"
    
    # No match
    response = await client.get("/transactions/?q=NotExist", headers=auth_headers)
    assert len(response.json()) == 0

@pytest.mark.asyncio
async def test_list_transactions_date_range(client: AsyncClient, auth_headers: dict, sample_account):
    # Transaction in the past
    await client.post(
        "/transactions/",
        json={
            "account_id": sample_account,
            "amount": 10.0,
            "type": "EXPENSE",
            "transaction_date": "2023-01-01T10:00:00Z"
        },
        headers=auth_headers
    )
    # Transaction in the future
    await client.post(
        "/transactions/",
        json={
            "account_id": sample_account,
            "amount": 20.0,
            "type": "EXPENSE",
            "transaction_date": "2023-12-31T10:00:00Z"
        },
        headers=auth_headers
    )
    
    # Filter by start_date
    response = await client.get("/transactions/?start_date=2023-06-01T00:00:00", headers=auth_headers)
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 20.0
    
    # Filter by end_date
    response = await client.get("/transactions/?end_date=2023-06-01T00:00:00", headers=auth_headers)
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 10.0
    
    response = await client.get("/transactions/?start_date=2023-01-01T00:00:00&end_date=2023-12-31T23:59:59", headers=auth_headers)
    assert len(response.json()) == 2

@pytest.mark.asyncio
async def test_update_transaction_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.patch("/transactions/non-existent", json={"amount": 10.0}, headers=auth_headers)
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_delete_transaction_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.delete("/transactions/non-existent", headers=auth_headers)
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_transaction_documents_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.get("/transactions/non-existent/documents", headers=auth_headers)
    assert res.status_code == 404
