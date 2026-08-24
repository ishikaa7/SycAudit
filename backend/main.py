from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health import router as health_router
from api.submissions import router as submissions_router
from database.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="SycAudit API", version="0.1.0", lifespan=lifespan)


@app.get("/")
async def root() -> dict:
    return {"name": "SycAudit API", "version": "0.1.0", "docs": "/docs", "health": "/health"}


app.include_router(health_router)
app.include_router(submissions_router)
