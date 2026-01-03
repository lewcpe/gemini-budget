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
from ..models import Document, Transaction, ProposedChange, Account, Category
from ..config import settings
from ..database import SessionLocal
import json
from sqlalchemy import desc

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
            
            prompt = """
            Extract all transactions from the following document(s). 
            For each transaction, provide:
            - amount (number)
            - merchant (string)
            - transaction_date (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
            - type (EXPENSE or INCOME)
            - note (any additional details)

            Format the output as a JSON list of objects.
            Return ONLY the JSON list.
            """

            # Prepare multimodal content
            contents = [prompt]
            for img in images:
                contents.append(img)

            response = client.models.generate_content(
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

            # 3. Match and Propose
            for item in extracted_data:
                await create_or_update_proposal(item, doc, db)

            doc.status = "PROCESSED"
            await db.commit()

        except Exception as e:
            print(f"Error processing document {document_id}: {str(e)}")
            doc.status = "ERROR"
            await db.commit()

async def create_or_update_proposal(data: dict, doc: Document, db: AsyncSession):
    """
    Agentic loop to match a transaction:
    1. Gather context (last 5 transactions, accounts).
    2. Prompt Gemini to decide: MATCH, NEW, or QUERY.
    3. Loop up to GENAI_LIMIT_QUERY if Gemini needs more info.
    """
    client = genai.Client(api_key=settings.GOOGLE_GENAI_KEY)
    user_id = doc.user_id
    
    # 1. Gather initial context
    context = await get_agent_context(db, user_id)
    
    query_count = 0
    limit = settings.GENAI_LIMIT_QUERY
    history = []

    while query_count < limit:
        prompt = f"""
        You are an intelligent accounting assistant. Your goal is to decide whether the following parsed transaction
        matches an existing transaction in the database or should be created as a new one.

        Parsed Transaction:
        {json.dumps(data, indent=2)}

        User Context (Last 5 transactions and accounts):
        {json.dumps(context, indent=2)}

        History of your queries and results in this session:
        {json.dumps(history, indent=2)}

        Available Actions:
        1. QUERY: If you need more information, you can query transactions. 
           Available filters: merchant (string), amount (number), start_date (YYYY-MM-DD), end_date (YYYY-MM-DD).
           Example: {{"action": "QUERY", "params": {{"merchant": "Amazon", "amount": 25.00}}}}
        2. DECIDE: If you have enough information, make a decision.
           Options: 
           - "CREATE_NEW": No matching transaction found.
           - "UPDATE_EXISTING": Found a matching transaction that should be updated. Provide the `target_transaction_id`.
           Example: {{"action": "DECIDE", "decision": "UPDATE_EXISTING", "target_transaction_id": "uuid-here", "confidence": 0.95}}
           Example: {{"action": "DECIDE", "decision": "CREATE_NEW", "confidence": 0.8}}

        Return ONLY a JSON object with "action" and relevant fields.
        """

        response = client.models.generate_content(
            model=settings.GOOGLE_GENAI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
            )
        )

        if not response.text:
            print(f"Gemini agent returned no text for document {doc.id}")
            break

        try:
            res = json.loads(response.text)
        except json.JSONDecodeError:
            # Fallback to simple matching if Gemini fails
            print(f"Gemini agent failed to return valid JSON: {response.text}")
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
            decision = res.get("decision")
            target_id = res.get("target_transaction_id")
            confidence = res.get("confidence", 0.9)
            
            if decision == "UPDATE_EXISTING":
                await apply_proposal(data, doc, db, "UPDATE_EXISTING", target_id, confidence)
            else:
                await apply_proposal(data, doc, db, "CREATE_NEW", None, confidence)
            return
        else:
            break

    # Final fallback: use simple logic if limit reached or agent fails
    await fallback_matching_logic(data, doc, db)

async def get_agent_context(db: AsyncSession, user_id: str):
    # Last 5 transactions
    q_t = select(Transaction).where(Transaction.user_id == user_id).order_by(desc(Transaction.transaction_date)).limit(5)
    res_t = await db.execute(q_t)
    transactions = res_t.scalars().all()
    
    # All accounts
    q_a = select(Account).where(Account.user_id == user_id)
    res_a = await db.execute(q_a)
    accounts = res_a.scalars().all()
    
    return {
        "recent_transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "merchant": t.merchant,
                "date": t.transaction_date.isoformat(),
                "type": t.type
            } for t in transactions
        ],
        "accounts": [{"id": a.id, "name": a.name} for a in accounts]
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

async def apply_proposal(data: dict, doc: Document, db: AsyncSession, change_type: str, target_id: Optional[str], confidence: float):
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
    
    await apply_proposal(data, doc, db, change_type, target_id, 0.7)
