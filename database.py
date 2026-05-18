import os

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = os.environ.get("EXPENSE_DB_URL", "sqlite:///./expense_tracker.db")

_engine_kwargs = {"connect_args": {"check_same_thread": False}}
if DATABASE_URL.startswith("sqlite") and ":memory:" in DATABASE_URL:
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def ensure_columns():
    """Add columns introduced after first DB deploy (SQLite ALTER)."""
    with engine.begin() as conn:
        def col_names(table: str) -> set[str]:
            rows = conn.execute(text(f"PRAGMA table_info({table})"))
            return {r[1] for r in rows}

        for table, additions in (
            ("users", (("phone", "VARCHAR DEFAULT ''"),)),
            ("categories", (("description", "VARCHAR DEFAULT ''"),)),
            (
                "expenses",
                (
                    ("notes", "VARCHAR DEFAULT ''"),
                    ("payment_method", "VARCHAR DEFAULT ''"),
                ),
            ),
        ):
            have = col_names(table)
            for col, ddl in additions:
                if col not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
