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

            extracted_data = json.loads(response.text)
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
    # Try to find a matching transaction
    # Logic: same merchant, same date, same amount (within 1 day range for date maybe?)
    # For now, let's just use exact match or create new.
    
    amount = float(data.get("amount", 0))
    merchant = data.get("merchant", "")
    date_str = data.get("transaction_date", "")
    
    try:
        t_date = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
    except:
        t_date = datetime.now(timezone.utc)

    # Simple matching logic: find existing transactions for this user
    # with similar amount and merchant within a 2-day window
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

    if match:
        change_type = "UPDATE_EXISTING"
        target_id = match.id
    else:
        change_type = "CREATE_NEW"
        target_id = None

    # Check for existing proposal for this document and similar data
    # To avoid creating duplicate proposals if the task is re-run
    query_p = select(ProposedChange).where(
        ProposedChange.document_id == doc.id,
        ProposedChange.target_transaction_id == target_id
    )
    result_p = await db.execute(query_p)
    existing_proposals = result_p.scalars().all()
    
    existing_p = None
    for ep in existing_proposals:
        # Check if proposed data is similar
        ep_amount = float(ep.proposed_data.get("amount", 0))
        ep_merchant = ep.proposed_data.get("merchant", "")
        if abs(ep_amount - amount) < 0.01 and ep_merchant == merchant:
            existing_p = ep
            break
            
    if existing_p:
        existing_p.proposed_data = data
        existing_p.confidence_score = 0.9
        # existing_p.status = "PENDING" # Maybe keep current status?
    else:
        proposal = ProposedChange(
            user_id=doc.user_id,
            document_id=doc.id,
            target_transaction_id=target_id,
            change_type=change_type,
            proposed_data=data,
            confidence_score=0.9,
            status="PENDING"
        )
        db.add(proposal)
