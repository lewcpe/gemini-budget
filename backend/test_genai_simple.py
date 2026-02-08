import asyncio
import os
from google import genai
from backend.config import settings

async def test_genai():
    print(f"Testing model: {settings.GOOGLE_GENAI_MODEL}")
    client = genai.Client(api_key=settings.GOOGLE_GENAI_KEY)
    try:
        response = await client.aio.models.generate_content(
            model=settings.GOOGLE_GENAI_MODEL,
            contents=["Hello, are you there?"],
        )
        print("Response received:")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_genai())
