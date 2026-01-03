import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from backend.services.document_processor import process_document_task
from backend.models import Document, User, ProposedChange
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
        
        # Setup Gemini mock for multiple calls
        # 1st call: Extraction
        # 2nd call: Agentic Decision
        mock_client = MagicMock()
        mock_genai_client_class.return_value = mock_client
        
        mock_res_extraction = MagicMock()
        mock_res_extraction.text = mock_gemini_json
        
        mock_res_agent = MagicMock()
        mock_res_agent.text = '{"action": "DECIDE", "decision": "CREATE_NEW", "confidence": 0.9}'
        
        mock_client.models.generate_content.side_effect = [mock_res_extraction, mock_res_agent]
        
        # 3. Run the task
        await process_document_task(doc.id)
        
        # 4. Verifications
        assert mock_pdf_conv.called
        assert mock_client.models.generate_content.called
        
        # Verify status updated
        await db_session.refresh(doc)
        assert doc.status == "PROCESSED"
        
        # Verify proposal created
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()
        assert len(proposals) == 1
        assert proposals[0].proposed_data["amount"] == 100.0
        assert proposals[0].proposed_data["merchant"] == "Test Shop"

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
        mock_genai.return_value.models.generate_content.side_effect = Exception("Gemini Down")
        
        await process_document_task(doc.id)
        
        await db_session.refresh(doc)
        assert doc.status == "ERROR"
