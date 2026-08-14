from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db

app = FastAPI(title="SycAudit API", version="0.1.0")


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    """
    Proves the whole chain works: app process is up, config loaded,
    and the DB connection is real — not just that uvicorn started.
    """
    db_ok = True
    db_error = None
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — deliberately broad for a health check
        db_ok = False
        db_error = str(exc)

    return {
        "status": "ok" if db_ok else "degraded",
        "environment": settings.environment,
        "database_connected": db_ok,
        "database_error": db_error,
    }
