import asyncio
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import delete, select

from database.models import LLMModel
from database.session import AsyncSessionLocal

SEED_MODELS = [
    {"provider": "groq", "model_name": "openai/gpt-oss-20b", "rate_limit_rpm": 30},
    {"provider": "groq", "model_name": "openai/gpt-oss-120b", "rate_limit_rpm": 30},
    {"provider": "gemini", "model_name": "gemini-3.6-flash", "rate_limit_rpm": 10},
    {"provider": "huggingface", "model_name": "Qwen/Qwen2.5-72B-Instruct", "rate_limit_rpm": 15},
]

# Rows that must never be active responders again. Kept in the table (FK safety)
# but flipped to inactive/non-responder so a "fresh seed" never recreates them
# as responders and existing rows are decommissioned idempotently.
RETIRED_MODELS = [
    ("gemini", "gemini-2.5-flash"),
    ("huggingface", "Qwen/Qwen2.5-7B-Instruct"),
]

# Rows to physically delete (never referenced by other tables).
REMOVED_MODELS = [
    ("groq", "qwen/qwen3-32b"),
]


async def _existing_keys(session) -> set[tuple[str, str]]:
    result = await session.execute(select(LLMModel.provider, LLMModel.model_name))
    return {(row[0], row[1]) for row in result.all()}


async def _insert_missing(session, existing: set[tuple[str, str]]) -> None:
    missing = [m for m in SEED_MODELS if (m["provider"], m["model_name"]) not in existing]
    if not missing:
        return
    session.add_all(
        LLMModel(
            provider=m["provider"],
            model_name=m["model_name"],
            rate_limit_rpm=m["rate_limit_rpm"],
        )
        for m in missing
    )
    for m in missing:
        print(f"inserted: {m['provider']}/{m['model_name']}")


async def _ensure_active(session) -> None:
    for m in SEED_MODELS:
        rows = (
            await session.execute(
                select(LLMModel).where(
                    LLMModel.provider == m["provider"],
                    LLMModel.model_name == m["model_name"],
                )
            )
        ).scalars().all()
        for row in rows:
            if not (row.is_responder and row.is_active):
                row.is_responder = True
                row.is_active = True
                print(f"reactivated: {row.provider}/{row.model_name}")


async def _retire(session) -> None:
    for provider, model_name in RETIRED_MODELS:
        rows = (
            await session.execute(
                select(LLMModel).where(
                    LLMModel.provider == provider, LLMModel.model_name == model_name
                )
            )
        ).scalars().all()
        for row in rows:
            if row.is_responder or row.is_active:
                row.is_responder = False
                row.is_active = False
                print(f"retired: {provider}/{model_name}")


async def _remove_stale(session, existing: set[tuple[str, str]]) -> None:
    stale = [pair for pair in REMOVED_MODELS if pair in existing]
    if not stale:
        return
    for provider, model_name in stale:
        await session.execute(
            delete(LLMModel).where(
                LLMModel.provider == provider,
                LLMModel.model_name == model_name,
            )
        )
        print(f"removed stale: {provider}/{model_name}")


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing = await _existing_keys(session)
        await _insert_missing(session, existing)
        await _ensure_active(session)
        await _retire(session)
        await _remove_stale(session, existing)
        await session.commit()

        active = (
            await session.execute(
                select(LLMModel).where(LLMModel.is_responder.is_(True)).order_by(LLMModel.provider)
            )
        ).scalars().all()
        print(f"done - {len(active)} active responder model(s):")
        for row in active:
            print(f"  {row.provider:12} {row.model_name} (rpm={row.rate_limit_rpm})")


async def main() -> None:
    try:
        await seed()
    finally:
        from database.database import engine

        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())