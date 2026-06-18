from src.auth import hash_password, validate_password_complexity, verify_password
from .conftest import make_user


def test_password_round_trip():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_login_success(client, db):
    make_user(db)
    r = client.post("/login", data={"username": "testuser", "password": "Test1234"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_login_fail(client, db):
    make_user(db)
    r = client.post("/login", data={"username": "testuser", "password": "wrong"}, follow_redirects=False)
    assert r.status_code == 401


def test_login_redirects_admin(client, db):
    make_user(db, username="adminuser", role="admin")
    r = client.post("/login", data={"username": "adminuser", "password": "Test1234"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/admin/users"


def test_must_change_password(client, db):
    make_user(db, must_change=True)
    r = client.post("/login", data={"username": "testuser", "password": "Test1234"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/change-password"


def test_require_login_redirect(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_require_admin_forbidden(client, db):
    make_user(db)
    client.post("/login", data={"username": "testuser", "password": "Test1234"})
    r = client.get("/admin/users")
    assert r.status_code == 403


def test_password_complexity(db):
    assert validate_password_complexity("short", db) is not None       # 길이 미달
    assert validate_password_complexity("alllowercase1", db) is not None  # 대문자 없음
    assert validate_password_complexity("ValidPass1", db) is None      # 통과
