"""Exception hierarchy for morton-com.

All application-specific errors inherit from MortonError, which carries
user-facing messaging alongside the standard exception message so that
UI layers can present actionable feedback without leaking internals.
"""

from __future__ import annotations


class MortonError(Exception):
    """Base exception for all morton-com errors.

    Parameters
    ----------
    message:
        Technical message suitable for logging.
    user_message:
        Short, non-technical message safe to display in the UI.
    suggested_action:
        Guidance the user can follow to resolve the problem.
    technical_detail:
        Optional extra detail for diagnostics / log output.
    """

    def __init__(
        self,
        message: str,
        user_message: str,
        suggested_action: str,
        technical_detail: str = "",
    ) -> None:
        super().__init__(message)
        self.user_message = user_message
        self.suggested_action = suggested_action
        self.technical_detail = technical_detail


class AuthenticationError(MortonError):
    """Raised when authentication with Google Cloud fails."""


class PermissionError(MortonError):  # noqa: A001
    """Raised when the user lacks permission to perform an operation."""


class NetworkError(MortonError):
    """Raised on network-level failures (timeouts, DNS, connectivity)."""


class TransferError(MortonError):
    """Raised when a file transfer operation fails."""


class ConfigurationError(MortonError):
    """Raised when application configuration is invalid or missing."""


class FileSystemError(MortonError):
    """Raised on local file-system errors (read, write, delete)."""
