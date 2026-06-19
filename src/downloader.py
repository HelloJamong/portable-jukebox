import asyncio
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yt_dlp

from .activity import log_event
from .database import SessionLocal
from .models import DownloadLog

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "./downloads"))

_executor = ThreadPoolExecutor(max_workers=3)
_semaphore = threading.Semaphore(3)

TASKS: dict[str, dict] = {}

_MP4_HEIGHTS = {"1080p (FHD)": 1080, "720p (HD)": 720, "480p": 480, "360p": 360}
_MP3_KBPS = {"320kbps": "320", "192kbps": "192", "128kbps": "128", "96kbps": "96"}


def _classify_error(exc: Exception) -> tuple[str, str]:
    """Returns (display_message, error_type) for activity log."""
    msg = str(exc).lower()
    if "is not a valid url" in msg or "invalid url" in msg or "unsupported url" in msg:
        return "잘못된 URL", "invalid_url"
    if "private video" in msg or "members only" in msg or "member-only" in msg:
        return "비공개/멤버십 전용 영상", "private"
    if "sign in" in msg or "login required" in msg:
        return "로그인이 필요한 영상", "login_required"
    if "http error 403" in msg or "403: forbidden" in msg:
        return "접근 거부 (403 Forbidden)", "forbidden"
    if "http error 404" in msg or "404" in msg:
        return "영상 없음 (삭제됐거나 존재하지 않음)", "not_found"
    if "copyright" in msg:
        return "저작권으로 인해 차단된 영상", "copyright"
    if "age" in msg and ("restricted" in msg or "limit" in msg):
        return "연령 제한 영상", "age_restricted"
    if "urlopen error" in msg or "connection" in msg or "network" in msg or "timed out" in msg or "errno" in msg:
        return "네트워크 오류 (연결 실패 또는 시간 초과)", "network_error"
    if "ffmpeg" in msg:
        return "FFmpeg 처리 오류", "ffmpeg_error"
    return f"다운로드 오류: {str(exc)[:120]}", "unknown"


def _make_opts(fmt: str, quality: str, task_id: str) -> dict:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    def hook(d: dict) -> None:
        if d["status"] == "downloading":
            pct_str = d.get("_percent_str", "").strip().rstrip("%")
            try:
                new_progress = min(99, int(float(pct_str)))
            except (ValueError, TypeError):
                total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                done = d.get("downloaded_bytes", 0)
                new_progress = int(done / total * 100) if total else 0
            # ponytail: max() prevents progress jumping backward when yt-dlp resets per stream
            TASKS[task_id]["progress"] = max(TASKS[task_id]["progress"], new_progress)
            TASKS[task_id]["status"] = "downloading"

    ffmpeg_path = os.getenv("FFMPEG_LOCATION", "ffmpeg")
    base: dict = {
        "outtmpl": str(DOWNLOAD_DIR / "%(title)s.%(ext)s"),
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": ffmpeg_path,
    }

    if fmt == "mp4":
        h = _MP4_HEIGHTS.get(quality, 1080)
        base["format"] = (
            f"bestvideo[height<={h}][ext=mp4]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={h}]+bestaudio/best[height<={h}]"
        )
        base["merge_output_format"] = "mp4"
    else:
        base["format"] = "bestaudio/best"
        base["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": _MP3_KBPS.get(quality, "192"),
        }]

    return base


def _run(task_id: str, url: str, fmt: str, quality: str, log_id: int, username: str) -> None:
    with _semaphore:
        db = SessionLocal()
        try:
            opts = _make_opts(fmt, quality, task_id)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", url)
                out = Path(ydl.prepare_filename(info))
                if fmt == "mp3":
                    out = out.with_suffix(".mp3")

            file_size = out.stat().st_size if out.exists() else None

            log = db.get(DownloadLog, log_id)
            if log:
                log.status = "done"
                log.title = title
                log.filename = out.name
                log.file_size = file_size
            log_event("download_done", username=username, detail={
                "url": url, "title": title, "filename": out.name,
                "format": fmt, "quality": quality,
            }, db=db)
            db.commit()
            TASKS[task_id].update(
                {"status": "done", "progress": 100, "title": title, "filename": str(out)}
            )
            threading.Timer(600, TASKS.pop, args=(task_id, None)).start()

        except Exception as exc:
            display_msg, error_type = _classify_error(exc)
            TASKS[task_id].update({
                "status": "error",
                "error": str(exc),
                "error_display": display_msg,
            })
            threading.Timer(600, TASKS.pop, args=(task_id, None)).start()
            log = db.get(DownloadLog, log_id)
            if log:
                log.status = "error"
            log_event("download_fail", username=username, detail={
                "url": url, "error_type": error_type,
                "error_display": display_msg, "error_raw": str(exc)[:500],
            }, db=db)
            db.commit()
        finally:
            db.close()


async def enqueue(url: str, fmt: str, quality: str, log_id: int, username: str = "") -> str:
    task_id = str(uuid.uuid4())
    TASKS[task_id] = {"status": "pending", "progress": 0, "title": None, "filename": None, "error": None}
    asyncio.get_running_loop().run_in_executor(_executor, _run, task_id, url, fmt, quality, log_id, username)
    return task_id
