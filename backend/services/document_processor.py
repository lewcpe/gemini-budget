import os
import tempfile
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timezone
import PIL.Image
from pdf2image import convert_from_path
from google import genai
from google.genai import types
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Document, Transaction, ProposedChange, Account, Category, Merchant
from ..config import settings
from ..database import SessionLocal
from sqlalchemy import desc, or_
import json
import asyncio
import time

class RateLimiter:
    def __init__(self, rpm: int):
        self.interval = 60.0 / rpm if rpm > 0 else 0
        self.last_call = 0.0
        self.lock = asyncio.Lock()

    async def wait(self):
        if self.interval <= 0:
            return
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_call
            if elapsed < self.interval:
                await asyncio.sleep(self.interval - elapsed)
                self.last_call = time.time()
            else:
                self.last_call = now

gemini_limiter = RateLimiter(settings.GEMINI_RPM)

async def process_document_task(document_id: str):
    """
    Background task to process a document:
    1. Convert PDF to images if necessary.
    2. Use Gemini to extract transactions.
    3. Match extracted transactions with existing ones.
    4. Create or update ProposedChanges.
    """
    async with SessionLocal() as db:
        # Fetch document
        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalars().first()
        if not doc:
            return

        doc.status = "PARSING"
        await db.commit()

        try:
            # 1. Prepare images
            images = []
            file_path = Path(doc.file_path)
            
            if doc.mime_type == "application/pdf":
                with tempfile.TemporaryDirectory() as temp_dir:
                    converted_images = convert_from_path(file_path)
                    for i, img in enumerate(converted_images):
                        img_path = Path(temp_dir) / f"page_{i}.jpg"
                        img.save(img_path, "JPEG")
                        images.append(PIL.Image.open(img_path))
            elif doc.mime_type.startswith("image/"):
                images.append(PIL.Image.open(file_path))
            else:
                doc.status = "ERROR"
                await db.commit()
                return

            if not images:
                doc.status = "ERROR"
                await db.commit()
                return

            # 2. Unified Agentic Loop
            client = genai.Client(api_key=settings.GOOGLE_GENAI_KEY)
            user_id = doc.user_id
            
            # Initial context (without merchant filtering yet, or we can do a broad one)
            context = await get_agent_context(db, user_id)
            
            query_count = 0
            limit = settings.GENAI_LIMIT_QUERY
            history = []

            while query_count < limit:
                prompt = f"""
                You are an intelligent accounting assistant. Your goal is to extract all transactions from the following document images
                and decide whether they match existing ones, should be created individually, or part of a batch.

                User Context (Accounts, Categories, and Recent Transactions):
                {json.dumps(context, indent=2)}

                History of your queries and results:
                {json.dumps(history, indent=2)}

                CRITICAL RULES:
                1. Every transaction MUST have an `account_id` if it is a `CREATE_NEW` or `UPDATE_EXISTING`.
                2. If the document clearly belongs to a specific account (e.g., a credit card statement) that is NOT in the context, propose `CREATE_ACCOUNT`.
                3. If you cannot find a matching account in the context or suggestions, use the ID of the "Petty Cash Account".
                4. CATEGORY MATCHING: Use the provided categories. If you're unsure, suggest a likely category name.
                5. ACCOUNT TYPES: When proposing `CREATE_ACCOUNT`, the `type` MUST be exactly 'ASSET' or 'LIABILITY'. Use `sub_type` for specific details (e.g., 'BANK', 'CREDIT_CARD', 'CASH', 'INVESTMENT').
                
                Available Actions:
                1. QUERY: If you need to search for more transactions to confirm a match.
                   Example: {{"action": "QUERY", "params": {{"merchant": "Amazon", "amount": 25.00}}}}
                2. DECIDE: Make a final proposal for the document. You can return multiple proposals.
                   Decision Options for each item: 
                   - "CREATE_NEW": No matching transaction found.
                   - "UPDATE_EXISTING": Match found. Provide `target_transaction_id`.
                   - "CREATE_ACCOUNT": If transactions belong to a NEW account. Provide `new_account_data` and the list of `transactions`.

                   Return format for DECIDE:
                   {{
                     "action": "DECIDE",
                     "proposals": [
                       {{
                         "type": "CREATE_NEW",
                         "data": {{
                            "amount": 10.50,
                            "merchant": "Coffee Shop",
                            "transaction_date": "2026-01-01",
                            "type": "EXPENSE",
                            "category_id": "cat_123",
                            "account_id": "acc_456"
                         }},
                         "confidence": 0.9
                       }},
                       {{
                         "type": "CREATE_ACCOUNT",
                         "new_account_data": {{
                            "name": "Human-readable name", 
                            "type": "MANDATORY: MUST BE EITHER 'ASSET' OR 'LIABILITY'", 
                            "sub_type": "Optional: e.g., 'BANK', 'SAVINGS', 'CREDIT_CARD', 'CASH'", 
                            "description": "..."
                         }},
                         "transactions": [{{
                            "amount": 1000.0,
                            "merchant": "Employer",
                            "transaction_date": "2026-01-01",
                            "type": "INCOME",
                            "category_id": "MANDATORY: Use an ID from the context"
                         }}],
                         "confidence": 0.95
                       }}
                     ]
                   }}

                Return ONLY a JSON object.
                """

                # Prepare multimodal content: Prompt + Images
                contents = [prompt]
                for img in images:
                    contents.append(img)

                await gemini_limiter.wait()
                response = await client.aio.models.generate_content(
                    model=settings.GOOGLE_GENAI_MODEL,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                    )
                )

                if not response.text or not response.text.strip():
                    break

                try:
                    res = json.loads(response.text)
                except json.JSONDecodeError:
                    break

                if res.get("action") == "QUERY":
                    query_count += 1
                    params = res.get("params", {})
                    search_results = await search_transactions_logic(db, user_id, params)
                    history.append({
                        "query": params,
                        "results": search_results
                    })
                    continue
                elif res.get("action") == "DECIDE":
                    proposals = res.get("proposals", [])
                    validation_errors = []
                    
                    # Extract valid IDs from context
                    valid_account_ids = {a["id"] for a in context.get("accounts", [])}
                    valid_category_ids = {c["id"] for c in context.get("categories", [])}
                    valid_transaction_types = {"INCOME", "EXPENSE", "TRANSFER"}

                    for p in proposals:
                        p_type = p.get("type")
                        if p_type == "CREATE_ACCOUNT":
                            new_acc = p.get("new_account_data", {})
                            if new_acc.get("type") not in ["ASSET", "LIABILITY"]:
                                validation_errors.append(f"Invalid account type '{new_acc.get('type')}' for account '{new_acc.get('name')}'. MUST be 'ASSET' or 'LIABILITY'.")
                            
                            for tx in p.get("transactions", []):
                                if tx.get("type") not in valid_transaction_types:
                                    validation_errors.append(f"Invalid transaction type '{tx.get('type')}'. MUST be 'INCOME', 'EXPENSE', or 'TRANSFER'.")
                                if tx.get("category_id") and tx.get("category_id") not in valid_category_ids:
                                    validation_errors.append(f"Invalid category_id '{tx.get('category_id')}' for transaction with merchant '{tx.get('merchant')}'. This ID does not exist in your context. Use a valid ID from the provided categories list.")
                        
                        elif p_type in ["CREATE_NEW", "UPDATE_EXISTING"]:
                            p_data = p.get("data", {})
                            if p_data.get("account_id") and p_data.get("account_id") not in valid_account_ids:
                                validation_errors.append(f"Invalid account_id '{p_data.get('account_id')}'. This ID does not exist. Use a valid ID from the provided accounts list.")
                            if p_data.get("category_id") and p_data.get("category_id") not in valid_category_ids:
                                validation_errors.append(f"Invalid category_id '{p_data.get('category_id')}' for merchant '{p_data.get('merchant')}'. This ID does not exist. Use a valid ID from the provided categories list.")
                            if p_data.get("type") and p_data.get("type") not in valid_transaction_types:
                                validation_errors.append(f"Invalid transaction type '{p_data.get('type')}'. MUST be 'INCOME', 'EXPENSE', or 'TRANSFER'.")

                    if validation_errors:
                        query_count += 1
                        history.append({
                            "decision": res,
                            "errors": validation_errors
                        })
                        continue

                    for p in proposals:
                        p_type = p.get("type")
                        p_data = p.get("data")
                        p_confidence = p.get("confidence", 0.7)
                        
                        if p_type == "CREATE_ACCOUNT":
                            batch_data = {
                                "_new_account": p.get("new_account_data"),
                                "transactions": p.get("transactions")
                            }
                            await apply_proposal(batch_data, doc, db, "CREATE_ACCOUNT", None, p_confidence)
                        elif p_type == "UPDATE_EXISTING":
                            await apply_proposal(p_data, doc, db, "UPDATE_EXISTING", p.get("target_transaction_id"), p_confidence)
                        else:
                            await apply_proposal(p_data, doc, db, "CREATE_NEW", None, p_confidence)
                    
                    doc.status = "PROCESSED"
                    await db.commit()
                    return
                else:
                    break

            # Fallback (optional, if DECIDE was never reached)
            doc.status = "PROCESSED"
            await db.commit()

        except Exception as e:
            print(f"Error processing document {document_id}: {str(e)}")
            doc.status = "ERROR"
            await db.commit()

