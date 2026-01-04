from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .models import User, Account, Category
from .config import settings
from typing import Optional

class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = skip
        self.limit = limit

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    x_forwarded_email: str = Header(None, alias=settings.AUTH_EMAIL_HEADER)
) -> User:
    if not x_forwarded_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {settings.AUTH_EMAIL_HEADER} header",
        )
    
    # Check if user exists, if not create them (lazy registration)
    result = await db.execute(select(User).where(User.email == x_forwarded_email))
    user = result.scalars().first()
    
    if not user:
        user = User(email=x_forwarded_email, full_name=x_forwarded_email.split("@")[0])
        db.add(user)
        await db.flush() # Flush to get user.id
        
        # Create default Petty Cash Account
        petty_cash = Account(
            user_id=user.id,
            name="Petty Cash Account",
            type="ASSET",
            sub_type="CASH",
            currency="USD",
            description="Default account for miscellaneous cash expenses and bills without specified accounts."
        )
        db.add(petty_cash)
        
        # Create default categories
        default_categories = [
            ("Food", "EXPENSE"),
            ("Transportation", "EXPENSE"),
            ("Housing", "EXPENSE"),
            ("Entertainment", "EXPENSE"),
            ("Utilities", "EXPENSE"),
            ("Health", "EXPENSE"),
            ("Salary", "INCOME"),
            ("Others", "EXPENSE"),
        ]
        for name, cat_type in default_categories:
            db.add(Category(user_id=user.id, name=name, type=cat_type))
            
        await db.commit()
        await db.refresh(user)
    
    return user
