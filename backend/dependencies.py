from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db
from .models import User
from .config import settings

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
        await db.commit()
        await db.refresh(user)
    
    return user
