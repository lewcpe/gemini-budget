import pytest
import os
import shutil
from pathlib import Path
from sqlalchemy.future import select
from backend.models import User, Account, Category, Document, ProposedChange
from backend.services.document_processor import process_document_task
from backend.database import SessionLocal
from backend.config import settings
from unittest.mock import MagicMock, patch

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def mock_session_local(db_session):
    # Mock SessionLocal to return the existing test session provided by conftest
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
async def test_real_world_fixtures(db_session, mock_session_local):
    """
    Test document processing using real-world image fixtures.
    """
    if not settings.GOOGLE_GENAI_KEY:
        pytest.skip("GOOGLE_GENAI_KEY not set")

    # 1. Setup Base Data
    email = "real_world_test@example.com"
    user = User(email=email)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Required: Petty Cash Account (used as fallback by document_processor)
    acc = Account(user_id=user.id, name="Petty Cash Account", type="ASSET", sub_type="CASH")
    
    # Common categories to help LLM matching
    cat1 = Category(user_id=user.id, name="Food & Dining", type="EXPENSE")
    cat2 = Category(user_id=user.id, name="Shopping", type="EXPENSE")
    cat3 = Category(user_id=user.id, name="Subscriptions", type="EXPENSE")
    cat4 = Category(user_id=user.id, name="Travel", type="EXPENSE")
    cat5 = Category(user_id=user.id, name="Salary", type="INCOME")
    cat6 = Category(user_id=user.id, name="Housing", type="EXPENSE")
    cat7 = Category(user_id=user.id, name="Transfers", type="TRANSFER")
    cat8 = Category(user_id=user.id, name="Bank Fees", type="EXPENSE")
    cat9 = Category(user_id=user.id, name="Personal", type="EXPENSE")
    cat10 = Category(user_id=user.id, name="Cash", type="EXPENSE")
    
    db_session.add_all([acc, cat1, cat2, cat3, cat4, cat5, cat6, cat7, cat8, cat9, cat10])
    await db_session.commit()

    # 2. Process each image in fixtures
    fixture_files = list(FIXTURES_DIR.glob("*.jpg")) + list(FIXTURES_DIR.glob("*.pdf"))
    assert len(fixture_files) > 0, "No fixture files found"

    for fixture_path in fixture_files:
        # Create a temporary copy of the fixture to simulate an uploaded file
        # The document_processor expects file_path to exist
        doc = Document(
            user_id=user.id,
            original_filename=fixture_path.name,
            file_path=str(fixture_path), # Use actual path for test
            mime_type="image/jpeg" if fixture_path.suffix == ".jpg" else "application/pdf",
            status="UPLOADED"
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        # 3. Run Process Task
        with patch("backend.services.document_processor.SessionLocal", mock_session_local):
            await process_document_task(doc.id)

        # 4. Verify Results
        await db_session.refresh(doc)
        assert doc.status == "PROCESSED", f"Document {fixture_path.name} failed to process. Check logs."

        # Verify that proposals were created
        res = await db_session.execute(select(ProposedChange).where(ProposedChange.document_id == doc.id))
        proposals = res.scalars().all()
        
        assert len(proposals) > 0, f"No proposals created for {fixture_path.name}"
        
        # Log results for visibility (optional in automated tests, but helpful here)
        print(f"\nProcessed {fixture_path.name}:")
        for p in proposals:
            print(f"  - Change Type: {p.change_type}, Confidence: {p.confidence_score}")
            print(f"    Data: {p.proposed_data}")
