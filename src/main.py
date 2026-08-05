import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .auth import RequiresLogin, hash_password
from .database import SessionLocal, engine
from .models import AppSetting, Base, User
from .routers import admin, user
from . import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _seed_defaults()
    scheduler.start()
    yield
    scheduler.stop()


def rename_legacy_deleted_usernames(db):
    """26.6.0 이전 패치에서 소프트 삭제된 계정은 username이 리네임되지 않아
    동일 아이디 재생성이 막혀 있음 — 1회성으로 정리."""
    for u in db.query(User).filter(User.is_active.is_(False)).all():
        if "__deleted_" not in u.username:
            u.username = f"{u.username}__deleted_{u.id}"


def _seed_defaults():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "admin").first():
            db.add(User(
                username=os.getenv("ADMIN_USERNAME", "admin"),
                hashed_password=hash_password(os.getenv("ADMIN_PASSWORD", "admin1234")),
                role="admin",
            ))
        defaults = {
            "retention_days": "30",
            "default_password": "Change1234!",
            "pw_min_length": "8",
            "pw_require_upper": "true",
            "pw_require_number": "true",
            "pw_require_special": "false",
        }
        for key, value in defaults.items():
            if not db.get(AppSetting, key):
                db.add(AppSetting(key=key, value=value))
        rename_legacy_deleted_usernames(db)
        db.commit()
    finally:
        db.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-change-in-production"),
)


@app.middleware("http")
async def no_cache_html(request: Request, call_next):
    response = await call_next(request)
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["Cache-Control"] = "no-store"
    return response


app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(user.router)
app.include_router(admin.router, prefix="/admin")


@app.exception_handler(RequiresLogin)
async def requires_login_handler(request, exc):
    return RedirectResponse("/login", status_code=302)