async def get_agent_context(db: AsyncSession, user_id: str, relevant_merchants: Optional[List[str]] = None):
    # Last transactions
    q_t = select(Transaction).where(Transaction.user_id == user_id).order_by(desc(Transaction.transaction_date))
    
    # If we have relevant merchants, prioritize transactions from them
    relevant_transactions: List[Transaction] = []
    if relevant_merchants:
        t_conditions = [Transaction.merchant.ilike(f"%{m}%") for m in relevant_merchants if m]
        if t_conditions:
            q_t_relevant = select(Transaction).where(Transaction.user_id == user_id, or_(*t_conditions)).limit(10)
            res_t_rel = await db.execute(q_t_relevant)
            relevant_transactions = list(res_t_rel.scalars().all())

    res_t = await db.execute(q_t.limit(10))
    recent_transactions = list(res_t.scalars().all())
    
    # Combine and deduplicate
    all_context_transactions = {t.id: t for t in recent_transactions + relevant_transactions}.values()
    
    # All accounts
    q_a = select(Account).where(Account.user_id == user_id)
    res_a = await db.execute(q_a)
    accounts = res_a.scalars().all()
    
    # All categories
    q_c = select(Category).where(Category.user_id == user_id)
    res_c = await db.execute(q_c)
    categories = res_c.scalars().all()
    
    # Filtered merchants
    if relevant_merchants:
        m_conditions = [Merchant.name.ilike(f"%{m}%") for m in relevant_merchants if m]
        if m_conditions:
            q_m = select(Merchant).where(Merchant.user_id == user_id, or_(*m_conditions))
        else:
            q_m = select(Merchant).where(Merchant.user_id == user_id).limit(20)
    else:
        q_m = select(Merchant).where(Merchant.user_id == user_id).limit(20)
        
    res_m = await db.execute(q_m)
    merchants = res_m.scalars().all()
    
    return {
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "merchant": t.merchant,
                "date": t.transaction_date.isoformat(),
                "type": t.type,
                "category_id": t.category_id
            } for t in all_context_transactions
        ],
        "accounts": [{"id": a.id, "name": a.name} for a in accounts],
        "categories": [{"id": c.id, "name": c.name, "type": c.type} for c in categories],
        "merchants": [{"id": m.id, "name": m.name, "default_category_id": m.default_category_id} for m in merchants]
    }

