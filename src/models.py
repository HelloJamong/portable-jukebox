from datetime import datetime, timedelta, timezone

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database import Base

KST = timezone(timedelta(hours=9))


def _now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user")  # "admin" | "user"
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now_kst)
    logs = relationship("DownloadLog", back_populates="user")


class DownloadLog(Base):
    __tablename__ = "download_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String, nullable=False)
    title = Column(String)
    filename = Column(String)
    format = Column(String)   # "mp4" | "mp3"
    quality = Column(String)
    file_size = Column(BigInteger)
    status = Column(String, default="pending")  # "pending" | "downloading" | "done" | "error"
    downloaded_at = Column(DateTime, default=_now_kst)
    deleted_at = Column(DateTime, nullable=True)
    user = relationship("User", back_populates="logs")


class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)


class RememberToken(Base):
    __tablename__ = "remember_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=_now_kst)


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    username = Column(String)
    detail = Column(String)  # JSON
    created_at = Column(DateTime, default=_now_kst)
