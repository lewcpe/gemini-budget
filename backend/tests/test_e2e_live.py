import pytest
import os
import io
import asyncio
import tempfile
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
from unittest.mock import MagicMock, patch
from sqlalchemy.future import select
from backend.services.document_processor import process_document_task
from backend.models import User, Account, Category, Transaction, Document, ProposedChange

# Helper to create images
def create_text_image(text):
    # Create a white image
    img = Image.new('RGB', (800, 1000), color='white')
    d = ImageDraw.Draw(img)

    # Draw text.
    # Note: Default font is small. We rely on Gemini's vision capabilities which are generally good with small text.
    # To be safe, we can try to position it well.
    y = 20
    for line in text.split('\n'):
        d.text((20, y), line, fill="black")
        y += 15 # Simple line height

    # Save to bytes
    b = io.BytesIO()
    img.save(b, format="JPEG")
    return b.getvalue()

@pytest.fixture
def mock_session_local(db_session):
    # Mock SessionLocal to return the existing test session provided by conftest
    # SessionLocal() is called as a context manager: async with SessionLocal() as db:
    mock_cm = MagicMock()

    async def aenter(self):
        return db_session

    async def aexit(self, exc_type, exc_val, exc_tb):
        pass

    mock_cm.__aenter__ = aenter
    mock_cm.__aexit__ = aexit

    mock_factory = MagicMock(return_value=mock_cm)
    return mock_factory

