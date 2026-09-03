"""Authentication endpoints."""

import uuid

import re
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_connection
try:
    from psycopg2 import IntegrityError as PostgresIntegrityError
except ImportError:
    PostgresIntegrityError = None
from sqlite3 import IntegrityError as SqliteIntegrityError
from app.models.auth_models import AuthResponse, LoginRequest, RegisterRequest, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _email(value: str) -> str:
    value = value.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    return value


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(request: RegisterRequest):
    name = request.name.strip()
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name must contain at least 2 characters")
    email = _email(request.email)
    conn = get_connection()
    user_id = str(uuid.uuid4())
    try:
        conn.execute(
            "INSERT INTO users (id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, name, email, hash_password(request.password)),
        )
        conn.commit()
    except tuple(error for error in (SqliteIntegrityError, PostgresIntegrityError) if error) as exc:
        conn.rollback()
        raise HTTPException(status_code=409, detail="An account with that email already exists") from exc
    finally:
        conn.close()
    user = UserResponse(id=user_id, name=name, email=email)
    try:
        token = create_access_token(user_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Authentication is not configured") from exc
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
def login(request: LoginRequest):
    conn = get_connection()
    try:
        user = conn.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (_email(request.email),)).fetchone()
    finally:
        conn.close()
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    try:
        token = create_access_token(user["id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Authentication is not configured") from exc
    return AuthResponse(access_token=token, user=UserResponse(id=user["id"], name=user["name"], email=user["email"]))


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_current_user)):
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return UserResponse(id=user["id"], name=user["name"], email=user["email"])
