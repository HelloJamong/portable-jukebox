import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.main import app
from src.database import get_db
from src.models import AppSetting, Base, User
from src.auth import hash_password

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_engine)
Base.metadata.create_all(_engine)

_SETTING_DEFAULTS = {
    "pw_min_length": "8", "pw_require_upper": "true",
    "pw_require_number": "true", "pw_require_special": "false",
    "default_password": "Change1234!", "retention_days": "30",
}


@pytest.fixture
def db():
    session = _Session()
    for k, v in _SETTING_DEFAULTS.items():
        if not session.get(AppSetting, k):
            session.add(AppSetting(key=k, value=v))
    session.commit()
    yield session
    session.close()
    with _engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def client(db):
    def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    # No context manager → lifespan (seed/scheduler) skipped
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, username="testuser", role="user", must_change=False):
    u = User(
        username=username,
        hashed_password=hash_password("Test1234"),
        role=role,
        must_change_password=must_change,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
