from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Callable
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .database import get_db
from .models import User, UserRole


PASSWORD_ITERATIONS = 260000
TOKEN_VERSION = "v1"
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    salt = secrets.token_urlsafe(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PASSWORD_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        PASSWORD_ITERATIONS, salt, _b64encode(digest)
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations_text),
        )
        return hmac.compare_digest(_b64encode(digest), expected)
    except (ValueError, TypeError):
        return False


def create_access_token(user: User, settings: Settings) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "iat": now,
        "exp": now + settings.access_token_expire_minutes * 60,
        "ver": TOKEN_VERSION,
    }
    payload_part = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(payload_part, settings.secret_key)
    return "{}.{}".format(payload_part, signature)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    expected = _sign(payload_part, settings.secret_key)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        payload = json.loads(_b64decode(payload_part))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return payload


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def create_user(
    db: Session, username: str, password: str, role: str = UserRole.developer.value
) -> User:
    if role not in {item.value for item in UserRole}:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = db.scalar(select(User).where(User.username == username))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_access_token(credentials.credentials, settings)
    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_roles(*roles: str) -> Callable[[User], User]:
    allowed = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


def can_view_all_tasks(user: User) -> bool:
    return user.role in {UserRole.admin.value, UserRole.reviewer.value}


def can_access_task(user: User, task_user_id: Optional[int]) -> bool:
    return can_view_all_tasks(user) or task_user_id == user.id


def can_manage_issue(user: User, task_user_id: Optional[int]) -> bool:
    return user.role in {UserRole.admin.value, UserRole.reviewer.value} or task_user_id == user.id


def can_manage_test_case(user: User, task_user_id: Optional[int]) -> bool:
    return user.role in {
        UserRole.admin.value,
        UserRole.reviewer.value,
        UserRole.tester.value,
    } or task_user_id == user.id


def _sign(payload_part: str, secret_key: str) -> str:
    digest = hmac.new(
        secret_key.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256
    ).digest()
    return _b64encode(digest)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))
