"""Unit tests for AuthService."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.errors import AuthenticationError
from src.models import AuthState
from src.models.user_session import UserSession
from src.services.auth_service import AuthService


def _create_test_session(
    email: str = "test@example.com",
    needs_refresh: bool = False,
) -> UserSession:
    """Create a UserSession for testing."""
    if needs_refresh:
        # Token expiring in 2 minutes (within 5-minute threshold)
        token_expiry = datetime.now(timezone.utc) + timedelta(minutes=2)
    else:
        # Token valid for a long time
        token_expiry = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    return UserSession(
        email=email,
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        token_expiry=token_expiry,
        scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
        signed_in_at=datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    )


class TestAuthServiceInitialization:
    """Tests for AuthService initialization."""

    def test_initial_state_is_signed_out(self) -> None:
        """AuthService starts with state SIGNED_OUT."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)

        assert service.state == AuthState.SIGNED_OUT

    def test_initial_current_user_is_none(self) -> None:
        """AuthService starts with current_user as None."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)

        assert service.current_user is None


class TestSignIn:
    """Tests for sign_in method."""

    def test_sign_in_raises_error_if_already_signing_in(self) -> None:
        """sign_in raises AuthenticationError if already SIGNING_IN."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNING_IN

        with pytest.raises(AuthenticationError) as exc_info:
            service.sign_in()

        assert "already in progress" in str(exc_info.value)

    def test_sign_in_sets_state_to_signing_in(self) -> None:
        """sign_in sets state to SIGNING_IN before starting thread."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)

        with patch.object(service, "_run_sign_in"):
            with patch("threading.Thread") as mock_thread:
                mock_thread_instance = MagicMock()
                mock_thread.return_value = mock_thread_instance

                service.sign_in()

                assert service.state == AuthState.SIGNING_IN


class TestRunSignIn:
    """Tests for _run_sign_in method (called directly to avoid threading)."""

    def test_run_sign_in_success_sets_signed_in_and_calls_on_success(self) -> None:
        """_run_sign_in success sets state to SIGNED_IN and calls on_success."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNING_IN

        # Mock ADC credentials
        mock_creds = MagicMock()
        mock_creds.token = "new_access_token"
        mock_creds.expiry = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        on_browser_opened = MagicMock()
        on_success = MagicMock()
        on_error = MagicMock()

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            with patch("google.auth.transport.requests.Request"):
                with patch.object(service, "_fetch_email", return_value="user@example.com"):
                    service._run_sign_in(on_browser_opened, on_success, on_error)

        assert service.state == AuthState.SIGNED_IN
        assert service.current_user is not None
        assert service.current_user.email == "user@example.com"

        on_browser_opened.assert_called_once()
        on_success.assert_called_once()
        on_error.assert_not_called()
        mock_storage.save.assert_called_once()

    def test_run_sign_in_failure_sets_signed_out_and_calls_on_error(self) -> None:
        """_run_sign_in failure sets state to SIGNED_OUT and calls on_error."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNING_IN

        on_success = MagicMock()
        on_error = MagicMock()

        with patch("google.auth.default", side_effect=Exception("ADC not found")):
            with patch("google.auth.transport.requests.Request"):
                service._run_sign_in(None, on_success, on_error)

        assert service.state == AuthState.SIGNED_OUT
        on_success.assert_not_called()
        on_error.assert_called_once()

        error_arg = on_error.call_args[0][0]
        assert isinstance(error_arg, AuthenticationError)

    def test_run_sign_in_provides_helpful_error_for_missing_adc(self) -> None:
        """_run_sign_in provides helpful error when ADC not configured."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNING_IN

        on_error = MagicMock()

        with patch(
            "google.auth.default",
            side_effect=Exception("Could not automatically determine credentials"),
        ):
            with patch("google.auth.transport.requests.Request"):
                service._run_sign_in(None, None, on_error)

        error_arg = on_error.call_args[0][0]
        assert "gcloud auth application-default login" in error_arg.suggested_action


class TestSignOut:
    """Tests for sign_out method."""

    def test_sign_out_clears_credentials_and_sets_signed_out(self) -> None:
        """sign_out clears credentials and sets state to SIGNED_OUT."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNED_IN
        service._current_user = _create_test_session()

        service.sign_out()

        assert service.state == AuthState.SIGNED_OUT
        assert service.current_user is None
        mock_storage.clear.assert_called_once()

    def test_sign_out_calls_on_complete_callback(self) -> None:
        """sign_out calls on_complete callback after clearing."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNED_IN
        service._current_user = _create_test_session()

        on_complete = MagicMock()
        service.sign_out(on_complete=on_complete)

        on_complete.assert_called_once()