async def search_transactions_logic(db: AsyncSession, user_id: str, params: dict):
    query = select(Transaction).where(Transaction.user_id == user_id)
    
    if "merchant" in params:
        query = query.where(Transaction.merchant.ilike(f"%{params['merchant']}%"))
    if "amount" in params:
        query = query.where(Transaction.amount == float(params['amount']))
    if "start_date" in params:
        query = query.where(Transaction.transaction_date >= datetime.fromisoformat(params['start_date']))
    if "end_date" in params:
        query = query.where(Transaction.transaction_date <= datetime.fromisoformat(params['end_date']))
        
    res = await db.execute(query.limit(20))
    transactions = res.scalars().all()
    
    return [
        {
            "id": t.id,
            "amount": t.amount,
            "merchant": t.merchant,
            "date": t.transaction_date.isoformat(),
            "type": t.type
        } for t in transactions
    ]

async def _get_petty_cash_account(db: AsyncSession, user_id: str) -> str:
    """
    Finds the 'Petty Cash Account' for the user.
    It's expected to have been created during user registration.
    """
    query = select(Account).where(
        Account.user_id == user_id,
        Account.name == "Petty Cash Account"
    )
    result = await db.execute(query)
    account = result.scalars().first()
    
    if not account:
        # Fallback to any account if Petty Cash is missing for some reason
        # (Though it should exist)
        fallback_query = select(Account).where(Account.user_id == user_id).limit(1)
        fallback_res = await db.execute(fallback_query)
        account = fallback_res.scalars().first()
        
    if not account:
        raise ValueError(f"No accounts found for user {user_id}")
        
    return account.id

