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

            # 2. Extract transactions using Gemini
            client = genai.Client(api_key=settings.GOOGLE_GENAI_KEY)
            
            # Fetch available categories to provide as context
            cat_query = select(Category).where(Category.user_id == doc.user_id).limit(settings.MAX_CATEGORY)
            cat_res = await db.execute(cat_query)
            categories = cat_res.scalars().all()
            category_list = [{"id": c.id, "name": c.name, "type": c.type} for c in categories]

            prompt = f"""
            Extract all transactions from the following document(s). 
            For each transaction, provide:
            - amount (number)
            - merchant (string)
            - transaction_date (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
            - type (EXPENSE or INCOME)
            - category (suggest a category name if possible, or try to match one from the list below)
            - category_id (the ID of the matching category from the list below, if it fits)
            - note (any additional details)

            Available Categories:
            {json.dumps(category_list, indent=2)}

            Format the output as a JSON list of objects.
            Return ONLY the JSON list.
            """

            # Prepare multimodal content
            contents = [prompt]
            for img in images:
                contents.append(img)

            response = await client.aio.models.generate_content(
                model=settings.GOOGLE_GENAI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',
                )
            )

            if not response.text or not response.text.strip():
                print(f"Error processing document {document_id}: Gemini returned an empty or null response.")
                doc.status = "ERROR"
                await db.commit()
                return

            try:
                extracted_data = json.loads(response.text)
            except json.JSONDecodeError as je:
                print(f"Error decoding JSON for document {document_id}: {str(je)}")
                print(f"Response text: {response.text}")
                doc.status = "ERROR"
                await db.commit()
                return

            if not isinstance(extracted_data, list):
                extracted_data = [extracted_data]

            # 3. Match and Propose (Batch)
            await create_proposals_for_extracted_data(extracted_data, doc, db)

            doc.status = "PROCESSED"
            await db.commit()

        except Exception as e:
            print(f"Error processing document {document_id}: {str(e)}")
            doc.status = "ERROR"
            await db.commit()

async def create_proposals_for_extracted_data(extracted_data: list, doc: Document, db: AsyncSession):
    """
    Agentic loop to process all transactions from a document at once.
    Allows for batching (e.g., New Account + Multiple Transactions).
    """
    client = genai.Client(api_key=settings.GOOGLE_GENAI_KEY)
    user_id = doc.user_id
    
    # Extract merchant names for context filtering
    extracted_merchants = list(set(item.get("merchant") for item in extracted_data if item.get("merchant")))
    context = await get_agent_context(db, user_id, extracted_merchants)
    
    query_count = 0
    limit = settings.GENAI_LIMIT_QUERY
    history = []

    while query_count < limit:
        prompt = f"""
        You are an intelligent accounting assistant. Your goal is to process the following extracted transactions
        and decide whether they match existing ones, should be created individually, or part of a batch.

        Extracted Transactions:
        {json.dumps(extracted_data, indent=2)}

        User Context (Accounts, Categories, and Relevant Merchants):
        {json.dumps(context, indent=2)}

        History of your queries and results:
        {json.dumps(history, indent=2)}

        CRITICAL RULE:
        Every transaction MUST have an `account_id` if it is a `CREATE_NEW` or `UPDATE_EXISTING`.
        If the document doesn't specify which account was used to pay (e.g., a bill) and you cannot find a matching account in the context, use the ID of the "Petty Cash Account". If "Petty Cash Account" is not in the context, you can still reference it by name or assume it will be handled.
        
        CATEGORY & MERCHANT MATCHING:
        - Try to find the best `category_id` from the available categories based on the transaction content or merchant.
        - If the merchant name in the document is similar to one of the "merchants" in the context, use its `name` and `default_category_id`.
        - If the transaction matches an existing transaction, use its `category_id`.
        - If you recognize a merchant but it's not in the context, suggest a likely category name.
        
        Available Actions:
        1. QUERY: If you need more information about a specific transaction or merchant.
           Example: {{"action": "QUERY", "params": {{"merchant": "Amazon", "amount": 25.00}}}}
        2. DECIDE: Make a final proposal for the document. You can return multiple proposals.
           Decision Options for each item: 
           - "CREATE_NEW": No matching transaction found.
           - "UPDATE_EXISTING": Match found. Provide `target_transaction_id`.
           - "CREATE_ACCOUNT": If one or more transactions belong to a NEW account. Provide `new_account_data` and the list of `transactions`.

           Return format for DECIDE:
           {{
             "action": "DECIDE",
             "proposals": [
               {{
                 "type": "CREATE_NEW",
                 "data": {{...}},
                 "confidence": 0.9
               }},
               {{
                 "type": "CREATE_ACCOUNT",
                 "new_account_data": {{"name": "...", "type": "...", "sub_type": "...", "description": "..."}},
                 "transactions": [{{...}}, {{...}}],
                 "confidence": 0.95
               }}
             ]
           }}

        Return ONLY a JSON object.
        """

        response = await client.aio.models.generate_content(
            model=settings.GOOGLE_GENAI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
            )
        )

        if not response.text:
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
            return
        else:
            break

    # Fallback if AI fails: process each item with fallback logic
    for item in extracted_data:
        await fallback_matching_logic(item, doc, db)

async def create_or_update_proposal(data: dict, doc: Document, db: AsyncSession):
    # This is now kept for backward compatibility or individual fallbacks, 
    # but the logic is mostly moved to create_proposals_for_extracted_data.
    await fallback_matching_logic(data, doc, db)

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
    # Ensure account_id for CREATE_NEW if missing
    if change_type == "CREATE_NEW" and not data.get("account_id"):
        data["account_id"] = await _get_petty_cash_account(db, doc.user_id)
        
    # Attempt to suggest category if missing
    merchant_name = data.get("merchant")
    if not data.get("category_id") and merchant_name:
        data["category_id"] = await _get_merchant_default_category(db, doc.user_id, str(merchant_name))

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
