import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app
from backend.config import settings

# Test Database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    connection = await test_engine.connect()
    transaction = await connection.begin()
    
    # Use actual class_ argument if using async_sessionmaker
    session_factory = async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
        class_=AsyncSession
    )
    session = session_factory()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()

@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers():
    return {settings.AUTH_EMAIL_HEADER: "test@example.com"}

@pytest.fixture
def auth_headers_other():
    return {settings.AUTH_EMAIL_HEADER: "other@example.com"}

@pytest.fixture
async def sample_account(client: AsyncClient, auth_headers: dict):
    res = await client.post(
        "/accounts/",
        json={"name": "Bank", "type": "ASSET"},
        headers=auth_headers
    )
    return res.json()["id"]

@pytest.fixture
async def sample_category(client: AsyncClient, auth_headers: dict):
    res = await client.post(
        "/categories/",
        json={"name": "Food", "type": "EXPENSE"},
        headers=auth_headers
    )
    return res.json()["id"]
