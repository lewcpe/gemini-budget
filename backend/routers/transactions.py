from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..models import Transaction, User, Document
from ..schemas import TransactionCreate, TransactionUpdate, Transaction as TransactionSchema, Document as DocumentSchema
from ..dependencies import get_current_user

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/", response_model=List[TransactionSchema])
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Transaction).where(Transaction.user_id == current_user.id))
    return result.scalars().all()

@router.post("/", response_model=TransactionSchema)
async def create_transaction(
    transaction: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_transaction = Transaction(**transaction.model_dump(), user_id=current_user.id)
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

@router.patch("/{transaction_id}", response_model=TransactionSchema)
async def update_transaction(
    transaction_id: str,
    transaction_update: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
    )
    db_transaction = result.scalars().first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    update_data = transaction_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
    )
    db_transaction = result.scalars().first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    await db.delete(db_transaction)
    await db.commit()
    return None

@router.get("/{transaction_id}/documents", response_model=List[DocumentSchema])
async def list_transaction_documents(
    transaction_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This endpoint shows documents which origin of a particular transaction.
    # one transaction could be originated from multiple documents.
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
    )
    db_transaction = result.scalars().first()
    if not db_transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Need to load the documents relationship
    # In a real app we might use selectinload, but for simplicity we access it here
    # Since it's async, we need to be careful. Let's use a query to avoid lazy loading issues.
    # Actually, SQLAlchemy 2.0 with async requires explicit loading or separate queries.
    
    doc_result = await db.execute(
        select(Document).join(Transaction.documents).where(Transaction.id == transaction_id)
    )
    return doc_result.scalars().all()
