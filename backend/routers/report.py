from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from datetime import datetime
from ..database import get_db
from ..models import Account, User, Transaction
from ..schemas import WealthReport, ReportDataPoint
from ..dependencies import get_current_user

router = APIRouter(prefix="/wealth", tags=["wealth"])

@router.get("/chart", response_model=WealthReport)
async def get_wealth_chart(
    interval: str = "month", # day, month, year
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This is a simplified version. A real one would track balance history.
    # For now, we'll return the current state as a single point or dummy points.
    
    # Calculate current assets and liabilities
    result = await db.execute(select(Account).where(Account.user_id == current_user.id))
    accounts = result.scalars().all()
    
    assets = sum(a.current_balance for a in accounts if a.type == "ASSET")
    liabilities = sum(a.current_balance for a in accounts if a.type == "LIABILITY")
    
    # In a real implementation, we'd iterate through periods and calculate historical balances
    # using transactions and current balance as a baseline.
    
    data_points = [
        ReportDataPoint(
            date=datetime.now().strftime("%Y-%m-%d"),
            assets=assets,
            liabilities=liabilities,
            net_worth=assets - liabilities
        )
    ]
    
    return WealthReport(data_points=data_points)
