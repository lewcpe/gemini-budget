from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
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

# Serve built frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")

# Catch-all for SPA
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Check if the requested path is a file in static dir (like assets/...)
    file_path = os.path.join(static_dir, full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    # Otherwise, serve index.html for SPA routing (if it exists)
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    # Fallback if static files are not built yet
    return {"message": "Gemini Budget API is running. Frontend not found."}
