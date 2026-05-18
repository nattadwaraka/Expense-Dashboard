"""Test isolation: in-memory SQLite before any app imports."""

import os

os.environ["EXPENSE_DB_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from database import Base, engine, ensure_columns
import main


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_columns()
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE expenses SET description = '' WHERE description IS NULL")
        )
    yield


@pytest.fixture
def client():
    return TestClient(main.app)
