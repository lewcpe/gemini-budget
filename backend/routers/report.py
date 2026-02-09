from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from datetime import datetime
from collections import defaultdict
import calendar

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
    """
    Calculates historical wealth data points by rolling back transitions from current account balances.
    """
    # Fetch accounts to distinguish types and get current balances
    acc_result = await db.execute(select(Account).where(Account.user_id == current_user.id))
    accounts = acc_result.scalars().all()
    account_map = {a.id: a for a in accounts}
    
    # Fetch all transactions sorted by date DESC
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_date.desc())
    )
    transactions = tx_result.scalars().all()
    
    # Track balances backwards from now
    temp_balances = {a.id: a.current_balance for a in accounts}
    now = datetime.now()
    
    # Group transactions by interval
    txs_by_period = defaultdict(list)
    for tx in transactions:
        if interval == "month":
            period_key = tx.transaction_date.strftime("%Y-%m")
        elif interval == "day":
            period_key = tx.transaction_date.strftime("%Y-%m-%d")
        else: # year
            period_key = tx.transaction_date.strftime("%Y")
        txs_by_period[period_key].append(tx)
        
    # Get all period keys
    if interval == "month":
        now_key = now.strftime("%Y-%m")
    elif interval == "day":
        now_key = now.strftime("%Y-%m-%d")
    else:
        now_key = now.strftime("%Y")
        
    all_periods = sorted(list(txs_by_period.keys() | {now_key}), reverse=True)
    
    # Limit number of points
    if interval == "month" and len(all_periods) > 12:
        all_periods = all_periods[:12]
    elif interval == "day" and len(all_periods) > 30:
        all_periods = all_periods[:30]
        
    data_points = []
    
    for period_key in all_periods:
        # The point for this period represents the state at the END of the period.
        # Since we are iterating backwards (all_periods is sorted reverse=True),
        # the first period_key is the current one, and temp_balances are already
        # at the "end of current period" state.
        
        # Robust calculation:
        # Assets are positive balances, Liabilities (absolute) are negative balances.
        # This handles overdrawn asset accounts and positive-balance liability accounts (credits).
        assets = sum(bal for bal in temp_balances.values() if bal > 0)
        liab_debt_sum = sum(bal for bal in temp_balances.values() if bal < 0)
        
        # Display liabilities as a positive number
        report_liabilities = abs(liab_debt_sum)
        
        # Net worth is the algebraic sum of all balances
        net_worth = sum(temp_balances.values())
        
        # Determine display date
        display_date = period_key
        if interval == "month":
            year, month = map(int, period_key.split("-"))
            _, last_day = calendar.monthrange(year, month)
            display_date = f"{period_key}-{last_day:02d}"
            # If current month, use today's date for a more accurate "as of now"
            if period_key == now_key:
                display_date = now.strftime("%Y-%m-%d")
        
        data_points.append(ReportDataPoint(
            date=display_date,
            assets=assets,
            liabilities=report_liabilities,
            net_worth=net_worth
        ))
        
        # Roll back balances for this period to get state at the end of the *previous* period
        period_txs = txs_by_period[period_key]
        for tx in period_txs:
            if tx.type == "INCOME":
                if tx.account_id in temp_balances:
                    temp_balances[tx.account_id] -= tx.amount
            elif tx.type == "EXPENSE":
                if tx.account_id in temp_balances:
                    temp_balances[tx.account_id] += tx.amount
            elif tx.type == "TRANSFER":
                if tx.account_id in temp_balances:
                    temp_balances[tx.account_id] += tx.amount
                if tx.target_account_id in temp_balances:
                    temp_balances[tx.target_account_id] -= tx.amount
                    
    data_points.reverse()
    return WealthReport(data_points=data_points)
