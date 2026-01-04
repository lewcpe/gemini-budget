from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
from ..database import get_db
from ..models import Transaction, User, Document
from ..schemas import TransactionCreate, TransactionUpdate, Transaction as TransactionSchema, Document as DocumentSchema
from ..dependencies import get_current_user, PaginationParams
from ..services.account_service import recalculate_account_balance

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/", response_model=List[TransactionSchema])
async def list_transactions(
    q: Optional[str] = Query(None, description="Search merchant or note"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Transaction).where(Transaction.user_id == current_user.id)
    
    if q:
        search_filter = or_(
            Transaction.merchant.ilike(f"%{q}%"),
            Transaction.note.ilike(f"%{q}%")
        )
        query = query.where(search_filter)
    
    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)
    
    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)
    
    # Order by date descending by default
    query = query.order_by(Transaction.transaction_date.desc())
    
    query = query.offset(pagination.skip).limit(pagination.limit)
    
    result = await db.execute(query)
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
    
    # Update balance
    await recalculate_account_balance(db, db_transaction.account_id)
    if db_transaction.target_account_id:
        await recalculate_account_balance(db, db_transaction.target_account_id)
    await db.commit()

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
    old_account_id = db_transaction.account_id
    old_target_account_id = db_transaction.target_account_id
    
    for key, value in update_data.items():
        setattr(db_transaction, key, value)
    
    await db.commit()
    await db.refresh(db_transaction)
    
    # Update balances for all affected accounts
    affected_accounts = {old_account_id, db_transaction.account_id}
    if old_target_account_id:
        affected_accounts.add(old_target_account_id)
    if db_transaction.target_account_id:
        affected_accounts.add(db_transaction.target_account_id)
        
    for acc_id in affected_accounts:
        if acc_id:
            await recalculate_account_balance(db, acc_id)
    
    await db.commit()
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
        
    account_id = db_transaction.account_id
    target_account_id = db_transaction.target_account_id
    
    await db.delete(db_transaction)
    await db.commit()
    
    # Update balances
    await recalculate_account_balance(db, account_id)
    if target_account_id:
        await recalculate_account_balance(db, target_account_id)
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
