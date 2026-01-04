from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import accounts, categories, transactions, documents, proposals, report, merchants
from .config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Gemini Budget API",
    description="FastAPI Backend for Personal Accounting Application",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
if settings.DEV_MODE:
    app.add_middleware(
        CORSMiddleware,  # type: ignore
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Global OPTIONS handler for non-CORS requests
@app.options("/{path:path}")
async def options_handler(path: str):
    return {"message": "ok"}

# Register routers
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(documents.router)
app.include_router(proposals.router)
app.include_router(report.router)
app.include_router(merchants.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Gemini Budget API"}
