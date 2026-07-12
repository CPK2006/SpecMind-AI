from sqlalchemy import text

from app.database.session import engine


def check_database() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        print("✅ Connected to PostgreSQL")