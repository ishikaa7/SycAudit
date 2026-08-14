"""
Run once after migrations: `python -m app.seed_models`
Populates llm_models with the four models decided on. Safe to re-run —
skips any row that already exists (matched on provider+model_name+version).
"""
import asyncio

from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import LLMModel

MODELS = [
    dict(
        provider="groq", model_name="qwen3-32b", version=None,
        temperature=0.7, max_tokens=1024, rate_limit_rpm=60,
        is_responder=True, is_framer=True, is_grader=True,
    ),
    dict(
        provider="groq", model_name="gpt-oss-20b", version=None,
        temperature=0.7, max_tokens=1024, rate_limit_rpm=60,
        is_responder=True, is_framer=True, is_grader=True,
    ),
    dict(
        provider="gemini", model_name="gemini-2.5-flash", version=None,
        temperature=0.7, max_tokens=1024, rate_limit_rpm=15,  # free-tier ceiling — verify current value before demo
        is_responder=True, is_framer=False, is_grader=True,
    ),
    dict(
        provider="huggingface", model_name="Qwen2.5-7B-Instruct", version=None,
        temperature=0.7, max_tokens=1024, rate_limit_rpm=None,  # HF free tier: no fixed RPM, but expect queueing/cold starts
        is_responder=True, is_framer=False, is_grader=False,
    ),
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for entry in MODELS:
            existing = await session.execute(
                select(LLMModel).where(
                    LLMModel.provider == entry["provider"],
                    LLMModel.model_name == entry["model_name"],
                    LLMModel.version == entry["version"],
                )
            )
            if existing.scalar_one_or_none() is not None:
                print(f"skip (exists): {entry['provider']}/{entry['model_name']}")
                continue
            session.add(LLMModel(**entry))
            print(f"inserted: {entry['provider']}/{entry['model_name']}")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
