from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    # Optional: request the council-officer role. When true, state + council are
    # required and stored as a pending request for an admin to approve.
    request_officer: bool = False
    state: Optional[str] = None
    council: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime
    is_admin: bool = False
    role: str = "registered"          # effective tier: registered | officer | admin
    assigned_state: Optional[str] = None
    assigned_council: Optional[str] = None
    officer_request_pending: bool = False
    requested_state: Optional[str] = None
    requested_council: Optional[str] = None

    model_config = {"from_attributes": True}
