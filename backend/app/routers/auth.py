"""Auth router — register, login."""

import os
import re
import time
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.dependencies import (
    get_db, get_current_user, hash_password, verify_password, create_access_token, is_admin,
)
from backend.app.models import User
from backend.app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory rate limiter: {ip: [timestamps]}
_rate_window = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
_rate_max = int(os.getenv("RATE_LIMIT_MAX", "10"))         # max requests per window per IP
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_buckets[ip]
    bucket[:] = [t for t in bucket if now - t < _rate_window]
    if len(bucket) >= _rate_max:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
    bucket.append(now)


_COMMON_PASSWORDS = {
    "password", "password123", "12345678", "qwerty123", "admin123",
    "letmein1", "welcome1", "changeme",
}


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")
    if len(password) > 128:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at most 128 characters")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must contain a digit")
    if password.lower() in _COMMON_PASSWORDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password is too common")


_STATES = {"NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"}


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: UserRegister, request: Request, db: Session = Depends(get_db)):
    _check_rate_limit(request)
    _validate_password(body.password)

    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    # New users are always 'registered'. An officer request is captured as a
    # pending request (state + council); an admin approves it later.
    requested_state = requested_council = None
    if body.request_officer:
        state = (body.state or "").strip().upper()
        council = (body.council or "").strip()
        if state not in _STATES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Valid state required for an officer request")
        if not council:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Council name required for an officer request")
        requested_state, requested_council = state, council

    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        role="registered",
        requested_state=requested_state,
        requested_council=requested_council,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, request: Request, db: Session = Depends(get_db)):
    _check_rate_limit(request)

    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    # is_admin + effective role are computed (admin from the ADMIN_EMAILS
    # allow-list). Build the response explicitly — never write the resolved role
    # back onto the ORM object, so admin stays out of the DB.
    from backend.app.dependencies import effective_role
    role = effective_role(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        is_admin=is_admin(user),
        role=role,
        assigned_state=user.assigned_state,
        assigned_council=user.assigned_council,
        officer_request_pending=bool(user.requested_council) and role != "officer",
        requested_state=user.requested_state,
        requested_council=user.requested_council,
    )
