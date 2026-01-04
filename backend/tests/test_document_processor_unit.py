import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import json
from backend.services.document_processor import process_document_task
from backend.models import Document, User, ProposedChange, Account, Category, Merchant
from sqlalchemy import select

@pytest.mark.asyncio
async def test_process_document_task_pdf(db_session, auth_headers):
    # 1. Setup mock user and document
    await db_session.execute(select(User)) # Ensure user created if lazy registration used elsewhere
    user = User(email="test@example.com", full_name="Test User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(
        user_id=user.id,
        original_filename="test.pdf",
        file_path="/tmp/test.pdf",
        mime_type="application/pdf",
        status="PENDING"
    )
    db_session.add(doc)
    
    # Create Petty Cash Account (normally created by dependencies.py)
    petty_cash = Account(user_id=user.id, name="Petty Cash Account", type="ASSET")
    db_session.add(petty_cash)
    
    await db_session.commit()
    await db_session.refresh(doc)

    # 2. Mocks
    mock_images = [MagicMock(), MagicMock()]
    mock_images[0].save = MagicMock()
    mock_images[1].save = MagicMock()
    
    # Mock return text from Gemini
    mock_gemini_json = '[{"amount": 100.0, "merchant": "Test Shop", "transaction_date": "2026-01-01", "type": "EXPENSE"}]'
    
    with patch("backend.services.document_processor.convert_from_path", return_value=mock_images) as mock_pdf_conv, \
         patch("backend.services.document_processor.PIL.Image.open", return_value=mock_images[0]) as mock_img_open, \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        # Setup SessionLocal mock to return our db_session
        mock_session_local.return_value.__aenter__.return_value = db_session
        
        # Setup Gemini mock for integrated agentic loop
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        mock_res = MagicMock()
        mock_res.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 100.0, "merchant": "Test Shop", "transaction_date": "2026-01-01", "type": "EXPENSE"},
                    "confidence": 0.9
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_res)
        
        # 3. Run the task
        await process_document_task(doc.id)
        
        # 4. Verifications
        assert mock_pdf_conv.called
        assert mock_client.aio.models.generate_content.called
        
        # Verify status updated
        await db_session.refresh(doc)
        assert doc.status == "PROCESSED"
        
        # Verify proposal created
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()
        assert len(proposals) == 1
        assert proposals[0].proposed_data["amount"] == 100.0
        assert proposals[0].proposed_data["merchant"] == "Test Shop"
        # Verify Petty Cash Account was assigned
        assert "account_id" in proposals[0].proposed_data
        
        # Verify account was created
        acc_res = await db_session.execute(select(Account).where(Account.id == proposals[0].proposed_data["account_id"]))
        acc = acc_res.scalar()
        assert acc.name == "Petty Cash Account"

@pytest.mark.asyncio
async def test_process_document_task_unsupported_mime(db_session):
    doc = Document(
        user_id="any",
        original_filename="test.txt",
        file_path="/tmp/test.txt",
        mime_type="text/plain",
        status="PENDING"
    )
    db_session.add(doc)
    await db_session.commit()

    with patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        mock_session_local.return_value.__aenter__.return_value = db_session
        await process_document_task(doc.id)
        
        await db_session.refresh(doc)
        assert doc.status == "ERROR"

@pytest.mark.asyncio
async def test_process_document_task_gemini_error(db_session):
    user = User(email="error@example.com", full_name="Error User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(
        user_id=user.id,
        original_filename="test.jpg",
        file_path="/tmp/test.jpg",
        mime_type="image/jpeg",
        status="PENDING"
    )
    db_session.add(doc)
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_genai.return_value.aio.models.generate_content = AsyncMock(side_effect=Exception("Gemini Down"))
        
        await process_document_task(doc.id)
        
        await db_session.refresh(doc)
        assert doc.status == "ERROR"

@pytest.mark.asyncio
async def test_process_document_task_batch(db_session, auth_headers):
    # Setup
    user = User(email="batch@example.com", full_name="Batch User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="batch.jpg", file_path="/tmp/batch.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    
    # Create Petty Cash Account
    petty_cash = Account(user_id=user.id, name="Petty Cash Account", type="ASSET")
    db_session.add(petty_cash)
    
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # Call: Agentic Decision (1 account proposal with batch)
        mock_res_agent = MagicMock()
        mock_res_agent.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_ACCOUNT",
                    "new_account_data": {"name": "Batch Card", "type": "LIABILITY"},
                    "transactions": [
                        {"amount": 10.0, "merchant": "A", "transaction_date": "2026-01-01", "type": "EXPENSE"},
                        {"amount": 20.0, "merchant": "B", "transaction_date": "2026-01-01", "type": "EXPENSE"}
                    ],
                    "confidence": 0.95
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_res_agent)
        
        await process_document_task(doc.id)
        
        # Verify proposal
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()
        assert len(proposals) == 1
        assert proposals[0].change_type == "CREATE_ACCOUNT"
        assert len(proposals[0].proposed_data["transactions"]) == 2
        assert proposals[0].proposed_data["_new_account"]["name"] == "Batch Card"

