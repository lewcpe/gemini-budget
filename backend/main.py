from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import engine, Base
from .routers import accounts, categories, transactions, documents, proposals, report

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

# Register routers
app.include_router(accounts.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(documents.router)
app.include_router(proposals.router)
app.include_router(report.router)

@app.get("/")
async def root():
    return {"message": "Welcome to Gemini Budget API"}
