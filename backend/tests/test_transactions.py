import pytest
from httpx import AsyncClient
from datetime import datetime

@pytest.mark.asyncio
async def test_create_transaction(client: AsyncClient, auth_headers: dict, sample_account, sample_category):
    tx_data = {
        "account_id": sample_account,
        "category_id": sample_category,
        "amount": 50.0,
        "type": "EXPENSE",
        "transaction_date": datetime.utcnow().isoformat(),
        "merchant": "Supermarket"
    }
    response = await client.post("/transactions/", json=tx_data, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["amount"] == 50.0
    assert response.json()["merchant"] == "Supermarket"

@pytest.mark.asyncio
async def test_list_transactions(client: AsyncClient, auth_headers: dict, sample_account):
    await client.post(
        "/transactions/",
        json={
            "account_id": sample_account,
            "amount": 20.0,
            "type": "EXPENSE",
            "transaction_date": datetime.utcnow().isoformat()
        },
        headers=auth_headers
    )
    
    response = await client.get("/transactions/", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1
