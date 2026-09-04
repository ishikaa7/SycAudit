import asyncio

from sqlalchemy import select

from database.models import LLMModel
from database.session import AsyncSessionLocal

SEED_MODELS = [
    {"provider": "groq", "model_name": "qwen/qwen3-32b", "rate_limit_rpm": 30},
    {"provider": "groq", "model_name": "openai/gpt-oss-20b", "rate_limit_rpm": 30},
    {"provider": "huggingface", "model_name": "Qwen/Qwen2.5-7B-Instruct", "rate_limit_rpm": 15},
    {"provider": "gemini", "model_name": "gemini-2.5-flash", "rate_limit_rpm": 10},
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(LLMModel.provider, LLMModel.model_name))
        existing = {(row[0], row[1]) for row in result.all()}

        missing = [m for m in SEED_MODELS if (m["provider"], m["model_name"]) not in existing]
        if not missing:
            print("llm_models already seeded")
            return

        session.add_all(
            LLMModel(
                provider=m["provider"],
                model_name=m["model_name"],
                rate_limit_rpm=m["rate_limit_rpm"],
            )
            for m in missing
        )
        await session.commit()

        for m in missing:
            print(f"inserted: {m['provider']}/{m['model_name']}")

        total = len((await session.execute(select(LLMModel))).all())
        print(f"done — llm_models now has {total} rows")


async def main() -> None:
    try:
        await seed()
    finally:
        from database.database import engine

        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
