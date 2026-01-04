from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./gemini_budget.db"
    AUTH_EMAIL_HEADER: str = "X-Forwarded-Email"
    UPLOAD_DIR: Path = Path("backend/uploads")
    GOOGLE_GENAI_KEY: str = ""
    GOOGLE_GENAI_MODEL: str = "gemini-3-flash-preview"
    GENAI_LIMIT_QUERY: int = 5
    DEV_MODE: bool = False
    MAX_CATEGORY: int = 100
    GEMINI_RPM: int = 20
    CORS_ORIGINS: list[str] = ["*"]
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
