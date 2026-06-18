import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler

from .activity import log_event
from .database import SessionLocal
from .models import AppSetting, DownloadLog

KST = timezone(timedelta(hours=9))
logger = logging.getLogger(__name__)
_scheduler = BackgroundScheduler()


def _now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def _delete_expired_files() -> None:
    db = SessionLocal()
    try:
        retention = db.get(AppSetting, "retention_days")
        days = int(retention.value) if retention else 0
        if days == 0:
            return

        cutoff = _now_kst() - timedelta(days=days)
        expired = (
            db.query(DownloadLog)
            .filter(DownloadLog.deleted_at.is_(None), DownloadLog.downloaded_at < cutoff)
            .all()
        )

        for log in expired:
            if log.filename:
                path = Path(os.getenv("DOWNLOAD_DIR", "./downloads")) / log.filename
                if path.exists():
                    path.unlink()
                    logger.info("deleted %s", path)
            log.deleted_at = _now_kst()
            log_event("auto_delete", detail={
                "filename": log.filename,
                "reason": f"보관 기간 {days}일 초과",
                "downloaded_at": log.downloaded_at.strftime("%Y-%m-%d %H:%M") if log.downloaded_at else None,
            }, db=db)

        if expired:
            db.commit()
            logger.info("auto-delete: removed %d file(s)", len(expired))
    finally:
        db.close()


def start() -> None:
    _scheduler.add_job(_delete_expired_files, "cron", hour=0, minute=0, id="auto_delete")
    _scheduler.start()
    logger.info("scheduler started")


def stop() -> None:
    _scheduler.shutdown(wait=False)
