from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timezone
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..models import ProposedChange, Transaction, User, Account, Category, Document
from ..schemas import ProposedChange as ProposedChangeSchema, ProposedChangeConfirm
from ..dependencies import get_current_user, PaginationParams

router = APIRouter(prefix="/proposals", tags=["proposals"])

@router.get("/", response_model=List[ProposedChangeSchema])
async def list_proposals(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = (
        select(ProposedChange)
        .where(ProposedChange.user_id == current_user.id, ProposedChange.status == "PENDING")
        .offset(pagination.skip)
        .limit(pagination.limit)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/{proposal_id}/confirm")
async def confirm_proposal(
    proposal_id: str,
    action: ProposedChangeConfirm,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ProposedChange).where(ProposedChange.id == proposal_id, ProposedChange.user_id == current_user.id)
    )
    db_proposal = result.scalars().first()
    if not db_proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if action.status == "REJECTED":
        db_proposal.status = "REJECTED"
        await db.commit()
        return {"status": "rejected"}
    
    if action.status == "APPROVED":
        # Data to use (either edited or original)
        data = db_proposal.proposed_data.copy()
        if action.edited_data:
            data.update(action.edited_data)
        
        if db_proposal.change_type == "CREATE_NEW":
            new_tx = await _create_transaction_from_data(data, current_user.id, proposal_id, db)
            db.add(new_tx)

        elif db_proposal.change_type == "CREATE_ACCOUNT":
            # Handle one or more transactions, with optional new account creation
            acc_id = data.get("account_id") # Check for override in edited_data
            
            # 1. Create Account if NO account_id provided (meaning user accepts the proposal as is)
            if not acc_id and "_new_account" in data:
                acc_data = data["_new_account"]
                new_acc = Account(
                    user_id=current_user.id,
                    name=acc_data.get("name"),
                    type=acc_data.get("type", "ASSET"),
                    sub_type=acc_data.get("sub_type"),
                    currency=acc_data.get("currency", "USD"),
                    description=acc_data.get("description")
                )
                db.add(new_acc)
                await db.flush()
                acc_id = new_acc.id
            
            if not acc_id:
                raise HTTPException(status_code=400, detail="Missing target account or account metadata")
            
            # 2. Create transactions
            transactions = data.get("transactions")
            if not transactions:
                # If AI returned it as a single data object instead of a list (fallback)
                transactions = [data]
            
            for tx_item in transactions:
                # Ensure the transaction uses the decided account_id
                tx_item["account_id"] = acc_id
                new_tx = await _create_transaction_from_data(tx_item, current_user.id, proposal_id, db)
                db.add(new_tx)

        elif db_proposal.change_type == "UPDATE_EXISTING":
            if not db_proposal.target_transaction_id:
                raise HTTPException(status_code=400, detail="Missing target transaction for update")
            
            tx_result = await db.execute(
                select(Transaction).where(Transaction.id == db_proposal.target_transaction_id)
            )
            tx = tx_result.scalars().first()
            if not tx:
                raise HTTPException(status_code=404, detail="Target transaction not found")
            
            for key, value in data.items():
                if hasattr(tx, key) and key != "id":
                    setattr(tx, key, value)
        
        db_proposal.status = "APPROVED"
        await db.commit()
        return {"status": "approved"}
        
    raise HTTPException(status_code=400, detail="Invalid action status")

async def _create_transaction_from_data(data: dict, user_id: str, proposal_id: str, db: AsyncSession) -> Transaction:
    new_tx = Transaction(
        user_id=user_id,
        account_id=data.get("account_id"),
        target_account_id=data.get("target_account_id"),
        category_id=data.get("category_id"),
        amount=data.get("amount"),
        type=data.get("type"),
        transaction_date=(
            datetime.fromisoformat(data["transaction_date"])
            if isinstance(data.get("transaction_date"), str)
            else (data.get("transaction_date") or datetime.now(timezone.utc))
        ),
        note=data.get("note"),
        merchant=data.get("merchant")
    )
    
    # Link to document
    doc_result = await db.execute(
        select(Document)
        .join(ProposedChange, ProposedChange.document_id == Document.id)
        .where(ProposedChange.id == proposal_id)
    )
    doc = doc_result.scalars().first()
    if doc:
        new_tx.documents.append(doc)
    
    return new_tx
