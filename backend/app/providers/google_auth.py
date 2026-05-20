from __future__ import annotations

from typing import Protocol

from google.auth.transport import requests
from google.oauth2 import id_token

from app.providers.auth import GoogleProfile


class GoogleTokenVerificationError(Exception):
    pass


class GoogleAuthNotConfiguredError(Exception):
    pass


class GoogleIdTokenVerifier(Protocol):
    def verify(self, id_token_value: str) -> GoogleProfile:
        ...


class GoogleOAuthIdTokenVerifier:
    def __init__(self, client_id: str | None) -> None:
        self.client_id = client_id

    def verify(self, id_token_value: str) -> GoogleProfile:
        if not self.client_id:
            raise GoogleAuthNotConfiguredError("Google client id is not configured")
        try:
            payload = id_token.verify_oauth2_token(id_token_value, requests.Request(), self.client_id)
        except ValueError as exc:
            raise GoogleTokenVerificationError("Invalid Google ID token") from exc

        subject = str(payload.get("sub") or "")
        email = str(payload.get("email") or "")
        if not subject or not email:
            raise GoogleTokenVerificationError("Invalid Google ID token")
        return GoogleProfile(
            sub=subject,
            email=email,
            email_verified=payload.get("email_verified") is True
            or str(payload.get("email_verified")).lower() == "true",
            name=str(payload.get("name") or "") or None,
            avatar_url=str(payload.get("picture") or "") or None,
        )
