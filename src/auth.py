import bcrypt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import AppSetting, User


class RequiresLogin(Exception):
    pass


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise RequiresLogin()
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise RequiresLogin()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return user


def validate_password_complexity(password: str, db: Session) -> str | None:
    """Return error message if password fails complexity rules, else None."""
    def _val(key: str, default: str) -> str:
        s = db.get(AppSetting, key)
        return s.value if s else default

    min_len = int(_val("pw_min_length", "8"))
    require_upper = _val("pw_require_upper", "true") == "true"
    require_number = _val("pw_require_number", "true") == "true"
    require_special = _val("pw_require_special", "false") == "true"

    if len(password) < min_len:
        return f"비밀번호는 최소 {min_len}자 이상이어야 합니다."
    if require_upper and not any(c.isupper() for c in password):
        return "대문자를 포함해야 합니다."
    if require_number and not any(c.isdigit() for c in password):
        return "숫자를 포함해야 합니다."
    if require_special and not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        return "특수문자를 포함해야 합니다."
    return None
