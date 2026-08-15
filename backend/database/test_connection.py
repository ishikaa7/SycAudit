from sqlalchemy import text
from database.database import engine

with engine.connect() as conn:
    result = conn.execute(
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