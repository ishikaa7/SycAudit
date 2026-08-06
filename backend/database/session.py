from sqlalchemy.orm import sessionmaker

from database.database import engine

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)