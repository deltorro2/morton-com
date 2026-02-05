"""User session data model.

Tracks Google Cloud OAuth2 session state including tokens, expiry, and
convenience properties for authentication status checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class UserSession:
    """An authenticated Google Cloud user session.

    Parameters
    ----------
    email:
        Google account email address.
    access_token:
        OAuth2 access token.
    refresh_token:
        OAuth2 refresh token for obtaining new access tokens.
    token_expiry:
        UTC timestamp when the access token expires.
    scopes:
        OAuth2 scopes granted to this session.
    signed_in_at:
        UTC timestamp when the user signed in.
    """

    email: str
    access_token: str
    refresh_token: str
    token_expiry: datetime
    scopes: list[str] = field(default_factory=list)
    signed_in_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_authenticated(self) -> bool:
        """``True`` when an access token is present."""
        return bool(self.access_token)

    @property
    def is_expired(self) -> bool:
        """``True`` when the access token has expired."""
        return self.token_expiry < datetime.now(timezone.utc)

    @property
    def needs_refresh(self) -> bool:
        """``True`` when the token will expire within 5 minutes."""
        return self.token_expiry < datetime.now(timezone.utc) + timedelta(minutes=5)

    @property
    def display_name(self) -> str:
        """Email prefix before the ``@`` sign."""
        return self.email.split("@", 1)[0]
