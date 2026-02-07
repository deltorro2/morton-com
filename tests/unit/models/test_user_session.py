"""Unit tests for UserSession dataclass."""

from datetime import datetime, timedelta, timezone

import pytest

from src.models.user_session import UserSession


class TestUserSessionCreation:
    """Tests for UserSession instantiation."""

    def test_user_session_with_required_fields(self) -> None:
        """UserSession can be created with only required fields."""
        token_expiry = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        session = UserSession(
            email="user@example.com",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            token_expiry=token_expiry,
        )

        assert session.email == "user@example.com"
        assert session.access_token == "access_token_123"
        assert session.refresh_token == "refresh_token_456"
        assert session.token_expiry == token_expiry
        assert session.scopes == []
        assert session.signed_in_at is not None
        assert session.signed_in_at.tzinfo == timezone.utc

    def test_user_session_with_all_fields_including_scopes(self) -> None:
        """UserSession can be created with all fields including scopes."""
        token_expiry = datetime(2099, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        signed_in_at = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        scopes = ["https://www.googleapis.com/auth/devstorage.read_only"]

        session = UserSession(
            email="admin@company.org",
            access_token="admin_access_token",
            refresh_token="admin_refresh_token",
            token_expiry=token_expiry,
            scopes=scopes,
            signed_in_at=signed_in_at,
        )

        assert session.email == "admin@company.org"
        assert session.access_token == "admin_access_token"
        assert session.refresh_token == "admin_refresh_token"
        assert session.token_expiry == token_expiry
        assert session.scopes == scopes
        assert session.signed_in_at == signed_in_at


class TestIsAuthenticated:
    """Tests for is_authenticated property."""

    def test_is_authenticated_returns_true_when_access_token_present(self) -> None:
        """is_authenticated returns True when access_token is present."""
        session = UserSession(
            email="user@example.com",
            access_token="valid_token",
            refresh_token="refresh",
            token_expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )

        assert session.is_authenticated is True

    def test_is_authenticated_returns_false_when_access_token_empty(self) -> None:
        """is_authenticated returns False when access_token is empty string."""
        session = UserSession(
            email="user@example.com",
            access_token="",
            refresh_token="refresh",
            token_expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )

        assert session.is_authenticated is False


class TestIsExpired:
    """Tests for is_expired property."""

    def test_is_expired_returns_true_when_token_expiry_in_past(self) -> None:
        """is_expired returns True when token_expiry is in the past."""
        far_past = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        session = UserSession(
            email="user@example.com",
            access_token="token",
            refresh_token="refresh",
            token_expiry=far_past,
        )

        assert session.is_expired is True

    def test_is_expired_returns_false_when_token_expiry_in_future(self) -> None:
        """is_expired returns False when token_expiry is in the future."""
        far_future = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        session = UserSession(
            email="user@example.com",
            access_token="token",
            refresh_token="refresh",
            token_expiry=far_future,
        )

        assert session.is_expired is False


class TestNeedsRefresh:
    """Tests for needs_refresh property."""

    def test_needs_refresh_returns_true_when_expiring_within_5_minutes(self) -> None:
        """needs_refresh returns True when token expires within 5 minutes."""
        # Set expiry to 3 minutes from now (within 5-minute threshold)
        expiry_soon = datetime.now(timezone.utc) + timedelta(minutes=3)

        session = UserSession(
            email="user@example.com",
            access_token="token",
            refresh_token="refresh",
            token_expiry=expiry_soon,
        )

        assert session.needs_refresh is True

    def test_needs_refresh_returns_false_when_valid_for_more_than_5_minutes(
        self,
    ) -> None:
        """needs_refresh returns False when token is valid for more than 5 minutes."""
        far_future = datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

        session = UserSession(
            email="user@example.com",
            access_token="token",
            refresh_token="refresh",
            token_expiry=far_future,
        )

        assert session.needs_refresh is False


class TestDisplayName:
    """Tests for display_name property."""

    def test_display_name_returns_email_prefix_before_at_symbol(self) -> None:
        """display_name returns email prefix before '@' symbol."""
        session = UserSession(
            email="john.doe@example.com",
            access_token="token",
            refresh_token="refresh",
            token_expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )

        assert session.display_name == "john.doe"

    def test_display_name_handles_email_without_at_symbol(self) -> None:
        """display_name handles email without '@' symbol gracefully."""
        session = UserSession(
            email="invalid_email_format",
            access_token="token",
            refresh_token="refresh",
            token_expiry=datetime(2099, 1, 1, tzinfo=timezone.utc),
        )

        assert session.display_name == "invalid_email_format"
