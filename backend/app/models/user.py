import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Optional profile captured at registration.
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Role tiers: 'registered' (default — read + export) or 'officer' (may upload
    # reports for their assigned council). 'admin' is NOT stored here — it is the
    # ADMIN_EMAILS allow-list, so a DB write can never escalate to admin.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="registered")
    # Set on approval; officer uploads must match this council.
    assigned_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    assigned_council: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Pending officer request captured at registration; cleared on approve/deny.
    requested_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    requested_council: Mapped[str | None] = mapped_column(String(255), nullable=True)

    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="user", cascade="all, delete-orphan"
    )
