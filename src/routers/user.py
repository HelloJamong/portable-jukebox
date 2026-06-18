import hashlib
import os
import secrets
from datetime import timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from markupsafe import escape
from sqlalchemy.orm import Session

from .. import downloader
from ..activity import log_event
from ..auth import get_current_user, hash_password, validate_password_complexity, verify_password
from ..database import get_db
from ..models import DownloadLog, RememberToken, User
from ..models import _now_kst

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
templates.env.globals["app_version"] = os.getenv("APP_VERSION", "dev")

_COOKIE = "jb_remember"
_TOKEN_DAYS = 30


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _set_remember_cookie(response: Response, raw: str) -> None:
    response.set_cookie(_COOKIE, raw, max_age=_TOKEN_DAYS * 86400, httponly=True, samesite="lax")


def _clear_remember_cookie(response: Response) -> None:
    response.delete_cookie(_COOKIE)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user_id"):
        return RedirectResponse("/")

    raw = request.cookies.get(_COOKIE)
    if raw:
        token = db.query(RememberToken).filter(
            RememberToken.token_hash == _hash(raw),
            RememberToken.expires_at > _now_kst(),
        ).first()
        if token:
            user = db.get(User, token.user_id)
            if user and user.is_active:
                request.session["user_id"] = user.id
                log_event("login_ok", username=user.username,
                          detail={"ip": request.client.host, "method": "auto"}, db=db)
                db.commit()
                dest = "/admin/users" if user.role == "admin" else "/"
                return RedirectResponse(dest, status_code=302)
        # 만료 또는 무효 토큰 → 쿠키 삭제
        resp = templates.TemplateResponse(request, "login.html")
        _clear_remember_cookie(resp)
        return resp

    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    auto_login: str = Form(""),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username, User.is_active.is_(True)).first()
    if not user or not verify_password(password, user.hashed_password):
        log_event("login_fail", username=username, detail={"ip": request.client.host}, db=db)
        db.commit()
        return templates.TemplateResponse(
            request, "login.html",
            {"error": "아이디 또는 비밀번호가 올바르지 않습니다."},
            status_code=401,
        )

    log_event("login_ok", username=user.username, detail={"ip": request.client.host}, db=db)
    db.commit()
    request.session["user_id"] = user.id

    if user.must_change_password:
        return RedirectResponse("/change-password", status_code=303)

    dest = "/admin/users" if user.role == "admin" else "/"

    if auto_login:
        raw = secrets.token_urlsafe(32)
        db.add(RememberToken(
            user_id=user.id,
            token_hash=_hash(raw),
            expires_at=_now_kst() + timedelta(days=_TOKEN_DAYS),
        ))
        db.commit()
        resp = RedirectResponse(dest, status_code=303)
        _set_remember_cookie(resp, raw)
        return resp

    return RedirectResponse(dest, status_code=303)


