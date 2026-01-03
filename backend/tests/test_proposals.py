import pytest
from httpx import AsyncClient
from datetime import datetime
from backend.models import ProposedChange, Document
from sqlalchemy import select

@pytest.mark.asyncio
async def test_proposal_flow(client: AsyncClient, db_session, auth_headers: dict, sample_account):
    # 1. Setup: Create a document and a proposal manually in DB
    doc = Document(
        user_id="test_user_id", # This might mismatch with auth_headers if not careful
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf"
    )
    # Get the user created by auth_headers (lazy registration)
    res = await client.get("/accounts/", headers=auth_headers)
    user_id = (await db_session.execute(select(Document.user_id))).scalars().first() # This is a hack, let's just use the client to get user if possible, or just seed user too.
    
    # Better: use the client to trigger user creation first
    await client.get("/accounts/", headers=auth_headers)
    from backend.models import User
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    doc = Document(
        user_id=user.id,
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf"
    )
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id,
        document_id=doc.id,
        change_type="CREATE_NEW",
        proposed_data={
            "account_id": sample_account,
            "amount": 100.0,
            "type": "EXPENSE",
            "transaction_date": "2026-01-01T10:00:00",
            "merchant": "Electric Co"
        },
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # 2. List proposals
    list_res = await client.get("/proposals/", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    
    # 3. Confirm proposal
    proposal_id = list_res.json()[0]["id"]
    conf_res = await client.post(
        f"/proposals/{proposal_id}/confirm",
        json={"status": "APPROVED"},
        headers=auth_headers
    )
    assert conf_res.status_code == 200
    assert conf_res.json()["status"] == "approved"
    
    # 4. Verify transaction created
    tx_res = await client.get("/transactions/", headers=auth_headers)
    assert any(tx["amount"] == 100.0 for tx in tx_res.json())

@pytest.mark.asyncio
async def test_proposal_rejection(client: AsyncClient, db_session, auth_headers: dict, sample_account):
    # Setup
    res = await client.get("/accounts/", headers=auth_headers)
    from backend.models import User, Document
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    doc = Document(user_id=user.id, original_filename="test.pdf", file_path="/tmp/test.pdf", mime_type="application/pdf")
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id, document_id=doc.id, change_type="CREATE_NEW",
        proposed_data={"account_id": sample_account, "amount": 50.0, "type": "EXPENSE", "transaction_date": "2026-01-01T10:00:00"},
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # Reject
    res = await client.post(f"/proposals/{proposal.id}/confirm", json={"status": "REJECTED"}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "rejected"
    
    # Verify status in DB
    await db_session.refresh(proposal)
    assert proposal.status == "REJECTED"

@pytest.mark.asyncio
async def test_proposal_approve_with_edit(client: AsyncClient, db_session, auth_headers: dict, sample_account):
    # Setup
    await client.get("/accounts/", headers=auth_headers)
    from backend.models import User, Document
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    doc = Document(user_id=user.id, original_filename="test.pdf", file_path="/tmp/test.pdf", mime_type="application/pdf")
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id, document_id=doc.id, change_type="CREATE_NEW",
        proposed_data={"account_id": sample_account, "amount": 10.0, "type": "EXPENSE", "transaction_date": "2026-01-01"},
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # Approve with edit
    res = await client.post(
        f"/proposals/{proposal.id}/confirm",
        json={"status": "APPROVED", "edited_data": {"amount": 99.99, "account_id": sample_account}},
        headers=auth_headers
    )
    assert res.status_code == 200
    
    # Verify transaction has EDITED amount
    tx_res = await client.get("/transactions/", headers=auth_headers)
    assert any(tx["amount"] == 99.99 for tx in tx_res.json())

@pytest.mark.asyncio
async def test_proposal_update_existing(client: AsyncClient, db_session, auth_headers: dict, sample_account, sample_category):
    # Setup: Create a transaction first
    await client.get("/accounts/", headers=auth_headers)
    from backend.models import User, Document, Transaction
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    tx = Transaction(user_id=user.id, account_id=sample_account, category_id=sample_category, amount=10.0, type="EXPENSE", transaction_date=datetime.now())
    db_session.add(tx)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="test.pdf", file_path="/tmp/test.pdf", mime_type="application/pdf")
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id, document_id=doc.id, change_type="UPDATE_EXISTING",
        target_transaction_id=tx.id,
        proposed_data={"amount": 20.0},
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # Confirm
    res = await client.post(f"/proposals/{proposal.id}/confirm", json={"status": "APPROVED"}, headers=auth_headers)
    assert res.status_code == 200
    
    # Verify original TX updated
    await db_session.refresh(tx)
    assert tx.amount == 20.0

@pytest.mark.asyncio
async def test_proposal_create_account_and_transaction(client: AsyncClient, db_session, auth_headers: dict):
    # Setup
    await client.get("/accounts/", headers=auth_headers)
    from backend.models import User, Document, Account, Transaction
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    doc = Document(user_id=user.id, original_filename="test.pdf", file_path="/tmp/test.pdf", mime_type="application/pdf")
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id, document_id=doc.id, change_type="CREATE_ACCOUNT",
        proposed_data={
            "_new_account": {
                "name": "Bonus Card",
                "type": "LIABILITY",
                "sub_type": "CREDIT_CARD",
                "description": "Acc No: 1234, Branch: Test"
            },
            "transactions": [
                {
                    "amount": 150.0,
                    "merchant": "New Store",
                    "type": "EXPENSE",
                    "transaction_date": "2026-01-02"
                }
            ]
        },
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # Confirm
    res = await client.post(f"/proposals/{proposal.id}/confirm", json={"status": "APPROVED"}, headers=auth_headers)
    assert res.status_code == 200
    
    # Verify account created
    acc_res = await db_session.execute(select(Account).where(Account.name == "Bonus Card"))
    account = acc_res.scalars().first()
    assert account is not None
    assert account.type == "LIABILITY"
    assert account.description == "Acc No: 1234, Branch: Test"
    
    # Verify transaction created for that account
    tx_res = await db_session.execute(select(Transaction).where(Transaction.account_id == account.id))
    tx = tx_res.scalars().first()
    assert tx is not None
    assert tx.amount == 150.0
    assert tx.merchant == "New Store"

@pytest.mark.asyncio
async def test_proposal_create_batch(client: AsyncClient, db_session, auth_headers: dict):
    # Setup
    await client.get("/accounts/", headers=auth_headers)
    from backend.models import User, Document, Account, Transaction
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    doc = Document(user_id=user.id, original_filename="batch.pdf", file_path="/tmp/batch.pdf", mime_type="application/pdf")
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id, document_id=doc.id, change_type="CREATE_ACCOUNT",
        proposed_data={
            "_new_account": {
                "name": "Batch Savings",
                "type": "ASSET",
                "sub_type": "CASH",
                "description": "Batch creation test"
            },
            "transactions": [
                {"amount": 100.0, "merchant": "Shop A", "type": "EXPENSE", "transaction_date": "2026-01-01"},
                {"amount": 200.0, "merchant": "Shop B", "type": "EXPENSE", "transaction_date": "2026-01-02"}
            ]
        },
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # Confirm
    res = await client.post(f"/proposals/{proposal.id}/confirm", json={"status": "APPROVED"}, headers=auth_headers)
    assert res.status_code == 200
    
    # Verify account created
    acc_res = await db_session.execute(select(Account).where(Account.name == "Batch Savings"))
    account = acc_res.scalars().first()
    assert account is not None
    
    # Verify transactions created
    tx_res = await db_session.execute(select(Transaction).where(Transaction.account_id == account.id))
    transactions = tx_res.scalars().all()
    assert len(transactions) == 2
    assert any(t.amount == 100.0 for t in transactions)
    assert any(t.amount == 200.0 for t in transactions)

@pytest.mark.asyncio
async def test_proposal_create_account_override(client: AsyncClient, db_session, auth_headers: dict, sample_account):
    # Setup
    await client.get("/accounts/", headers=auth_headers)
    from backend.models import User, Document, Account, Transaction
    user = (await db_session.execute(select(User).where(User.email == "test@example.com"))).scalars().first()
    
    doc = Document(user_id=user.id, original_filename="override.pdf", file_path="/tmp/override.pdf", mime_type="application/pdf")
    db_session.add(doc)
    await db_session.flush()
    
    proposal = ProposedChange(
        user_id=user.id, document_id=doc.id, change_type="CREATE_ACCOUNT",
        proposed_data={
            "_new_account": {"name": "Should not be created"},
            "transactions": [
                {"amount": 500.0, "merchant": "Big Purchase", "type": "EXPENSE", "transaction_date": "2026-01-05"}
            ]
        },
        status="PENDING"
    )
    db_session.add(proposal)
    await db_session.commit()
    
    # Confirm with OVERRIDE account_id
    res = await client.post(
        f"/proposals/{proposal.id}/confirm", 
        json={
            "status": "APPROVED",
            "edited_data": {"account_id": sample_account}
        }, 
        headers=auth_headers
    )
    assert res.status_code == 200
    
    # Verify NO new account was created with that name
    acc_res = await db_session.execute(select(Account).where(Account.name == "Should not be created"))
    assert acc_res.scalars().first() is None
    
    # Verify transaction linked to sample_account
    tx_res = await db_session.execute(select(Transaction).where(Transaction.account_id == sample_account))
    txs = tx_res.scalars().all()
    assert any(t.amount == 500.0 for t in txs)

@pytest.mark.asyncio
async def test_proposal_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.post("/proposals/non-existent-id/confirm", json={"status": "APPROVED"}, headers=auth_headers)
    assert res.status_code == 404
