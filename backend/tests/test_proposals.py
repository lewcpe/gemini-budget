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
