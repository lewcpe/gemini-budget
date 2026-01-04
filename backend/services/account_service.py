from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_, case
from ..models import Account, Transaction

async def recalculate_account_balance(db: AsyncSession, account_id: str):
    """
    Recalculates and updates the current_balance for a specific account
    by summing all its transactions.
    """
    # Sum as source account (EXPENSE or TRANSFER out)
    source_query = select(
        func.sum(
            case(
                (Transaction.type == 'EXPENSE', Transaction.amount),
                (Transaction.type == 'TRANSFER', Transaction.amount),
                else_=0
            )
        )
    ).where(Transaction.account_id == account_id)
    
    # Sum as primary account (INCOME)
    income_query = select(
        func.sum(
            case(
                (Transaction.type == 'INCOME', Transaction.amount),
                else_=0
            )
        )
    ).where(Transaction.account_id == account_id)

    # Sum as target account (TRANSFER in)
    target_query = select(
        func.sum(
            case(
                (Transaction.type == 'TRANSFER', Transaction.amount),
                else_=0
            )
        )
    ).where(Transaction.target_account_id == account_id)

    source_res = await db.execute(source_query)
    income_res = await db.execute(income_query)
    target_res = await db.execute(target_query)

    source_sum = source_res.scalar() or 0.0
    income_sum = income_res.scalar() or 0.0
    target_sum = target_res.scalar() or 0.0

    new_balance = income_sum + target_sum - source_sum

    # Update the account
    account_result = await db.execute(select(Account).where(Account.id == account_id))
    account = account_result.scalars().first()
    if account:
        account.current_balance = new_balance
        await db.flush()
    
    return new_balance
