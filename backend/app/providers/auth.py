from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from app.schemas.auth import AuthSession, AuthSessionRecord, AuthUserRecord, PublicUser


class GoogleProfile(BaseModel):
    sub: str
    email: str
    email_verified: bool
    name: str | None = None
    avatar_url: str | None = None


class AuthStore:
    def __init__(self, store_path: Path, session_max_age_days: int) -> None:
        self.store_path = store_path
        self.session_max_age_days = session_max_age_days
        self.users: list[AuthUserRecord] = []
        self.sessions: list[AuthSessionRecord] = []
        self._load()
        self._prune_expired_sessions()

    def upsert_google_user(self, profile: GoogleProfile) -> AuthUserRecord:
        if not profile.email_verified:
            raise ValueError("Google profile email must be verified")

        email = profile.email.strip().lower()
        now = self._now()
        user_by_sub = self._find_user_by_google_sub(profile.sub)
        user_by_email = self._find_user_by_email(email)
        if user_by_sub is not None and user_by_email is not None and user_by_sub.user_id != user_by_email.user_id:
            raise ValueError("Google profile email belongs to another user")

        user = user_by_sub or user_by_email
        if user is not None:
            updated = user.model_copy(
                update={
                    "google_sub": profile.sub,
                    "email": email,
                    "name": profile.name or user.name,
                    "avatar_url": profile.avatar_url or user.avatar_url,
                    "updated_at": now,
                }
            )
            self.users = [updated if candidate.user_id == user.user_id else candidate for candidate in self.users]
            self._save()
            return updated

        created = AuthUserRecord(
            user_id=f"user_{uuid4().hex[:16]}",
            google_sub=profile.sub,
            email=email,
            name=profile.name or email.split("@")[0] or "Google User",
            avatar_url=profile.avatar_url,
            provider="google",
            created_at=now,
            updated_at=now,
        )
        self.users.append(created)
        self._save()
        return created

    def create_session(self, user_id: str) -> AuthSession:
        if not any(user.user_id == user_id for user in self.users):
            raise ValueError(f"Unknown auth user: {user_id}")

        self._prune_expired_sessions()
        now = self._now()
        expires_at = now + timedelta(days=self.session_max_age_days)
        token = secrets.token_urlsafe(32)
        self.sessions.append(
            AuthSessionRecord(
                session_id=f"session_{uuid4().hex[:16]}",
                user_id=user_id,
                token_hash=self._hash_token(token),
                created_at=now,
                expires_at=expires_at,
            )
        )
        self._save()
        return AuthSession(token=token, expires_at=expires_at)

    def get_user_by_token(self, token: str | None) -> PublicUser | None:
        if not token:
            return None
        self._prune_expired_sessions()
        token_hash = self._hash_token(token)
        session = next((candidate for candidate in self.sessions if self._token_hash_matches(candidate, token_hash)), None)
        if session is None:
            return None
        user = next((candidate for candidate in self.users if candidate.user_id == session.user_id), None)
        return self._public_user(user) if user else None

    def destroy_session(self, token: str | None) -> None:
        if not token:
            return
        token_hash = self._hash_token(token)
        next_sessions = [session for session in self.sessions if not self._token_hash_matches(session, token_hash)]
        if len(next_sessions) == len(self.sessions):
            return
        self.sessions = next_sessions
        self._save()

    def _find_user_by_google_sub(self, google_sub: str) -> AuthUserRecord | None:
        return next((user for user in self.users if user.google_sub == google_sub), None)

    def _find_user_by_email(self, email: str) -> AuthUserRecord | None:
        return next((user for user in self.users if user.email == email), None)

    def _load(self) -> None:
        if not self.store_path.exists():
            return
        data = json.loads(self.store_path.read_text(encoding="utf-8"))
        self.users = [AuthUserRecord.model_validate(item) for item in data.get("users", [])]
        self.sessions = [AuthSessionRecord.model_validate(item) for item in data.get("sessions", [])]

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "users": [user.model_dump(mode="json") for user in self.users],
            "sessions": [session.model_dump(mode="json") for session in self.sessions],
        }
        temp_path = self.store_path.with_name(f".{self.store_path.name}.{uuid4().hex}.tmp")
        try:
            temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            temp_path.replace(self.store_path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def _prune_expired_sessions(self) -> None:
        now = self._now()
        next_sessions = [session for session in self.sessions if session.expires_at > now]
        if len(next_sessions) == len(self.sessions):
            return
        self.sessions = next_sessions
        self._save()

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _token_hash_matches(session: AuthSessionRecord, token_hash: str) -> bool:
        return hmac.compare_digest(session.token_hash, token_hash)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _public_user(user: AuthUserRecord | None) -> PublicUser | None:
        if user is None:
            return None
        return PublicUser(
            user_id=user.user_id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            provider=user.provider,
        )
