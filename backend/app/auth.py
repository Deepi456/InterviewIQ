"""JWT authentication and password hashing helpers."""

import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.database import get_connection

bearer = HTTPBearer(auto_error=False)
_ITERATIONS = 310_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.urlsafe_b64decode(salt), int(iterations))
        return hmac.compare_digest(base64.urlsafe_b64encode(digest).decode(), expected)
    except (ValueError, TypeError):
        return False


def _secret() -> str:
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET must be configured with at least 32 characters")
    return settings.jwt_secret


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return _encode_jwt(payload)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer)):
    if not credentials:
        return None
    try:
        payload = _decode_jwt(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Missing subject")
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired access token") from exc

    conn = get_connection()
    try:
        user = conn.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    finally:
        conn.close()


def require_current_user(user=Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def assert_session_owner(session_id: str, user):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    conn = get_connection()
    try:
        row = conn.execute("SELECT user_id FROM interview_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Interview session not found")
        if row["user_id"] is None:
            conn.execute("UPDATE interview_sessions SET user_id = ? WHERE session_id = ?", (user["id"], session_id))
            conn.commit()
        elif row["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="Interview session not found")
    finally:
        conn.close()


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode_jwt(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64(json.dumps(payload, separators=(",", ":"), default=lambda value: value.timestamp()).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = _b64(hmac.new(_secret().encode(), signing_input, hashlib.sha256).digest())
    return f"{encoded_header}.{encoded_payload}.{signature}"


def _decode_jwt(token: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Malformed token")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    expected = hmac.new(_secret().encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_unb64(parts[2]), expected):
        raise ValueError("Invalid signature")
    payload = json.loads(_unb64(parts[1]))
    if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
        raise ValueError("Expired token")
    return payload
