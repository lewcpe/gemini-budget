import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import UploadFile
from backend.routers.documents import upload_document
from backend.models import User, Document

@pytest.mark.asyncio
async def test_upload_document_triggers_background_task():
    # Mock dependencies
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.file = MagicMock()
    
    mock_db = MagicMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = "user123"
    
    mock_background_tasks = MagicMock()
    
    with patch("backend.routers.documents.open", MagicMock()), \
         patch("backend.routers.documents.shutil.copyfileobj", MagicMock()), \
         patch("backend.routers.documents.process_document_task") as mock_task:
        
        # We need to mock the db.add, db.commit, db.refresh
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Run the function
        await upload_document(
            file=mock_file,
            user_note="Test note",
            background_tasks=mock_background_tasks,
            db=mock_db,
            current_user=mock_user
        )
        
        mock_background_tasks.add_task.assert_called_once()
        args, _ = mock_background_tasks.add_task.call_args
        assert args[0] == mock_task
