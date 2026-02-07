"""Unit tests for CredentialStorage service."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from src.errors import ConfigurationError
from src.models.user_session import UserSession
from src.services.credential_storage import CredentialStorage


@pytest.fixture
def mock_keyring() -> MagicMock:
    """Create a mock keyring module with in-memory storage."""
    mock = MagicMock()
    mock.storage = {}

    def get_password(service: str, username: str) -> str | None:
        key = (service, username)
        return mock.storage.get(key)

    def set_password(service: str, username: str, password: str) -> None:
        key = (service, username)
        mock.storage[key] = password

    def delete_password(service: str, username: str) -> None:
        key = (service, username)
        if key in mock.storage:
            del mock.storage[key]
        else:
            raise mock.errors.PasswordDeleteError()

    mock.get_password = MagicMock(side_effect=get_password)
    mock.set_password = MagicMock(side_effect=set_password)
    mock.delete_password = MagicMock(side_effect=delete_password)
    mock.errors = MagicMock()
    mock.errors.PasswordDeleteError = Exception

    return mock


@pytest.fixture
def sample_session() -> UserSession:
    """Create a sample UserSession for testing."""
    return UserSession(
        email="test@example.com",
        access_token="access_token_123",
        refresh_token="refresh_token_456",
        token_expiry=datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        scopes=["https://www.googleapis.com/auth/devstorage.read_only"],
        signed_in_at=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )


class TestSave:
    """Tests for CredentialStorage.save()."""

    def test_save_creates_encrypted_credentials_file(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """save() creates an encrypted credentials file."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)
            storage.save(sample_session)

            credentials_file = tmp_path / "credentials.enc"
            assert credentials_file.exists()
            # File should contain encrypted data (not plain JSON)
            content = credentials_file.read_bytes()
            assert b"test@example.com" not in content

    def test_save_creates_config_directory_if_needed(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """save() creates the config directory if it does not exist."""
        config_dir = tmp_path / "nested" / "config" / "dir"
        assert not config_dir.exists()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=config_dir)
            storage.save(sample_session)

            assert config_dir.exists()
            assert (config_dir / "credentials.enc").exists()

    def test_save_raises_configuration_error_on_failure(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """save() raises ConfigurationError when encryption fails."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)

            # Make Fernet raise an exception
            with patch(
                "src.services.credential_storage.Fernet",
                side_effect=ValueError("Invalid key"),
            ):
                with pytest.raises(ConfigurationError) as exc_info:
                    storage.save(sample_session)

                assert "Failed to save credentials" in str(exc_info.value)


class TestLoad:
    """Tests for CredentialStorage.load()."""

    def test_load_returns_none_when_no_credentials_file(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """load() returns None when no credentials file exists."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)
            result = storage.load()

            assert result is None

    def test_load_returns_user_session_when_valid(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """load() returns a UserSession when credentials are valid."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)
            storage.save(sample_session)

            loaded_session = storage.load()

            assert loaded_session is not None
            assert loaded_session.email == sample_session.email
            assert loaded_session.access_token == sample_session.access_token
            assert loaded_session.refresh_token == sample_session.refresh_token
            assert loaded_session.token_expiry == sample_session.token_expiry
            assert loaded_session.scopes == sample_session.scopes
            assert loaded_session.signed_in_at == sample_session.signed_in_at

    def test_load_returns_none_and_clears_on_invalid_token(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """load() returns None and calls clear() when decryption fails with InvalidToken."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)
            storage.save(sample_session)

            credentials_file = tmp_path / "credentials.enc"
            assert credentials_file.exists()

            # Corrupt the encrypted file to cause InvalidToken
            credentials_file.write_bytes(b"corrupted data that is not valid fernet")

            result = storage.load()

            assert result is None
            # clear() should have been called, removing the file
            assert not credentials_file.exists()

    def test_load_returns_none_on_json_decode_error(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """load() returns None and calls clear() on JSONDecodeError."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)

            # Create a valid Fernet key and encrypt invalid JSON
            key = Fernet.generate_key()
            mock_keyring.storage[("morton-com", "oauth-key")] = key.decode()

            fernet = Fernet(key)
            invalid_json = b"not valid json {"
            encrypted = fernet.encrypt(invalid_json)

            credentials_file = tmp_path / "credentials.enc"
            credentials_file.write_bytes(encrypted)

            result = storage.load()

            assert result is None
            # clear() should have been called
            assert not credentials_file.exists()


class TestRoundTrip:
    """Tests for save/load round-trip."""

    def test_round_trip_save_then_load(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """Saving and then loading returns an equivalent UserSession."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)

            storage.save(sample_session)
            loaded_session = storage.load()

            assert loaded_session is not None
            assert loaded_session.email == sample_session.email
            assert loaded_session.access_token == sample_session.access_token
            assert loaded_session.refresh_token == sample_session.refresh_token
            assert loaded_session.token_expiry == sample_session.token_expiry
            assert loaded_session.scopes == sample_session.scopes
            assert loaded_session.signed_in_at == sample_session.signed_in_at


class TestClear:
    """Tests for CredentialStorage.clear()."""

    def test_clear_removes_file_and_keyring_entry(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """clear() removes the credentials file and keyring entry."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)
            storage.save(sample_session)

            credentials_file = tmp_path / "credentials.enc"
            assert credentials_file.exists()
            assert ("morton-com", "oauth-key") in mock_keyring.storage

            storage.clear()

            assert not credentials_file.exists()
            assert ("morton-com", "oauth-key") not in mock_keyring.storage


class TestHasCredentials:
    """Tests for CredentialStorage.has_credentials()."""

    def test_has_credentials_returns_false_when_no_file(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """has_credentials() returns False when no credentials file exists."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)

            assert storage.has_credentials() is False

    def test_has_credentials_returns_true_when_file_exists(
        self, tmp_path: Path, mock_keyring: MagicMock, sample_session: UserSession
    ) -> None:
        """has_credentials() returns True when credentials file exists."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            storage = CredentialStorage(config_dir=tmp_path)
            storage.save(sample_session)

            assert storage.has_credentials() is True


class TestGetOrCreateKey:
    """Tests for CredentialStorage._get_or_create_key()."""

    def test_get_or_create_key_creates_new_key_if_not_in_keyring(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """_get_or_create_key() creates a new key when none exists in keyring."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            assert ("morton-com", "oauth-key") not in mock_keyring.storage

            key = CredentialStorage._get_or_create_key()

            assert key is not None
            assert isinstance(key, bytes)
            # Key should now be stored in keyring
            assert ("morton-com", "oauth-key") in mock_keyring.storage
            # Verify it's a valid Fernet key
            Fernet(key)  # Should not raise

    def test_get_or_create_key_returns_existing_key_if_in_keyring(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """_get_or_create_key() returns existing key when one exists in keyring."""
        # Pre-populate keyring with a known key
        existing_key = Fernet.generate_key()
        mock_keyring.storage[("morton-com", "oauth-key")] = existing_key.decode()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            key = CredentialStorage._get_or_create_key()

            assert key == existing_key
            # set_password should not have been called (existing key was used)
            # We can verify the storage still has the same key
            assert (
                mock_keyring.storage[("morton-com", "oauth-key")]
                == existing_key.decode()
            )


class TestDeleteKey:
    """Tests for CredentialStorage._delete_key()."""

    def test_delete_key_removes_key_from_keyring(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """_delete_key() removes the encryption key from keyring."""
        # Pre-populate keyring with a key
        existing_key = Fernet.generate_key()
        mock_keyring.storage[("morton-com", "oauth-key")] = existing_key.decode()

        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            CredentialStorage._delete_key()

            assert ("morton-com", "oauth-key") not in mock_keyring.storage

    def test_delete_key_handles_missing_key_gracefully(
        self, tmp_path: Path, mock_keyring: MagicMock
    ) -> None:
        """_delete_key() does not raise when key does not exist in keyring."""
        with patch.dict("sys.modules", {"keyring": mock_keyring}):
            # Should not raise even though no key exists
            CredentialStorage._delete_key()