@pytest.mark.asyncio
async def test_petty_cash_account_reuse(db_session):
    # Setup user and an existing Petty Cash Account
    user = User(email="reuse@example.com", full_name="Reuse User")
    db_session.add(user)
    await db_session.flush()
    
    petty_cash = Account(user_id=user.id, name="Petty Cash Account", type="ASSET")
    db_session.add(petty_cash)
    await db_session.commit()
    
    doc = Document(user_id=user.id, original_filename="test.jpg", file_path="/tmp/test.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    await db_session.commit()
    
    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # Mock return from Gemini (DECIDE with CREATE_NEW but NO account_id)
        mock_res_agent = MagicMock()
        mock_res_agent.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Small Shop", "type": "EXPENSE"},
                    "confidence": 0.9
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_res_agent)
        
        await process_document_task(doc.id)
        
        # Verify it used the EXISTING petty cash account ID
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposal = res.scalars().first()
        assert proposal.proposed_data["account_id"] == petty_cash.id

@pytest.mark.asyncio
async def test_category_suggestion_via_merchant(db_session):
    # Setup user, account, category, and merchant
    user = User(email="cat@example.com", full_name="Cat User")
    db_session.add(user)
    await db_session.flush()
    
    acc = Account(user_id=user.id, name="Checking", type="ASSET")
    db_session.add(acc)
    
    cat = Category(user_id=user.id, name="Groceries", type="EXPENSE")
    db_session.add(cat)
    await db_session.flush()
    
    merchant = Merchant(user_id=user.id, name="SuperMart", default_category_id=cat.id)
    db_session.add(merchant)
    await db_session.commit()
    
    doc = Document(user_id=user.id, original_filename="test.jpg", file_path="/tmp/test.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    await db_session.commit()
    
    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # Mock Gemini to return "SuperMart" but NO category_id
        mock_res_agent = MagicMock()
        mock_res_agent.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 55.0, "merchant": "SuperMart", "type": "EXPENSE", "account_id": acc.id},
                    "confidence": 0.9
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_res_agent)
        
        await process_document_task(doc.id)
        
        # Verify it suggested the "Groceries" category_id
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposal = res.scalars().first()
        assert proposal.proposed_data["category_id"] == cat.id

@pytest.mark.asyncio
async def test_process_document_task_suggest_account(db_session, auth_headers):
    # Setup
    user = User(email="suggest_acc@example.com", full_name="Suggest Acc User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="statement.jpg", file_path="/tmp/statement.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # Mock Gemini Decision
        mock_res_agent = MagicMock()
        mock_res_agent.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_ACCOUNT",
                    "new_account_data": {"name": "New Salary Account", "type": "ASSET"},
                    "transactions": [
                        {"amount": 1200.0, "merchant": "Employer", "transaction_date": "2026-01-01", "type": "INCOME"}
                    ],
                    "confidence": 0.98
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_res_agent)
        
        await process_document_task(doc.id)
        
        # Verify proposal
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()
        assert len(proposals) == 1
        assert proposals[0].change_type == "CREATE_ACCOUNT"
        assert proposals[0].proposed_data["_new_account"]["name"] == "New Salary Account"

@pytest.mark.asyncio
async def test_process_document_task_agentic_retry_invalid_type(db_session):
    # Setup
    user = User(email="retry_val@example.com", full_name="Retry Val User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="test.jpg", file_path="/tmp/test.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # 1. Invalid DECIDE (type=BANK)
        mock_res_invalid = MagicMock()
        mock_res_invalid.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_ACCOUNT",
                    "new_account_data": {"name": "Bad Account", "type": "BANK"},
                    "transactions": [{"amount": 10.0, "merchant": "Test", "transaction_date": "2026-01-01", "type": "EXPENSE"}],
                    "confidence": 0.9
                }
            ]
        })
        
        # 2. Corrected DECIDE (type=ASSET)
        mock_res_correct = MagicMock()
        mock_res_correct.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_ACCOUNT",
                    "new_account_data": {"name": "Bad Account", "type": "ASSET", "sub_type": "BANK"},
                    "transactions": [{"amount": 10.0, "merchant": "Test", "transaction_date": "2026-01-01", "type": "EXPENSE"}],
                    "confidence": 0.95
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_res_invalid, mock_res_correct])
        
        await process_document_task(doc.id)
        
        # Verify result
        assert mock_client.aio.models.generate_content.call_count == 2
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposal = res.scalars().first()
        assert proposal.proposed_data["_new_account"]["type"] == "ASSET"
        assert proposal.proposed_data["_new_account"]["name"] == "Bad Account"

