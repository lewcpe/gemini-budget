from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from ..database import get_db
from ..models import Account, User
from ..schemas import AccountCreate, AccountUpdate, Account as AccountSchema
from ..dependencies import get_current_user, PaginationParams

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.get("/", response_model=List[AccountSchema])
async def list_accounts(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Account).where(Account.user_id == current_user.id).offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=AccountSchema)
async def create_account(
    account: AccountCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_account = Account(**account.model_dump(), user_id=current_user.id)
    db.add(db_account)
    await db.commit()
    await db.refresh(db_account)
    return db_account

@router.patch("/{account_id}", response_model=AccountSchema)
async def update_account(
    account_id: str,
    account_update: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    db_account = result.scalars().first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_data = account_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_account, key, value)
    
    await db.commit()
    await db.refresh(db_account)
    return db_account

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    )
    db_account = result.scalars().first()
    if not db_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    await db.delete(db_account)
    await db.commit()
    return None
