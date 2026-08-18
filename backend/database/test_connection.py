import asyncio

from sqlalchemy import text

from database.database import engine


async def main() -> None:
    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
        )

        print("Connected to Supabase!")
        print("\nSycAudit tables:")

        for row in result:
            print(row[0])


if __name__ == "__main__":
    asyncio.run(main())