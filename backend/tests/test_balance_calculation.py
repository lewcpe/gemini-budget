import pytest
from httpx import AsyncClient
from datetime import datetime, timezone

@pytest.mark.asyncio
async def test_balance_calculation_flow(client: AsyncClient, auth_headers: dict):
    # 1. Create an account
    account_data = {
        "name": "Test Account",
        "type": "ASSET",
        "currency": "USD"
    }
    response = await client.post("/accounts/", json=account_data, headers=auth_headers)
    assert response.status_code == 200
    account = response.json()
    account_id = account["id"]
    assert account["current_balance"] == 0.0

    # 2. Create an INCOME transaction
    income_data = {
        "account_id": account_id,
        "amount": 1000.0,
        "type": "INCOME",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "merchant": "Salary"
    }
    response = await client.post("/transactions/", json=income_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Check account balance
    response = await client.get("/accounts/", headers=auth_headers)
    accounts = response.json()
    account = next(acc for acc in accounts if acc["id"] == account_id)
    assert account["current_balance"] == 1000.0

    # 3. Create an EXPENSE transaction
    expense_data = {
        "account_id": account_id,
        "amount": 200.0,
        "type": "EXPENSE",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "merchant": "Groceries"
    }
    response = await client.post("/transactions/", json=expense_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Check account balance
    response = await client.get("/accounts/", headers=auth_headers)
    accounts = response.json()
    account = next(acc for acc in accounts if acc["id"] == account_id)
    assert account["current_balance"] == 800.0

    # 4. Create a target account for TRANSFER
    target_account_data = {
        "name": "Savings",
        "type": "ASSET",
        "currency": "USD"
    }
    response = await client.post("/accounts/", json=target_account_data, headers=auth_headers)
    target_account = response.json()
    target_account_id = target_account["id"]

    # 5. Create a TRANSFER transaction
    transfer_data = {
        "account_id": account_id,
        "target_account_id": target_account_id,
        "amount": 300.0,
        "type": "TRANSFER",
        "transaction_date": datetime.now(timezone.utc).isoformat(),
        "note": "Transfer to savings"
    }
    tx_response = await client.post("/transactions/", json=transfer_data, headers=auth_headers)
    assert tx_response.status_code == 200
    
    # Check both balances
    response = await client.get("/accounts/", headers=auth_headers)
    accounts = response.json()
    account = next(acc for acc in accounts if acc["id"] == account_id)
    target_account = next(acc for acc in accounts if acc["id"] == target_account_id)
    assert account["current_balance"] == 500.0
    assert target_account["current_balance"] == 300.0

    # 6. Update transaction amount
    tx_id = tx_response.json()["id"]
    update_data = {"amount": 500.0}
    response = await client.patch(f"/transactions/{tx_id}", json=update_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Check balances
    response = await client.get("/accounts/", headers=auth_headers)
    accounts = response.json()
    account = next(acc for acc in accounts if acc["id"] == account_id)
    target_account = next(acc for acc in accounts if acc["id"] == target_account_id)
    assert account["current_balance"] == 300.0
    assert target_account["current_balance"] == 500.0

    # 7. Delete transaction
    response = await client.delete(f"/transactions/{tx_id}", headers=auth_headers)
    assert response.status_code == 204
    
    # Check balances are restored
    response = await client.get("/accounts/", headers=auth_headers)
    accounts = response.json()
    account = next(acc for acc in accounts if acc["id"] == account_id)
    target_account = next(acc for acc in accounts if acc["id"] == target_account_id)
    assert account["current_balance"] == 800.0
    assert target_account["current_balance"] == 0.0
