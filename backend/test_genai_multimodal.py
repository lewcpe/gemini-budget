import asyncio
import os
import PIL.Image
from google import genai
from backend.config import settings
from pathlib import Path

async def test_genai_multimodal():
    fixture_path = Path("backend/tests/fixtures/grocery-invoice.jpg")
    print(f"Testing model: {settings.GOOGLE_GENAI_MODEL} with {fixture_path}")
    
    client = genai.Client(api_key=settings.GOOGLE_GENAI_KEY)
    img = PIL.Image.open(fixture_path)
    
    try:
        response = await client.aio.models.generate_content(
            model=settings.GOOGLE_GENAI_MODEL,
            contents=["What is in this image?", img],
        )
        print("Response received:")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_genai_multimodal())
