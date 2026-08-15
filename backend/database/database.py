from sqlalchemy.ext.asyncio import create_async_engine

from config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)