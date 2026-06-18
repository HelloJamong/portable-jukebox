import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..activity import log_event
from ..auth import hash_password, require_admin
from ..database import get_db
from ..models import ActivityLog, AppSetting, DownloadLog, User

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
templates.env.filters["fromjson"] = json.loads
templates.env.globals["app_version"] = os.getenv("APP_VERSION", "dev")


@router.get("/", response_class=HTMLResponse)
async def admin_index(admin: User = Depends(require_admin)):
    return RedirectResponse("/admin/users")


@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    users = db.query(User).filter(User.is_active == True).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(request, "admin/users.html", {"user": admin, "users": users})


@router.post("/users")
async def create_user(
    request: Request,
    username: str = Form(...),
    role: str = Form("user"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == username).first():
        users = db.query(User).filter(User.is_active == True).order_by(User.created_at.desc()).all()
        return templates.TemplateResponse(
            request, "admin/users.html",
            {"user": admin, "users": users, "error": "이미 존재하는 아이디입니다."},
            status_code=400,
        )
    default_pw = db.get(AppSetting, "default_password")
    password = default_pw.value if default_pw else "Change1234!"
    db.add(User(username=username, hashed_password=hash_password(password), role=role, must_change_password=True))
    log_event("user_create", username=admin.username, detail={"target": username, "role": role}, db=db)
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)


@router.delete("/users/{user_id}", response_class=HTMLResponse)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.get(User, user_id)
    if target and target.id != admin.id:
        target.is_active = False
        log_event("user_delete", username=admin.username, detail={"target": target.username}, db=db)
        db.commit()
    return HTMLResponse("")  # HTMX removes the row via hx-swap="outerHTML"


_CATEGORY_TYPES = {
    "auth": ["login_ok", "login_fail", "logout", "password_change"],
    "download": ["download_done", "download_fail"],
    "account": ["user_create", "user_delete"],
    "system": ["settings_change", "auto_delete"],
}

@router.get("/logs", response_class=HTMLResponse)
async def admin_logs(
    request: Request,
    category: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if per_page not in (20, 30, 50, 100):
        per_page = 30
    q = db.query(ActivityLog)
    if category in _CATEGORY_TYPES:
        q = q.filter(ActivityLog.event_type.in_(_CATEGORY_TYPES[category]))
    total = q.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = min(page, total_pages)
    logs = q.order_by(ActivityLog.created_at.desc()).limit(per_page).offset((page - 1) * per_page).all()
    return templates.TemplateResponse(request, "admin/logs.html", {
        "user": admin, "logs": logs,
        "current_category": category, "total": total,
        "page": page, "per_page": per_page, "total_pages": total_pages,
    })


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    def _val(key: str, default: str) -> str:
        s = db.get(AppSetting, key)
        return s.value if s else default

    return templates.TemplateResponse(
        request, "admin/settings.html",
        {
            "user": admin,
            "retention_days": _val("retention_days", "30"),
            "default_password": _val("default_password", "Change1234!"),
            "pw_min_length": _val("pw_min_length", "8"),
            "pw_require_upper": _val("pw_require_upper", "true"),
            "pw_require_number": _val("pw_require_number", "true"),
            "pw_require_special": _val("pw_require_special", "false"),
        },
    )


@router.post("/settings")
async def update_settings(
    retention_days: int = Form(...),
    default_password: str = Form(...),
    pw_min_length: int = Form(...),
    pw_require_upper: str = Form("false"),
    pw_require_number: str = Form("false"),
    pw_require_special: str = Form("false"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    updates = {
        "retention_days": str(retention_days),
        "default_password": default_password,
        "pw_min_length": str(pw_min_length),
        "pw_require_upper": pw_require_upper,
        "pw_require_number": pw_require_number,
        "pw_require_special": pw_require_special,
    }
    changed = {}
    for key, value in updates.items():
        s = db.get(AppSetting, key)
        if s:
            if s.value != value:
                changed[key] = {"from": s.value, "to": value}
            s.value = value
        else:
            db.add(AppSetting(key=key, value=value))
            changed[key] = {"from": None, "to": value}
    if changed:
        log_event("settings_change", username=admin.username, detail={"changed": changed}, db=db)
    db.commit()
    return RedirectResponse("/admin/settings", status_code=303)
