from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..database import get_db
from ..models import Merchant, User
from ..schemas import MerchantCreate, MerchantUpdate, Merchant as MerchantSchema
from ..dependencies import get_current_user, PaginationParams

router = APIRouter(prefix="/merchants", tags=["merchants"])

@router.get("/", response_model=List[MerchantSchema])
async def list_merchants(
    q: Optional[str] = None,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = select(Merchant).where(Merchant.user_id == current_user.id)
    
    if q:
        query = query.where(Merchant.name.ilike(f"%{q}%"))
        
    query = query.offset(pagination.skip).limit(pagination.limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=MerchantSchema)
async def create_merchant(
    merchant: MerchantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_merchant = Merchant(**merchant.model_dump(), user_id=current_user.id)
    db.add(db_merchant)
    await db.commit()
    await db.refresh(db_merchant)
    return db_merchant

@router.patch("/{merchant_id}", response_model=MerchantSchema)
async def update_merchant(
    merchant_id: str,
    merchant_update: MerchantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Merchant).where(Merchant.id == merchant_id, Merchant.user_id == current_user.id)
    )
    db_merchant = result.scalars().first()
    if not db_merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    update_data = merchant_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_merchant, key, value)
    
    await db.commit()
    await db.refresh(db_merchant)
    return db_merchant

@router.delete("/{merchant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_merchant(
    merchant_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Merchant).where(Merchant.id == merchant_id, Merchant.user_id == current_user.id)
    )
    db_merchant = result.scalars().first()
    if not db_merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    
    await db.delete(db_merchant)
    await db.commit()
    return None
