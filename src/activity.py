import json

from .database import SessionLocal
from .models import ActivityLog


def log_event(event_type: str, username: str | None = None, detail: dict | None = None, db=None) -> None:
    entry = ActivityLog(
        event_type=event_type,
        username=username,
        detail=json.dumps(detail or {}, ensure_ascii=False),
    )
    if db is not None:
        db.add(entry)
    else:
        _db = SessionLocal()
        try:
            _db.add(entry)
            _db.commit()
        finally:
            _db.close()
