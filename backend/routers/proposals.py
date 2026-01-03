from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..models import ProposedChange, Transaction, User, Account, Category, Document
from ..schemas import ProposedChange as ProposedChangeSchema, ProposedChangeConfirm
from ..dependencies import get_current_user

router = APIRouter(prefix="/proposals", tags=["proposals"])

@router.get("/", response_model=List[ProposedChangeSchema])
async def list_proposals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ProposedChange).where(ProposedChange.user_id == current_user.id, ProposedChange.status == "PENDING")
    )
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
        data = action.edited_data if action.edited_data else db_proposal.proposed_data
        
        if db_proposal.change_type == "CREATE_NEW":
            new_tx = Transaction(
                user_id=current_user.id,
                account_id=data.get("account_id"),
                target_account_id=data.get("target_account_id"),
                category_id=data.get("category_id"),
                amount=data.get("amount"),
                type=data.get("type"),
                transaction_date=datetime.fromisoformat(data.get("transaction_date")) if isinstance(data.get("transaction_date"), str) else data.get("transaction_date"),
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
                if hasattr(tx, key):
                    setattr(tx, key, value)
        
        db_proposal.status = "APPROVED"
        await db.commit()
        return {"status": "approved"}
        
    raise HTTPException(status_code=400, detail="Invalid action status")
