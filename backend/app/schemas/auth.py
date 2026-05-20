from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AuthProvider = Literal["google"]


class PublicUser(BaseModel):
    user_id: str
    email: str
    name: str
    avatar_url: str | None = None
    provider: AuthProvider = "google"


class AuthSession(BaseModel):
    token: str
    expires_at: datetime


class AuthUserRecord(PublicUser):
    google_sub: str
    created_at: datetime
    updated_at: datetime


class AuthSessionRecord(BaseModel):
    session_id: str
    user_id: str
    token_hash: str
    created_at: datetime
    expires_at: datetime


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=20)


class AuthResponse(BaseModel):
    user: PublicUser
    session: AuthSession
