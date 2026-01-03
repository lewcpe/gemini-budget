import pytest
from httpx import AsyncClient
from sqlalchemy import select
from backend.models import Account, Transaction, User

@pytest.mark.asyncio
async def test_delete_account_cascades_transactions(client: AsyncClient, db_session, auth_headers):
    # 1. Setup: Create an account and some transactions
    await client.get("/accounts/", headers=auth_headers) # Trigger user creation
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    acc = Account(user_id=user.id, name="Temp Account", type="ASSET")
    db_session.add(acc)
    await db_session.flush()
    
    tx1 = Transaction(
        user_id=user.id,
        account_id=acc.id,
        amount=100.0,
        type="EXPENSE",
        transaction_date=user.created_at # any date
    )
    tx2 = Transaction(
        user_id=user.id,
        account_id=acc.id,
        amount=200.0,
        type="EXPENSE",
        transaction_date=user.created_at
    )
    db_session.add_all([tx1, tx2])
    await db_session.commit()
    
    # 2. Verify they exist
    res = await db_session.execute(select(Transaction).where(Transaction.account_id == acc.id))
    assert len(res.scalars().all()) == 2
    
    # 3. Delete the account via API
    response = await client.delete(f"/accounts/{acc.id}", headers=auth_headers)
    assert response.status_code == 204
    
    # 4. Verify account is gone
    res_acc = await db_session.execute(select(Account).where(Account.id == acc.id))
    assert res_acc.scalars().first() is None
    
    # 5. Verify transactions are ALSO gone (Cascade Delete)
    res_tx = await db_session.execute(select(Transaction).where(Transaction.account_id == acc.id))
    assert len(res_tx.scalars().all()) == 0
