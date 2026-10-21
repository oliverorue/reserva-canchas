import os
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp.name) / 'test.db'}"

from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app, seed_courts  # noqa: E402


@pytest.fixture()
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_courts(session)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    with TestClient(app) as c:
        yield c