class TestRefreshToken:
    """Tests for refresh_token and _run_refresh methods."""

    def test_run_refresh_with_no_current_user_calls_on_error(self) -> None:
        """_run_refresh with no current_user calls on_error."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._current_user = None

        on_success = MagicMock()
        on_error = MagicMock()

        service._run_refresh(on_success, on_error)

        on_success.assert_not_called()
        on_error.assert_called_once()

        error_arg = on_error.call_args[0][0]
        assert isinstance(error_arg, AuthenticationError)
        assert "No user session" in str(error_arg)

    def test_run_refresh_success_updates_session_and_calls_on_success(self) -> None:
        """_run_refresh success updates session and calls on_success."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNED_IN
        service._current_user = _create_test_session(email="user@example.com")

        # Mock refreshed ADC credentials
        mock_creds = MagicMock()
        mock_creds.token = "refreshed_access_token"
        mock_creds.expiry = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        on_success = MagicMock()
        on_error = MagicMock()

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            with patch("google.auth.transport.requests.Request"):
                service._run_refresh(on_success, on_error)

        assert service.state == AuthState.SIGNED_IN
        assert service.current_user is not None
        assert service.current_user.access_token == "refreshed_access_token"

        on_success.assert_called_once()
        on_error.assert_not_called()
        mock_storage.save.assert_called_once()

    def test_run_refresh_failure_sets_signed_out_and_calls_on_error(self) -> None:
        """_run_refresh failure sets state to SIGNED_OUT and calls on_error."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNED_IN
        service._current_user = _create_test_session()

        on_success = MagicMock()
        on_error = MagicMock()

        with patch("google.auth.default", side_effect=Exception("Refresh failed")):
            with patch("google.auth.transport.requests.Request"):
                service._run_refresh(on_success, on_error)

        assert service.state == AuthState.SIGNED_OUT
        assert service.current_user is None
        on_success.assert_not_called()
        on_error.assert_called_once()


class TestLoadStoredCredentials:
    """Tests for load_stored_credentials method."""

    def test_load_stored_credentials_returns_none_if_adc_fails(self) -> None:
        """load_stored_credentials returns None if ADC fails."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)

        with patch("google.auth.default", side_effect=Exception("ADC not found")):
            with patch("google.auth.transport.requests.Request"):
                result = service.load_stored_credentials()

        assert result is None
        assert service.state == AuthState.SIGNED_OUT

    def test_load_stored_credentials_sets_state_to_signed_in(self) -> None:
        """load_stored_credentials sets state to SIGNED_IN when ADC available."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)

        # Mock ADC credentials
        mock_creds = MagicMock()
        mock_creds.token = "adc_access_token"
        mock_creds.expiry = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            with patch("google.auth.transport.requests.Request"):
                with patch.object(service, "_fetch_email", return_value="user@example.com"):
                    result = service.load_stored_credentials()

        assert result is not None
        assert result.email == "user@example.com"
        assert service.state == AuthState.SIGNED_IN
        assert service.current_user == result


class TestGetCredentials:
    """Tests for get_credentials method."""

    def test_get_credentials_raises_error_if_not_authenticated(self) -> None:
        """get_credentials raises AuthenticationError if not authenticated."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._current_user = None
        service._credentials = None

        with pytest.raises(AuthenticationError) as exc_info:
            service.get_credentials()

        assert "Not authenticated" in str(exc_info.value)

    def test_get_credentials_returns_stored_credentials_when_available(self) -> None:
        """get_credentials returns stored credentials when available."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._current_user = _create_test_session()

        # Set up stored credentials (not expired)
        mock_creds = MagicMock()
        mock_creds.expired = False
        service._credentials = mock_creds

        result = service.get_credentials()

        assert result == mock_creds

    def test_get_credentials_fetches_adc_when_no_stored_credentials(self) -> None:
        """get_credentials fetches ADC when no stored credentials available."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._current_user = _create_test_session()
        service._credentials = None

        # Mock ADC credentials
        mock_creds = MagicMock()

        with patch("google.auth.default", return_value=(mock_creds, "test-project")):
            result = service.get_credentials()

        assert result == mock_creds
        assert service._credentials == mock_creds


class TestEnsureAuthenticated:
    """Tests for ensure_authenticated method."""

    def test_ensure_authenticated_calls_on_authenticated_when_signed_in(self) -> None:
        """ensure_authenticated calls on_authenticated when signed in."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        session = _create_test_session()
        service._state = AuthState.SIGNED_IN
        service._current_user = session

        on_authenticated = MagicMock()
        on_sign_in_required = MagicMock()

        service.ensure_authenticated(on_authenticated, on_sign_in_required)

        on_authenticated.assert_called_once_with(session)
        on_sign_in_required.assert_not_called()

    def test_ensure_authenticated_calls_on_sign_in_required_when_not_signed_in(
        self,
    ) -> None:
        """ensure_authenticated calls on_sign_in_required when not signed in."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        service._state = AuthState.SIGNED_OUT
        service._current_user = None

        on_authenticated = MagicMock()
        on_sign_in_required = MagicMock()

        service.ensure_authenticated(on_authenticated, on_sign_in_required)

        on_authenticated.assert_not_called()
        on_sign_in_required.assert_called_once()

    def test_ensure_authenticated_requires_both_signed_in_and_current_user(
        self,
    ) -> None:
        """ensure_authenticated requires both SIGNED_IN state and current_user."""
        mock_storage = MagicMock()
        service = AuthService(credential_storage=mock_storage)
        # State is SIGNED_IN but current_user is None (edge case)
        service._state = AuthState.SIGNED_IN
        service._current_user = None

        on_authenticated = MagicMock()
        on_sign_in_required = MagicMock()

        service.ensure_authenticated(on_authenticated, on_sign_in_required)

        on_authenticated.assert_not_called()
        on_sign_in_required.assert_called_once()