@pytest.mark.asyncio
async def test_process_document_task_hallucinated_account_id(db_session):
    # Setup
    user = User(email="halluc_acc@example.com", full_name="Halluc Acc User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="test.jpg", file_path="/tmp/test.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    
    # Needs Petty Cash for fallback
    petty_acc = Account(user_id=user.id, name="Petty Cash Account", type="ASSET")
    db_session.add(petty_acc)
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # 1. AI returns a non-existent account_id
        mock_res_halluc = MagicMock()
        mock_res_halluc.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Shop", "account_id": "non_existent_id", "type": "EXPENSE"},
                    "confidence": 0.9
                }
            ]
        })
        
        # 2. Corrected follow-up (using Petty Cash)
        mock_res_correct = MagicMock()
        mock_res_correct.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Shop", "type": "EXPENSE"},
                    "confidence": 0.95
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_res_halluc, mock_res_correct])
        
        await process_document_task(doc.id)
        
        # Verify result
        assert mock_client.aio.models.generate_content.call_count == 2
        res = await db_session.execute(select(Account).where(Account.user_id == user.id, Account.name == "Petty Cash Account"))
        petty_acc = res.scalars().first()
        
        res_p = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposal = res_p.scalars().first()
        assert proposal.proposed_data["account_id"] == petty_acc.id

@pytest.mark.asyncio
async def test_process_document_task_hallucinated_category_id(db_session):
    # Setup
    user = User(email="halluc_cat@example.com", full_name="Halluc Cat User")
    db_session.add(user)
    await db_session.flush()
    
    acc = Account(user_id=user.id, name="Checking", type="ASSET")
    db_session.add(acc)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="test.jpg", file_path="/tmp/test.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    
    # Petty Cash fallback
    petty_acc = Account(user_id=user.id, name="Petty Cash Account", type="ASSET")
    db_session.add(petty_acc)
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # 1. AI returns a non-existent category_id
        mock_res_halluc = MagicMock()
        mock_res_halluc.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Shop", "account_id": acc.id, "category_id": "non_existent_cat", "type": "EXPENSE"},
                    "confidence": 0.9
                }
            ]
        })
        
        # 2. Corrected follow-up (no category)
        mock_res_correct = MagicMock()
        mock_res_correct.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Shop", "account_id": acc.id, "type": "EXPENSE"},
                    "confidence": 0.95
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_res_halluc, mock_res_correct])
        
        await process_document_task(doc.id)
        
        # Verify result
        assert mock_client.aio.models.generate_content.call_count == 2
        res_p = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposal = res_p.scalars().first()
        assert proposal.proposed_data.get("category_id") is None

@pytest.mark.asyncio
async def test_process_document_task_invalid_types_fallback(db_session):
    # Setup
    user = User(email="bad_types@example.com", full_name="Bad Types User")
    db_session.add(user)
    await db_session.flush()
    
    doc = Document(user_id=user.id, original_filename="test.jpg", file_path="/tmp/test.jpg", mime_type="image/jpeg")
    db_session.add(doc)
    
    # Ensure Petty Cash exists for fallback
    petty_acc = Account(user_id=user.id, name="Petty Cash Account", type="ASSET")
    db_session.add(petty_acc)
    await db_session.commit()

    with patch("backend.services.document_processor.PIL.Image.open", return_value=MagicMock()), \
         patch("backend.services.document_processor.genai.Client") as mock_genai_client_class, \
         patch("backend.services.document_processor.SessionLocal") as mock_session_local:
        
        mock_session_local.return_value.__aenter__.return_value = db_session
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        # 1. AI returns invalid transaction type 'CREDIT'
        mock_res_halluc = MagicMock()
        mock_res_halluc.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Shop", "type": "CREDIT"},
                    "confidence": 0.9
                }
            ]
        })
        
        # 2. Corrected follow-up 'INCOME'
        mock_res_correct = MagicMock()
        mock_res_correct.text = json.dumps({
            "action": "DECIDE",
            "proposals": [
                {
                    "type": "CREATE_NEW",
                    "data": {"amount": 50.0, "merchant": "Shop", "type": "INCOME"},
                    "confidence": 0.95
                }
            ]
        })
        
        mock_client.aio.models.generate_content = AsyncMock(side_effect=[mock_res_halluc, mock_res_correct])
        
        await process_document_task(doc.id)
        
        # Verify result
        assert mock_client.aio.models.generate_content.call_count == 2
        res_p = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposal = res_p.scalars().first()
        assert proposal.proposed_data["type"] == "INCOME"