@pytest.mark.asyncio
async def test_receipt_matching(db_session, mock_session_local):
    """
    Test Case 1: Receipt Matching
    - Scenario: User uploads a receipt for a transaction that already exists.
    - Expected: LLM identifies it as a match (UPDATE_EXISTING).
    """
    if not os.environ.get("GOOGLE_GENAI_KEY"):
        pytest.skip("GOOGLE_GENAI_KEY not set")

    # 1. Setup Data
    email = f"receipt_{os.urandom(4).hex()}@example.com"
    user = User(email=email)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    acc = Account(user_id=user.id, name="Cash Wallet", type="ASSET", sub_type="CASH")
    cat = Category(user_id=user.id, name="Dining", type="EXPENSE")
    db_session.add_all([acc, cat])
    await db_session.commit()

    yesterday = datetime.now() - timedelta(days=1)
    date_str = yesterday.strftime('%Y-%m-%d')

    tx = Transaction(
        user_id=user.id,
        account_id=acc.id,
        category_id=cat.id,
        amount=12.50,
        merchant="Joe's Coffee",
        transaction_date=yesterday,
        type="EXPENSE"
    )
    db_session.add(tx)
    await db_session.commit()

    # 2. Create Receipt Image
    text = f"""
    RECEIPT
    Joe's Coffee Shop
    123 Main St

    Date: {date_str}

    Latte       $4.50
    Sandwich    $8.00
    ----------------
    TOTAL      $12.50

    Paid by Cash
    Thank you!
    """
    img_data = create_text_image(text)

    # 3. Create Document Record
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(img_data)
        tmp_path = tmp.name

    try:
        doc = Document(
            user_id=user.id,
            original_filename="receipt.jpg",
            file_path=tmp_path,
            mime_type="image/jpeg",
            status="UPLOADED"
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        # 4. Run Process Task
        with patch("backend.services.document_processor.SessionLocal", mock_session_local):
            await process_document_task(doc.id)

        # 5. Verify Results
        await db_session.refresh(doc)
        assert doc.status == "PROCESSED", "Document status should be PROCESSED"

        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()

        assert len(proposals) > 0, "Should have at least one proposal"
        # We expect one proposal to update the existing transaction
        match_proposal = next((p for p in proposals if p.change_type == "UPDATE_EXISTING"), None)
        assert match_proposal is not None, "Should find UPDATE_EXISTING proposal"
        assert match_proposal.target_transaction_id == tx.id

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.asyncio
async def test_new_account_creation_from_statement(db_session, mock_session_local):
    """
    Test Case 2: New Account Creation
    - Scenario: Upload a Bank Statement for an unknown account.
    - Expected: LLM suggests CREATE_ACCOUNT for the new bank account.
    """
    if not os.environ.get("GOOGLE_GENAI_KEY"):
        pytest.skip("GOOGLE_GENAI_KEY not set")

    # 1. Setup Data
    email = f"bank_{os.urandom(4).hex()}@example.com"
    user = User(email=email)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Existing category just to help LLM
    cat = Category(user_id=user.id, name="Salary", type="INCOME")
    db_session.add(cat)
    await db_session.commit()

    # 2. Create Bank Statement Image
    # A statement usually has the bank name and account number clearly.
    text = """
    GOLDMAN SACHS BANK
    Account Statement
    Account Number: 987654321
    Period: Oct 1 - Oct 31, 2023

    Date        Description         Debit       Credit      Balance
    ----------------------------------------------------------------
    2023-10-01  Opening Balance                             $1000.00
    2023-10-15  Tech Corp Salary                $5000.00    $6000.00
    """
    img_data = create_text_image(text)

    # 3. Create Document
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(img_data)
        tmp_path = tmp.name

    try:
        doc = Document(
            user_id=user.id,
            original_filename="statement.jpg",
            file_path=tmp_path,
            mime_type="image/jpeg",
            status="UPLOADED"
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        # 4. Run Process Task
        with patch("backend.services.document_processor.SessionLocal", mock_session_local):
            await process_document_task(doc.id)

        # 5. Verify Results
        await db_session.refresh(doc)
        assert doc.status == "PROCESSED"

        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()

        # Look for CREATE_ACCOUNT
        acc_proposal = next((p for p in proposals if p.change_type == "CREATE_ACCOUNT"), None)
        assert acc_proposal is not None, "Should propose CREATE_ACCOUNT"

        data = acc_proposal.proposed_data
        new_acc = data.get("_new_account", {})
        assert "Goldman" in new_acc.get("name", "") or "Bank" in new_acc.get("name", "")
        assert new_acc.get("type") == "ASSET"

        txs = data.get("transactions", [])
        assert len(txs) >= 1
        assert any(t["merchant"] == "Tech Corp Salary" or "Tech Corp" in t["merchant"] for t in txs)

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@pytest.mark.asyncio
async def test_credit_card_statement_import(db_session, mock_session_local):
    """
    Test Case 3: Credit Card Statement Import
    - Scenario: Upload a CC Statement for an EXISTING account.
    - Expected: LLM suggests CREATE_NEW for the transactions, linked to the existing account.
    """
    if not os.environ.get("GOOGLE_GENAI_KEY"):
        pytest.skip("GOOGLE_GENAI_KEY not set")

    # 1. Setup Data
    email = f"cc_{os.urandom(4).hex()}@example.com"
    user = User(email=email)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create the account beforehand
    acc = Account(user_id=user.id, name="Chase Sapphire", type="LIABILITY", sub_type="CREDIT_CARD")
    cat1 = Category(user_id=user.id, name="Entertainment", type="EXPENSE")
    cat2 = Category(user_id=user.id, name="Transport", type="EXPENSE")
    db_session.add_all([acc, cat1, cat2])
    await db_session.commit()

    # 2. Create CC Statement Image
    text = """
    CHASE SAPPHIRE PREFERRED
    Statement Ending Dec 01, 2023

    Transactions:
    Nov 05     NETFLIX.COM         $19.99
    Nov 07     UBER TRIP           $25.50
    Nov 10     AMAZON MKTPLC       $45.00
    """
    img_data = create_text_image(text)

    # 3. Create Document
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(img_data)
        tmp_path = tmp.name

    try:
        doc = Document(
            user_id=user.id,
            original_filename="cc_stmt.jpg",
            file_path=tmp_path,
            mime_type="image/jpeg",
            status="UPLOADED"
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        # 4. Run Process Task
        with patch("backend.services.document_processor.SessionLocal", mock_session_local):
            await process_document_task(doc.id)

        # 5. Verify Results
        await db_session.refresh(doc)
        assert doc.status == "PROCESSED"

        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()

        # We expect CREATE_NEW proposals
        new_tx_proposals = [p for p in proposals if p.change_type == "CREATE_NEW"]
        assert len(new_tx_proposals) >= 3

        # Check that they are linked to the correct account
        # Note: The LLM might map "Chase Sapphire" string in doc to the account "Chase Sapphire" in context.
        # This relies on the agentic logic in `get_agent_context` returning the account.

        for p in new_tx_proposals:
            assert p.proposed_data.get("account_id") == acc.id, f"Should match to account {acc.name}"

            # Optional: Check categories
            m = p.proposed_data.get("merchant", "").upper()
            if "NETFLIX" in m:
                assert p.proposed_data.get("category_id") == cat1.id
            if "UBER" in m:
                assert p.proposed_data.get("category_id") == cat2.id

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
