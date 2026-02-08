"""Authentication service using Application Default Credentials (ADC).

Uses credentials from `gcloud auth application-default login` to authenticate
with Google Cloud services. Run the gcloud command once to set up credentials.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from src.errors import AuthenticationError
from src.models import AuthState
from src.models.user_session import UserSession
from src.services.credential_storage import CredentialStorage

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/devstorage.read_write",
    "https://www.googleapis.com/auth/cloud-platform",
]


class AuthService:
    """Service for authentication using Application Default Credentials."""

    def __init__(
        self,
        credential_storage: CredentialStorage | None = None,
    ) -> None:
        self._storage = credential_storage or CredentialStorage()
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

    def sign_in(
        self,
        on_browser_opened: Callable[[], None] | None = None,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Load Application Default Credentials in a background thread."""
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
        """Load ADC credentials (runs in background thread)."""
        try:
            import google.auth
            import google.auth.transport.requests

            if on_browser_opened:
                on_browser_opened()

            # Load Application Default Credentials
            credentials, project = google.auth.default(scopes=SCOPES)

            # Refresh to ensure we have a valid token
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)

            # Get user email
            email = self._fetch_email(credentials)

            # Store credentials
            self._credentials = credentials

            # Handle expiry
            expiry = getattr(credentials, "expiry", None)
            if expiry is None:
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            elif expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            session = UserSession(
                email=email,
                access_token=credentials.token or "",
                refresh_token=getattr(credentials, "refresh_token", "") or "",
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

        except Exception as exc:
            with self._lock:
                self._state = AuthState.SIGNED_OUT
            logger.error("Sign-in failed: %s", exc)

            # Provide helpful error message
            error_msg = str(exc)
            if "Could not automatically determine credentials" in error_msg:
                error = AuthenticationError(
                    message=f"ADC not found: {exc}",
                    user_message="No Google Cloud credentials found.",
                    suggested_action="Run 'gcloud auth application-default login' in your terminal.",
                    technical_detail=error_msg,
                )
            elif "Reauthentication is needed" in error_msg:
                error = AuthenticationError(
                    message=f"ADC expired: {exc}",
                    user_message="Your credentials have expired.",
                    suggested_action="Run 'gcloud auth application-default login' to refresh.",
                    technical_detail=error_msg,
                )
            else:
                error = AuthenticationError(
                    message=f"Authentication failed: {exc}",
                    user_message="Sign-in failed.",
                    suggested_action="Run 'gcloud auth application-default login' in your terminal.",
                    technical_detail=error_msg,
                )

            if on_error:
                on_error(error)

    @staticmethod
    def _fetch_email(credentials: object) -> str:
        """Fetch the user's email from credentials or userinfo endpoint."""
        # Try service account email first
        if hasattr(credentials, "service_account_email"):
            return credentials.service_account_email

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
            import google.auth
            import google.auth.transport.requests

            # Reload ADC credentials
            credentials, project = google.auth.default(scopes=SCOPES)
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)

            self._credentials = credentials

            expiry = getattr(credentials, "expiry", None)
            if expiry is None:
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            elif expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            session = UserSession(
                email=self._current_user.email,
                access_token=credentials.token or "",
                refresh_token=getattr(credentials, "refresh_token", "") or "",
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

    def load_stored_credentials(self) -> UserSession | None:
        """Load credentials on startup - tries ADC."""
        try:
            import google.auth
            import google.auth.transport.requests

            credentials, project = google.auth.default(scopes=SCOPES)
            request = google.auth.transport.requests.Request()
            credentials.refresh(request)

            email = self._fetch_email(credentials)
            self._credentials = credentials

            expiry = getattr(credentials, "expiry", None)
            if expiry is None:
                expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            elif expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)

            session = UserSession(
                email=email,
                access_token=credentials.token or "",
                refresh_token=getattr(credentials, "refresh_token", "") or "",
                token_expiry=expiry,
                scopes=list(SCOPES),
                signed_in_at=datetime.now(timezone.utc),
            )

            with self._lock:
                self._current_user = session
                self._state = AuthState.SIGNED_IN

            logger.info("Loaded ADC credentials for %s", email)
            return session

        except Exception as exc:
            logger.debug("Could not load ADC: %s", exc)
            return None

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

        # Try to get fresh ADC credentials
        try:
            import google.auth

            credentials, project = google.auth.default(scopes=SCOPES)
            self._credentials = credentials
            return credentials
        except Exception as exc:
            raise AuthenticationError(
                message=f"Could not get credentials: {exc}",
                user_message="Authentication failed.",
                suggested_action="Run 'gcloud auth application-default login' in your terminal.",
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
