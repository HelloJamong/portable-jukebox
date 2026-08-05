from src.auth import verify_password
from src.models import ActivityLog, User
from .conftest import make_user


def _login_admin(client, db):
    make_user(db, username="adminuser", role="admin")
    client.post("/login", data={"username": "adminuser", "password": "Test1234"})


def test_delete_then_recreate_same_username(client, db):
    _login_admin(client, db)
    target = make_user(db, username="alice")

    r = client.delete(f"/admin/users/{target.id}")
    assert r.status_code == 200

    r = client.post("/admin/users", data={"username": "alice", "role": "user"}, follow_redirects=False)
    assert r.status_code == 303  # previously failed with 400 "이미 존재하는 아이디입니다."

    active = db.query(User).filter(User.username == "alice", User.is_active.is_(True)).first()
    assert active is not None
    assert active.id != target.id


def test_reset_password_uses_default_and_logs(client, db):
    _login_admin(client, db)
    target = make_user(db, username="bob")
    old_hash = target.hashed_password

    r = client.post(f"/admin/users/{target.id}/reset-password", follow_redirects=False)
    assert r.status_code == 303

    db.refresh(target)
    assert target.hashed_password != old_hash
    assert verify_password("Change1234!", target.hashed_password)
    assert target.must_change_password is True

    log = db.query(ActivityLog).filter(ActivityLog.event_type == "password_reset").first()
    assert log is not None
    assert log.username == "adminuser"
