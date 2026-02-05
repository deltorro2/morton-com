"""Secure credential storage service.

Encrypts OAuth2 tokens using Fernet symmetric encryption with the
encryption key stored in the platform keyring (macOS Keychain /
Windows Credential Manager).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from src.errors import ConfigurationError
from src.models.user_session import UserSession
from src.platform import get_platform

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "morton-com"
_KEYRING_USERNAME = "oauth-key"
_CREDENTIALS_FILE = "credentials.enc"


class CredentialStorage:
    """Service for secure credential storage using Fernet encryption."""

    def __init__(self, config_dir: Path | None = None) -> None:
        if config_dir is not None:
            self._config_dir = config_dir
        else:
            self._config_dir = get_platform().get_config_directory()

    @property
    def _credentials_path(self) -> Path:
        return self._config_dir / _CREDENTIALS_FILE

    # ------------------------------------------------------------------
    # Keyring helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_or_create_key() -> bytes:
        """Retrieve the Fernet key from the keyring, creating one if absent."""
        import keyring

        existing = keyring.get_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        if existing is not None:
            return existing.encode()

        key = Fernet.generate_key()
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_USERNAME, key.decode())
        return key

    @staticmethod
    def _delete_key() -> None:
        """Remove the encryption key from the keyring."""
        import keyring

        try:
            keyring.delete_password(_KEYRING_SERVICE, _KEYRING_USERNAME)
        except keyring.errors.PasswordDeleteError:
            pass

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(self, session: UserSession) -> None:
        """Encrypt and persist a UserSession."""
        try:
            key = self._get_or_create_key()
            fernet = Fernet(key)

            payload = {
                "email": session.email,
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "token_expiry": session.token_expiry.isoformat(),
                "scopes": session.scopes,
                "signed_in_at": session.signed_in_at.isoformat(),
            }
            plaintext = json.dumps(payload).encode()
            encrypted = fernet.encrypt(plaintext)

            self._config_dir.mkdir(parents=True, exist_ok=True)
            self._credentials_path.write_bytes(encrypted)
            logger.info("Credentials saved for %s", session.email)
        except Exception as exc:
            raise ConfigurationError(
                message=f"Failed to save credentials: {exc}",
                user_message="Could not save your sign-in credentials.",
                suggested_action="Try signing in again.",
                technical_detail=str(exc),
            ) from exc

    def load(self) -> UserSession | None:
        """Load and decrypt stored credentials.

        Returns ``None`` if no credentials exist or decryption fails.
        """
        if not self._credentials_path.exists():
            return None

        try:
            key = self._get_or_create_key()
            fernet = Fernet(key)
            encrypted = self._credentials_path.read_bytes()
            plaintext = fernet.decrypt(encrypted)
            data = json.loads(plaintext)

            return UserSession(
                email=data["email"],
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                token_expiry=datetime.fromisoformat(data["token_expiry"]),
                scopes=data.get("scopes", []),
                signed_in_at=datetime.fromisoformat(data["signed_in_at"]),
            )
        except (InvalidToken, KeyError, json.JSONDecodeError) as exc:
            logger.warning("Stored credentials are invalid, clearing: %s", exc)
            self.clear()
            return None
        except Exception as exc:
            logger.warning("Failed to load credentials: %s", exc)
            return None

    def clear(self) -> None:
        """Remove stored credentials and keyring entry."""
        try:
            if self._credentials_path.exists():
                self._credentials_path.unlink()
            self._delete_key()
            logger.info("Credentials cleared")
        except OSError as exc:
            logger.warning("Failed to clear credentials file: %s", exc)

    def has_credentials(self) -> bool:
        """Return ``True`` if an encrypted credentials file exists."""
        return self._credentials_path.exists()
