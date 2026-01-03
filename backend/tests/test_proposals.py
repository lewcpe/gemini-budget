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
async def test_proposal_not_found(client: AsyncClient, auth_headers: dict):
    res = await client.post("/proposals/non-existent-id/confirm", json={"status": "APPROVED"}, headers=auth_headers)
    assert res.status_code == 404