@router.get("/logout")
@router.post("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if user_id:
        user = db.get(User, user_id)
        if user:
            log_event("logout", username=user.username, db=db)
        raw = request.cookies.get(_COOKIE)
        if raw:
            db.query(RememberToken).filter(
                RememberToken.token_hash == _hash(raw)
            ).delete()
        db.commit()
    request.session.clear()
    resp = RedirectResponse("/login", status_code=302)
    _clear_remember_cookie(resp)
    return resp


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(request, "change_password.html", {"user": user})


@router.post("/change-password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    def _err(msg: str):
        return templates.TemplateResponse(
            request, "change_password.html", {"user": user, "error": msg}, status_code=400
        )

    if not verify_password(current_password, user.hashed_password):
        return _err("현재 비밀번호가 올바르지 않습니다.")
    if new_password != confirm_password:
        return _err("새 비밀번호가 일치하지 않습니다.")
    err = validate_password_complexity(new_password, db)
    if err:
        return _err(err)

    user.hashed_password = hash_password(new_password)
    user.must_change_password = False
    log_event("password_change", username=user.username, db=db)
    db.commit()
    redirect = "/admin/users" if user.role == "admin" else "/"
    return RedirectResponse(redirect, status_code=303)


@router.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "admin":
        return RedirectResponse("/admin/users", status_code=302)
    logs = (
        db.query(DownloadLog)
        .filter(DownloadLog.user_id == user.id, DownloadLog.deleted_at.is_(None))
        .order_by(DownloadLog.downloaded_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(request, "dashboard.html", {"user": user, "logs": logs})


@router.post("/download", response_class=HTMLResponse)
async def start_download(
    request: Request,
    url: str = Form(""),
    format: str = Form("mp4"),
    quality: str = Form("1080p (FHD)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    url = url.strip()
    if not url:
        return HTMLResponse(
            '<div id="progress-container" class="text-sm text-red-500 text-center py-2">'
            '<i class="fa-solid fa-circle-exclamation mr-1.5"></i>URL을 입력해주세요.</div>'
        )

    log = DownloadLog(user_id=user.id, url=url, format=format, quality=quality, status="pending")
    db.add(log)
    db.commit()

    task_id = await downloader.enqueue(url, format, quality, log.id, user.username)
    return HTMLResponse(_progress_html(task_id, 0, "pending"))


@router.get("/download/status/{task_id}", response_class=HTMLResponse)
async def download_status(
    task_id: str,
    request: Request,
    poll: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = downloader.TASKS.get(task_id)
    if not task:
        return HTMLResponse(
            '<div class="text-sm text-red-500 text-center py-2">'
            "작업을 찾을 수 없습니다.</div>"
        )

    status = task["status"]
    progress = task["progress"]

    if status in ("pending", "downloading"):
        return HTMLResponse(_progress_html(task_id, progress, status, poll))

    logs = (
        db.query(DownloadLog)
        .filter(DownloadLog.user_id == user.id, DownloadLog.deleted_at.is_(None))
        .order_by(DownloadLog.downloaded_at.desc())
        .limit(20)
        .all()
    )
    history_oob = (
        '<div id="history-list" class="space-y-3" hx-swap-oob="outerHTML">'
        + templates.env.get_template("partials/history_list.html").render(logs=logs)
        + "</div>"
    )

    if status == "done":
        return HTMLResponse(
            '<div class="flex items-center justify-center gap-2 py-3 text-sm text-green-600">'
            '<i class="fa-solid fa-circle-check"></i><span>다운로드가 완료되었습니다.</span>'
            f"</div>{history_oob}"
        )

    msg = escape(task.get("error_display", task.get("error", "알 수 없는 오류")))
    return HTMLResponse(
        '<div class="flex items-center justify-center gap-2 py-3 text-sm text-red-500">'
        f'<i class="fa-solid fa-circle-exclamation"></i><span>{msg}</span>'
        f"</div>{history_oob}"
    )


@router.get("/download/history", response_class=HTMLResponse)
async def download_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    logs = (
        db.query(DownloadLog)
        .filter(DownloadLog.user_id == user.id, DownloadLog.deleted_at.is_(None))
        .order_by(DownloadLog.downloaded_at.desc())
        .limit(20)
        .all()
    )
    history_html = templates.env.get_template("partials/history_list.html").render(logs=logs)
    return HTMLResponse(f'<div id="history-list" class="space-y-3">{history_html}</div>')


@router.delete("/download/{log_id}", response_class=HTMLResponse)
async def delete_download(
    log_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    log = db.query(DownloadLog).filter(
        DownloadLog.id == log_id,
        DownloadLog.user_id == user.id,
        DownloadLog.deleted_at.is_(None),
    ).first()
    if not log:
        raise HTTPException(status_code=404)
    if log.filename:
        path = downloader.DOWNLOAD_DIR / log.filename
        if path.exists():
            path.unlink()
    log.deleted_at = _now_kst()
    log_event("manual_delete", username=user.username,
              detail={"filename": log.filename}, db=db)
    db.commit()
    return HTMLResponse("")


@router.get("/files/{filename}")
async def serve_file(
    filename: str,
    user: User = Depends(get_current_user),
):
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="잘못된 파일명입니다.")
    path = downloader.DOWNLOAD_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


def _progress_html(task_id: str, progress: int, status: str, poll: int = 0) -> str:
    # ponytail: stop polling after 10 min (300 × 2s) to prevent infinite loop on hung tasks
    if poll >= 300:
        return (
            '<div class="flex items-center justify-center gap-2 py-3 text-sm text-red-500">'
            '<i class="fa-solid fa-circle-exclamation"></i><span>다운로드 시간이 초과되었습니다. 다시 시도해주세요.</span>'
            "</div>"
        )
    label = "다운로드 준비 중..." if (status == "pending" or progress == 0) else "다운로드 진행 중..."
    pct_label = f"{progress}%" if progress > 0 else "..."
    if progress > 0:
        bar = (
            f'<div class="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">'
            f'<div class="h-full bg-neutral-900 rounded-full transition-all" style="width:{progress}%"></div>'
            f'</div>'
        )
    else:
        bar = (
            '<div class="w-full h-2 bg-neutral-100 rounded-full overflow-hidden">'
            '<div class="h-full bg-neutral-400 rounded-full animate-pulse w-full"></div>'
            '</div>'
        )
    return (
        f'<div hx-get="/download/status/{task_id}?poll={poll + 1}"'
        f' hx-trigger="every 2s" hx-swap="outerHTML">'
        f'<div class="flex justify-between text-xs text-neutral-500 mb-1.5">'
        f"<span>{label}</span><span>{pct_label}</span></div>"
        f"{bar}</div>"
    )
