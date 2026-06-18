from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth import hash_password
from src.models import AppSetting, Base, DownloadLog, User
from src.scheduler import _delete_expired_files

KST = timezone(timedelta(hours=9))


def _now():
    return datetime.now(KST).replace(tzinfo=None)


@pytest.fixture
def sdb():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine)
    engine.dispose()


def _setup(Session, retention_days, days_ago, filename="f.mp4"):
    db = Session()
    user = User(username="u", hashed_password=hash_password("x"), role="user")
    db.add(user)
    db.flush()
    db.add(AppSetting(key="retention_days", value=str(retention_days)))
    log = DownloadLog(
        user_id=user.id, url="http://x.com", filename=filename,
        format="mp4", status="done",
        downloaded_at=_now() - timedelta(days=days_ago),
    )
    db.add(log)
    db.commit()
    log_id = log.id
    db.close()
    return Session(), log_id


def test_skip_when_retention_zero(sdb):
    db, log_id = _setup(sdb, retention_days=0, days_ago=60)
    with patch("src.scheduler.SessionLocal", sdb):
        _delete_expired_files()
    db.expire_all()
    assert db.get(DownloadLog, log_id).deleted_at is None


def test_delete_expired(sdb, tmp_path):
    fake = tmp_path / "old.mp4"
    fake.write_bytes(b"x")
    db, log_id = _setup(sdb, retention_days=30, days_ago=31, filename="old.mp4")
    with patch("src.scheduler.SessionLocal", sdb), \
         patch.dict("os.environ", {"DOWNLOAD_DIR": str(tmp_path)}):
        _delete_expired_files()
    db.expire_all()
    assert db.get(DownloadLog, log_id).deleted_at is not None
    assert not fake.exists()


def test_skip_not_expired(sdb):
    db, log_id = _setup(sdb, retention_days=30, days_ago=10)
    with patch("src.scheduler.SessionLocal", sdb):
        _delete_expired_files()
    db.expire_all()
    assert db.get(DownloadLog, log_id).deleted_at is None
