from __future__ import annotations

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Generator, Annotated

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import User, Analysis
from backend.app.models.base import Base
from backend.app.services.identity import parse_report_identity

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./backend/sdg_analyzer.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    logger.warning("JWT_SECRET not set — using insecure default. Set JWT_SECRET env var for production.")
    JWT_SECRET = "dev-secret-change-in-production"

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# Admin accounts (comma-separated emails) may publish/unpublish and upload for
# any council. Read of published results needs no account. See data-contract C#0.
ADMIN_EMAILS = {e.strip().lower() for e in os.getenv("ADMIN_EMAILS", "").split(",") if e.strip()}

security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_analysis_columns()


# New columns added to `analyses` after the table first shipped. create_all does
# not alter existing tables, so add any missing ones and backfill identity from
# the filename. Kept idempotent so it is safe to run on every startup.
_NEW_ANALYSIS_COLUMNS = {
    "lga_code": "VARCHAR(10)",
    "council_name": "VARCHAR(255)",
    "state": "VARCHAR(10)",
    "year": "INTEGER",
    "published": "BOOLEAN NOT NULL DEFAULT 0",
}


def _migrate_analysis_columns() -> None:
    if "sqlite" not in DATABASE_URL:
        return
    insp = inspect(engine)
    if "analyses" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("analyses")}
    missing = {c: ddl for c, ddl in _NEW_ANALYSIS_COLUMNS.items() if c not in existing}
    if not missing:
        return
    with engine.begin() as conn:
        for col, ddl in missing.items():
            conn.execute(text(f"ALTER TABLE analyses ADD COLUMN {col} {ddl}"))
    _backfill_identity()


def _backfill_identity() -> None:
    """Populate council identity for existing rows and publish completed ones so
    the public landing page has data to render immediately."""
    db = SessionLocal()
    try:
        for a in db.query(Analysis).filter(Analysis.council_name.is_(None)).all():
            ident = parse_report_identity(a.original_filename)
            a.council_name = ident["council_name"]
            a.state = ident["state"]
            a.year = ident["year"]
            if a.status == "completed":
                a.published = True
        db.commit()
    finally:
        db.close()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def is_admin(user: User) -> bool:
    return user.email.lower() in ADMIN_EMAILS


def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
