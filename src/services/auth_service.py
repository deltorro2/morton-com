"""OAuth2 browser-based authentication service.

Uses ``google_auth_oauthlib.flow.InstalledAppFlow`` for the browser-based
OAuth2 flow and manages token lifecycle (storage, refresh, sign-out).
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from src.errors import AuthenticationError
from src.models import AuthState
from src.models.user_session import UserSession
from src.services.credential_storage import CredentialStorage

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/devstorage.read_write",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Embedded OAuth client configuration for desktop app.
# In production, replace with actual client_id/client_secret from GCP console.
_CLIENT_CONFIG = {
    "installed": {
        "client_id": "REPLACE_WITH_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "REPLACE_WITH_CLIENT_SECRET",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}


class AuthService:
    """Service for OAuth2 authentication with Google."""

    def __init__(
        self,
        credential_storage: CredentialStorage | None = None,
        client_config: dict | None = None,
    ) -> None:
        self._storage = credential_storage or CredentialStorage()
        self._client_config = client_config or _CLIENT_CONFIG
        self._state = AuthState.SIGNED_OUT
        self._current_user: UserSession | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> AuthState:
        """Current authentication state."""
        return self._state

    @property
    def current_user(self) -> UserSession | None:
        """Current authenticated user, or ``None``."""
        return self._current_user

    def sign_in(
        self,
        on_browser_opened: Callable[[], None] | None = None,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Start browser-based sign-in in a background thread."""
        with self._lock:
            if self._state == AuthState.SIGNING_IN:
                raise AuthenticationError(
                    message="Sign-in already in progress",
                    user_message="A sign-in is already in progress.",
                    suggested_action="Wait for the current sign-in to complete.",
                )
            self._state = AuthState.SIGNING_IN

        thread = threading.Thread(
            target=self._run_sign_in,
            args=(on_browser_opened, on_success, on_error),
            daemon=True,
        )
        thread.start()

    def _run_sign_in(
        self,
        on_browser_opened: Callable[[], None] | None,
        on_success: Callable[[UserSession], None] | None,
        on_error: Callable[[Exception], None] | None,
    ) -> None:
        """Execute the OAuth2 flow (runs in background thread)."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_config(
                self._client_config, scopes=SCOPES
            )

            if on_browser_opened:
                on_browser_opened()

            creds = flow.run_local_server(
                port=0,
                prompt="consent",
                access_type="offline",
                success_message=(
                    "Authentication successful! You can close this tab "
                    "and return to Morton."
                ),
            )

            # Fetch user email
            email = self._fetch_email(creds)

            session = UserSession(
                email=email,
                access_token=creds.token,
                refresh_token=creds.refresh_token or "",
                token_expiry=creds.expiry.replace(tzinfo=timezone.utc)
                if creds.expiry
                else datetime.now(timezone.utc),
                scopes=list(creds.scopes or SCOPES),
                signed_in_at=datetime.now(timezone.utc),
            )

            self._storage.save(session)

            with self._lock:
                self._current_user = session
                self._state = AuthState.SIGNED_IN

            logger.info("Signed in as %s", email)
            if on_success:
                on_success(session)

        except Exception as exc:
            with self._lock:
                self._state = AuthState.SIGNED_OUT
            logger.error("Sign-in failed: %s", exc)
            if on_error:
                on_error(exc)

    @staticmethod
    def _fetch_email(creds: object) -> str:
        """Fetch the user's email from the userinfo endpoint."""
        try:
            import google.auth.transport.requests

            from google.oauth2.credentials import Credentials

            if not isinstance(creds, Credentials):
                return "unknown@gmail.com"

            session = google.auth.transport.requests.AuthorizedSession(creds)
            resp = session.get("https://www.googleapis.com/oauth2/v1/userinfo")
            if resp.status_code == 200:
                return resp.json().get("email", "unknown@gmail.com")
        except Exception as exc:
            logger.warning("Could not fetch email: %s", exc)
        return "unknown@gmail.com"

    def sign_out(
        self,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Sign out and clear stored credentials."""
        self._storage.clear()
        with self._lock:
            self._current_user = None
            self._state = AuthState.SIGNED_OUT
        logger.info("Signed out")
        if on_complete:
            on_complete()

    def refresh_token(
        self,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Refresh the access token in a background thread."""
        thread = threading.Thread(
            target=self._run_refresh,
            args=(on_success, on_error),
            daemon=True,
        )
        thread.start()

    def _run_refresh(
        self,
        on_success: Callable[[UserSession], None] | None,
        on_error: Callable[[Exception], None] | None,
    ) -> None:
        """Execute token refresh (runs in background thread)."""
        with self._lock:
            if self._current_user is None:
                if on_error:
                    on_error(
                        AuthenticationError(
                            message="No user session to refresh",
                            user_message="You are not signed in.",
                            suggested_action="Sign in with Google first.",
                        )
                    )
                return
            self._state = AuthState.REFRESHING

        try:
            import google.auth.transport.requests

            from google.oauth2.credentials import Credentials

            creds = Credentials(
                token=self._current_user.access_token,
                refresh_token=self._current_user.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self._client_config["installed"]["client_id"],
                client_secret=self._client_config["installed"]["client_secret"],
                scopes=self._current_user.scopes,
            )
            creds.refresh(google.auth.transport.requests.Request())

            session = UserSession(
                email=self._current_user.email,
                access_token=creds.token,
                refresh_token=creds.refresh_token or self._current_user.refresh_token,
                token_expiry=creds.expiry.replace(tzinfo=timezone.utc)
                if creds.expiry
                else datetime.now(timezone.utc),
                scopes=self._current_user.scopes,
                signed_in_at=self._current_user.signed_in_at,
            )

            self._storage.save(session)

            with self._lock:
                self._current_user = session
                self._state = AuthState.SIGNED_IN

            logger.info("Token refreshed for %s", session.email)
            if on_success:
                on_success(session)

        except Exception as exc:
            with self._lock:
                self._state = AuthState.SIGNED_OUT
                self._current_user = None
            logger.error("Token refresh failed: %s", exc)
            if on_error:
                on_error(exc)

    def load_stored_credentials(self) -> UserSession | None:
        """Load credentials from secure storage on startup."""
        session = self._storage.load()
        if session is None:
            return None

        with self._lock:
            self._current_user = session
            self._state = AuthState.SIGNED_IN

        # Proactive refresh if expiring soon
        if session.needs_refresh:
            logger.info("Stored token expiring soon, refreshing proactively")
            self.refresh_token()

        return session

    def get_credentials(self) -> object:
        """Return a ``google.oauth2.credentials.Credentials`` object.

        Raises ``AuthenticationError`` if not authenticated.
        """
        if self._current_user is None:
            raise AuthenticationError(
                message="Not authenticated",
                user_message="You are not signed in.",
                suggested_action="Sign in with Google to access GCS.",
            )

        from google.oauth2.credentials import Credentials

        return Credentials(
            token=self._current_user.access_token,
            refresh_token=self._current_user.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self._client_config["installed"]["client_id"],
            client_secret=self._client_config["installed"]["client_secret"],
            scopes=self._current_user.scopes,
        )

    def ensure_authenticated(
        self,
        on_authenticated: Callable[[UserSession], None],
        on_sign_in_required: Callable[[], None],
    ) -> None:
        """Check auth state and call appropriate callback."""
        if self._current_user is not None and self._state == AuthState.SIGNED_IN:
            on_authenticated(self._current_user)
        else:
            on_sign_in_required()
