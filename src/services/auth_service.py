"""Authentication service using browser-based OAuth2 flow.

Uses google_auth_oauthlib to open a browser for user authentication.
No gcloud CLI required - authenticates directly via browser.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.errors import AuthenticationError
from src.models import AuthState
from src.models.user_session import UserSession
from src.services.credential_storage import CredentialStorage

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/devstorage.read_write",
    "https://www.googleapis.com/auth/cloud-platform",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

# Default OAuth2 client config path (user can place their own here)
DEFAULT_CLIENT_SECRETS_PATH = Path.home() / ".config" / "morton" / "client_secrets.json"


class AuthService:
    """Service for browser-based OAuth2 authentication."""

    def __init__(
        self,
        credential_storage: CredentialStorage | None = None,
        client_config: dict | None = None,
        client_secrets_path: Path | None = None,
    ) -> None:
        """Initialize AuthService.

        Args:
            credential_storage: Storage for persisting credentials.
            client_config: OAuth2 client configuration dict.
            client_secrets_path: Path to client_secrets.json file.
        """
        self._storage = credential_storage or CredentialStorage()
        self._client_config = client_config
        self._client_secrets_path = client_secrets_path or DEFAULT_CLIENT_SECRETS_PATH
        self._state = AuthState.SIGNED_OUT
        self._current_user: UserSession | None = None
        self._credentials: object | None = None
        self._lock = threading.Lock()

    @property
    def state(self) -> AuthState:
        """Current authentication state."""
        return self._state

    @property
    def current_user(self) -> UserSession | None:
        """Current authenticated user, or ``None``."""
        return self._current_user

    def _get_client_config(self) -> dict:
        """Get OAuth2 client configuration.

        Returns client_config if provided, otherwise loads from file.
        Raises AuthenticationError if no config available.
        """
        if self._client_config:
            return self._client_config

        if self._client_secrets_path.exists():
            try:
                with open(self._client_secrets_path) as f:
                    return json.load(f)
            except Exception as exc:
                raise AuthenticationError(
                    message=f"Failed to load client secrets: {exc}",
                    user_message="Could not load OAuth2 configuration.",
                    suggested_action=f"Check the file at {self._client_secrets_path}",
                ) from exc

        raise AuthenticationError(
            message="No OAuth2 client configuration found",
            user_message="OAuth2 client credentials not configured.",
            suggested_action=(
                f"Create a client_secrets.json file at:\n"
                f"{self._client_secrets_path}\n\n"
                "Get credentials from Google Cloud Console:\n"
                "1. Go to APIs & Services > Credentials\n"
                "2. Create OAuth 2.0 Client ID (Desktop app)\n"
                "3. Download JSON and save to the path above"
            ),
        )

    def sign_in(
        self,
        on_browser_opened: Callable[[], None] | None = None,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Start browser-based OAuth2 sign-in flow in a background thread."""
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
        """Execute OAuth2 browser flow (runs in background thread)."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            # Get client configuration
            client_config = self._get_client_config()

            # Create OAuth2 flow
            flow = InstalledAppFlow.from_client_config(
                client_config,
                scopes=SCOPES,
            )

            # Notify that browser will open
            if on_browser_opened:
                on_browser_opened()

            # Run local server for OAuth2 callback (opens browser)
            credentials = flow.run_local_server(
                port=0,  # Use any available port
                prompt="consent",
                success_message="Authentication successful! You can close this window.",
                open_browser=True,
            )

            # Get user email
            email = self._fetch_email(credentials)

            # Store credentials
            self._credentials = credentials

            # Handle expiry
            expiry = credentials.expiry
            if expiry is None:
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            elif expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            session = UserSession(
                email=email,
                access_token=credentials.token or "",
                refresh_token=credentials.refresh_token or "",
                token_expiry=expiry,
                scopes=list(SCOPES),
                signed_in_at=datetime.now(timezone.utc),
            )

            self._storage.save(session)

            with self._lock:
                self._current_user = session
                self._state = AuthState.SIGNED_IN

            logger.info("Signed in as %s", email)
            if on_success:
                on_success(session)

        except AuthenticationError as exc:
            # Handle our own errors
            with self._lock:
                self._state = AuthState.SIGNED_OUT
            logger.error("Sign-in failed: %s", exc)
            if on_error:
                on_error(exc)
            return

        except Exception as exc:
            with self._lock:
                self._state = AuthState.SIGNED_OUT
            logger.error("Sign-in failed: %s", exc)

            error = AuthenticationError(
                message=f"OAuth2 sign-in failed: {exc}",
                user_message="Sign-in failed.",
                suggested_action="Please try again or check your internet connection.",
                technical_detail=str(exc),
            )

            if on_error:
                on_error(error)

    @staticmethod
    def _fetch_email(credentials: object) -> str:
        """Fetch the user's email from credentials or userinfo endpoint."""
        # Try id_token first (contains email for OAuth2 flow)
        id_token = getattr(credentials, "id_token", None)
        if id_token:
            try:
                import google.oauth2.id_token
                import google.auth.transport.requests

                request = google.auth.transport.requests.Request()
                id_info = google.oauth2.id_token.verify_oauth2_token(
                    id_token, request
                )
                if "email" in id_info:
                    return id_info["email"]
            except Exception as exc:
                logger.debug("Could not decode id_token: %s", exc)

        # Try userinfo endpoint
        try:
            import google.auth.transport.requests
            import urllib.request

            # Ensure token is fresh
            if hasattr(credentials, "refresh") and hasattr(credentials, "expired"):
                if credentials.expired:
                    request = google.auth.transport.requests.Request()
                    credentials.refresh(request)

            token = getattr(credentials, "token", None)
            if token:
                req = urllib.request.Request(
                    "https://www.googleapis.com/oauth2/v1/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    return data.get("email", "authenticated-user")
        except Exception as exc:
            logger.warning("Could not fetch email: %s", exc)

        return "authenticated-user"

    def sign_out(
        self,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Sign out and clear stored credentials."""
        self._storage.clear()
        with self._lock:
            self._current_user = None
            self._credentials = None
            self._state = AuthState.SIGNED_OUT
        logger.info("Signed out")
        if on_complete:
            on_complete()

    def refresh_token(
        self,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Refresh the credentials in a background thread."""
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
        """Execute credential refresh (runs in background thread)."""
        with self._lock:
            if self._current_user is None:
                if on_error:
                    on_error(
                        AuthenticationError(
                            message="No user session to refresh",
                            user_message="You are not signed in.",
                            suggested_action="Sign in first.",
                        )
                    )
                return
            self._state = AuthState.REFRESHING

        try:
            import google.auth.transport.requests

            if self._credentials is None:
                # Try to rebuild credentials from stored session
                self._credentials = self._build_credentials_from_session()

            request = google.auth.transport.requests.Request()
            self._credentials.refresh(request)

            expiry = getattr(self._credentials, "expiry", None)
            if expiry is None:
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            elif expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            session = UserSession(
                email=self._current_user.email,
                access_token=self._credentials.token or "",
                refresh_token=getattr(self._credentials, "refresh_token", "") or "",
                token_expiry=expiry,
                scopes=self._current_user.scopes,
                signed_in_at=self._current_user.signed_in_at,
            )

            self._storage.save(session)

            with self._lock:
                self._current_user = session
                self._state = AuthState.SIGNED_IN

            logger.info("Credentials refreshed for %s", session.email)
            if on_success:
                on_success(session)

        except Exception as exc:
            with self._lock:
                self._state = AuthState.SIGNED_OUT
                self._current_user = None
                self._credentials = None
            logger.error("Credential refresh failed: %s", exc)
            if on_error:
                on_error(exc)

    def _build_credentials_from_session(self) -> object:
        """Build credentials object from stored session."""
        from google.oauth2.credentials import Credentials

        if self._current_user is None:
            raise AuthenticationError(
                message="No session to build credentials from",
                user_message="You are not signed in.",
                suggested_action="Sign in first.",
            )

        # Get client config for token refresh
        client_config = self._get_client_config()
        client_info = client_config.get("installed") or client_config.get("web", {})

        return Credentials(
            token=self._current_user.access_token,
            refresh_token=self._current_user.refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_info.get("client_id"),
            client_secret=client_info.get("client_secret"),
            scopes=self._current_user.scopes,
        )

    def load_stored_credentials(self) -> UserSession | None:
        """Load credentials on startup from storage."""
        session = self._storage.load()
        if session is None:
            return None

        # Check if token needs refresh
        now = datetime.now(timezone.utc)
        token_expiry = session.token_expiry
        if token_expiry.tzinfo is None:
            token_expiry = token_expiry.replace(tzinfo=timezone.utc)

        needs_refresh = (token_expiry - now) < timedelta(minutes=5)

        with self._lock:
            self._current_user = session
            self._state = AuthState.SIGNED_IN

        # Try to rebuild and refresh credentials
        if session.refresh_token:
            try:
                self._credentials = self._build_credentials_from_session()
                if needs_refresh:
                    self.refresh_token()
            except Exception as exc:
                logger.debug("Could not rebuild credentials: %s", exc)

        return session

    def get_credentials(self) -> object:
        """Return the current credentials object.

        Raises ``AuthenticationError`` if not authenticated.
        """
        if self._credentials is not None:
            # Refresh if needed
            try:
                import google.auth.transport.requests

                if hasattr(self._credentials, "expired") and self._credentials.expired:
                    request = google.auth.transport.requests.Request()
                    self._credentials.refresh(request)
            except Exception:
                pass
            return self._credentials

        if self._current_user is None:
            raise AuthenticationError(
                message="Not authenticated",
                user_message="You are not signed in.",
                suggested_action="Sign in to access GCS.",
            )

        # Try to rebuild credentials from session
        try:
            self._credentials = self._build_credentials_from_session()
            return self._credentials
        except Exception as exc:
            raise AuthenticationError(
                message=f"Could not get credentials: {exc}",
                user_message="Authentication failed.",
                suggested_action="Please sign in again.",
            ) from exc

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