async def _get_merchant_default_category(db: AsyncSession, user_id: str, merchant_name: str) -> Optional[str]:
    """
    Looks up a merchant by name (case-insensitive) and returns its default category ID.
    """
    if not merchant_name:
        return None
    query = select(Merchant).where(
        Merchant.user_id == user_id,
        Merchant.name.ilike(merchant_name)
    )
    result = await db.execute(query)
    merchant = result.scalars().first()
    return merchant.default_category_id if merchant else None

async def apply_proposal(data: dict, doc: Document, db: AsyncSession, change_type: str, target_id: Optional[str], confidence: float):
    # Get merchant name for category lookup
    merchant_name = data.get("merchant")

    # 1. Validate and default account_id
    acc_id = data.get("account_id")
    if change_type == "CREATE_NEW":
        # Check if the account exists for this user
        valid_acc = False
        if acc_id:
            res_a = await db.execute(select(Account).where(Account.id == acc_id, Account.user_id == doc.user_id))
            if res_a.scalars().first():
                valid_acc = True
        
        if not valid_acc:
            # Default to Petty Cash if hallucinated or missing
            data["account_id"] = await _get_petty_cash_account(db, doc.user_id)
            
    # 2. Validate and suggest category if missing or hallucinated
    cat_id = data.get("category_id")
    valid_cat = False
    if cat_id:
        res_c = await db.execute(select(Category).where(Category.id == cat_id, Category.user_id == doc.user_id))
        if res_c.scalars().first():
            valid_cat = True
    
    if not valid_cat and merchant_name:
        data["category_id"] = await _get_merchant_default_category(db, doc.user_id, str(merchant_name))
    elif not valid_cat:
        data["category_id"] = None

    # 3. Sanitize transaction type
    tx_type = data.get("type", "EXPENSE")
    if tx_type not in ["INCOME", "EXPENSE", "TRANSFER"]:
        # Simple mapping/fallback
        if tx_type in ["DEBIT", "PAYMENT", "CASH_OUT"]:
            data["type"] = "EXPENSE"
        elif tx_type in ["CREDIT", "DEPOSIT", "CASH_IN"]:
            data["type"] = "INCOME"
        else:
            data["type"] = "EXPENSE"

    # Sanitize account type if it's CREATE_ACCOUNT
    if change_type == "CREATE_ACCOUNT" and data.get("_new_account"):
        acc_data = data["_new_account"]
        acc_type = acc_data.get("type")
        if acc_type not in ["ASSET", "LIABILITY"]:
            # Fallback/Sanitization: Usually bank accounts or cash are ASSETS
            # If the AI sent 'BANK' or 'SAVINGS', it belongs in sub_type
            if not acc_data.get("sub_type"):
                acc_data["sub_type"] = acc_type
            acc_data["type"] = "ASSET"

    # Check for existing proposal for this document and target
    query_p = select(ProposedChange).where(
        ProposedChange.document_id == doc.id,
        ProposedChange.target_transaction_id == target_id
    )
    result_p = await db.execute(query_p)
    existing_p = result_p.scalars().first()
    
    if existing_p:
        existing_p.proposed_data = data
        existing_p.confidence_score = confidence
        existing_p.change_type = change_type
    else:
        proposal = ProposedChange(
            user_id=doc.user_id,
            document_id=doc.id,
            target_transaction_id=target_id,
            change_type=change_type,
            proposed_data=data,
            confidence_score=confidence,
            status="PENDING"
        )
        db.add(proposal)

async def fallback_matching_logic(data: dict, doc: Document, db: AsyncSession):
    # Original matching logic as fallback
    amount = float(data.get("amount", 0))
    merchant = data.get("merchant", "")
    date_str = data.get("transaction_date", "")
    
    try:
        t_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except:
        t_date = datetime.now(timezone.utc)

    query = select(Transaction).where(
        Transaction.user_id == doc.user_id,
        Transaction.amount == amount,
        Transaction.merchant.ilike(f"%{merchant}%")
    )
    result = await db.execute(query)
    existing_transactions = result.scalars().all()
    
    match = None
    for et in existing_transactions:
        if abs((et.transaction_date - t_date).days) <= 1:
            match = et
            break

    change_type = "UPDATE_EXISTING" if match else "CREATE_NEW"
    target_id = match.id if match else None
    
    if change_type == "CREATE_NEW" and not data.get("account_id"):
        data["account_id"] = await _get_petty_cash_account(db, doc.user_id)
        
    await apply_proposal(data, doc, db, change_type, target_id, 0.7)
