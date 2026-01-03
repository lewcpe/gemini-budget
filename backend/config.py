from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./gemini_budget.db"
    AUTH_EMAIL_HEADER: str = "X-Forwarded-Email"
    UPLOAD_DIR: Path = Path("backend/uploads")
    GOOGLE_GENAI_KEY: str = ""
    GOOGLE_GENAI_MODEL: str = "gemini-3-flash-preview"
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
