import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..database import get_db
from ..models import Document, User
from ..schemas import Document as DocumentSchema
from ..dependencies import get_current_user, PaginationParams
from ..config import settings

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=DocumentSchema)
async def upload_document(
    file: UploadFile = File(...),
    user_note: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    file_id = str(uuid.uuid4())
    filename = file.filename or ""
    extension = filename.split(".")[-1] if "." in filename else ""
    safe_filename = f"{file_id}.{extension}" if extension else file_id
    file_path = settings.UPLOAD_DIR / safe_filename
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    db_document = Document(
        id=file_id,
        user_id=current_user.id,
        original_filename=file.filename,
        file_path=str(file_path),
        mime_type=file.content_type,
        user_note=user_note,
        status="UPLOADED"
    )
    
    db.add(db_document)
    await db.commit()
    await db.refresh(db_document)
    return db_document

@router.get("/", response_model=List[DocumentSchema])
async def list_documents(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Document).where(Document.user_id == current_user.id).offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.user_id == current_user.id)
    )
    db_document = result.scalars().first()
    if not db_document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # In a real app we might also delete the file from disk
    # path = Path(db_document.file_path)
    # if path.exists(): path.unlink()
    
    await db.delete(db_document)
    await db.commit()
    return None
