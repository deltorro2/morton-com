"""Unit tests for the morton-com exception hierarchy.

Tests cover MortonError and all subclasses, ensuring proper initialization,
attribute access, inheritance, exception chaining, and isinstance checks.
"""

from __future__ import annotations

import pytest

from src.errors import (
    AuthenticationError,
    ConfigurationError,
    FileSystemError,
    MortonError,
    NetworkError,
    PermissionError,
    TransferError,
)


class TestMortonErrorInitialization:
    """Tests for MortonError __init__ with various argument combinations."""

    def test_init_with_all_arguments(self) -> None:
        """MortonError accepts all four arguments and stores them correctly."""
        error = MortonError(
            message="Technical failure detail",
            user_message="Something went wrong",
            suggested_action="Please try again",
            technical_detail="Stack trace or debug info",
        )

        assert error.user_message == "Something went wrong"
        assert error.suggested_action == "Please try again"
        assert error.technical_detail == "Stack trace or debug info"

    def test_init_with_default_technical_detail(self) -> None:
        """MortonError uses empty string as default for technical_detail."""
        error = MortonError(
            message="Connection failed",
            user_message="Could not connect",
            suggested_action="Check your internet connection",
        )

        assert error.technical_detail == ""

    def test_init_with_empty_strings(self) -> None:
        """MortonError accepts empty strings for all parameters."""
        error = MortonError(
            message="",
            user_message="",
            suggested_action="",
            technical_detail="",
        )

        assert error.user_message == ""
        assert error.suggested_action == ""
        assert error.technical_detail == ""


class TestMortonErrorMessageAccess:
    """Tests for accessing the exception message via str() and args."""

    def test_message_accessible_via_str(self) -> None:
        """The message is accessible via str() on the exception."""
        error = MortonError(
            message="Detailed error message",
            user_message="User-friendly message",
            suggested_action="Take this action",
        )

        assert str(error) == "Detailed error message"

    def test_message_accessible_via_args(self) -> None:
        """The message is accessible via the args tuple."""
        error = MortonError(
            message="Error in args",
            user_message="User message",
            suggested_action="Action to take",
        )

        assert error.args == ("Error in args",)
        assert error.args[0] == "Error in args"


class TestMortonErrorAttributes:
    """Tests for user_message, suggested_action, and technical_detail attributes."""

    def test_user_message_attribute(self) -> None:
        """user_message attribute is correctly stored and accessible."""
        error = MortonError(
            message="Internal error",
            user_message="The file could not be uploaded",
            suggested_action="Try again later",
        )

        assert hasattr(error, "user_message")
        assert error.user_message == "The file could not be uploaded"

    def test_suggested_action_attribute(self) -> None:
        """suggested_action attribute is correctly stored and accessible."""
        error = MortonError(
            message="Auth token expired",
            user_message="Session expired",
            suggested_action="Please log in again",
        )

        assert hasattr(error, "suggested_action")
        assert error.suggested_action == "Please log in again"

    def test_technical_detail_attribute(self) -> None:
        """technical_detail attribute is correctly stored and accessible."""
        error = MortonError(
            message="API error",
            user_message="Service unavailable",
            suggested_action="Contact support",
            technical_detail="HTTP 503: Service Unavailable at endpoint /api/v1/upload",
        )

        assert hasattr(error, "technical_detail")
        assert "HTTP 503" in error.technical_detail


class TestSubclassInheritance:
    """Tests that each subclass properly inherits from MortonError."""

    @pytest.mark.parametrize(
        "error_class",
        [
            AuthenticationError,
            PermissionError,
            NetworkError,
            TransferError,
            ConfigurationError,
            FileSystemError,
        ],
    )
    def test_subclass_inherits_from_morton_error(self, error_class: type) -> None:
        """Each error subclass is a subclass of MortonError."""
        assert issubclass(error_class, MortonError)

    @pytest.mark.parametrize(
        "error_class",
        [
            AuthenticationError,
            PermissionError,
            NetworkError,
            TransferError,
            ConfigurationError,
            FileSystemError,
        ],
    )
    def test_subclass_inherits_from_exception(self, error_class: type) -> None:
        """Each error subclass is also a subclass of Exception."""
        assert issubclass(error_class, Exception)


class TestSubclassRaiseAndCatch:
    """Tests that subclasses can be raised and caught as MortonError."""

    def test_authentication_error_caught_as_morton_error(self) -> None:
        """AuthenticationError can be raised and caught as MortonError."""
        with pytest.raises(MortonError):
            raise AuthenticationError(
                message="OAuth token invalid",
                user_message="Authentication failed",
                suggested_action="Sign in again",
            )

    def test_permission_error_caught_as_morton_error(self) -> None:
        """PermissionError can be raised and caught as MortonError."""
        with pytest.raises(MortonError):
            raise PermissionError(
                message="Access denied to bucket",
                user_message="You don't have access",
                suggested_action="Request access from the owner",
            )

    def test_network_error_caught_as_morton_error(self) -> None:
        """NetworkError can be raised and caught as MortonError."""
        with pytest.raises(MortonError):
            raise NetworkError(
                message="DNS resolution failed",
                user_message="Network unavailable",
                suggested_action="Check your connection",
            )

    def test_transfer_error_caught_as_morton_error(self) -> None:
        """TransferError can be raised and caught as MortonError."""
        with pytest.raises(MortonError):
            raise TransferError(
                message="Upload interrupted at byte 1024",
                user_message="Upload failed",
                suggested_action="Retry the upload",
            )

    def test_configuration_error_caught_as_morton_error(self) -> None:
        """ConfigurationError can be raised and caught as MortonError."""
        with pytest.raises(MortonError):
            raise ConfigurationError(
                message="Missing required key: gcs_bucket",
                user_message="Configuration error",
                suggested_action="Check your settings file",
            )

    def test_filesystem_error_caught_as_morton_error(self) -> None:
        """FileSystemError can be raised and caught as MortonError."""
        with pytest.raises(MortonError):
            raise FileSystemError(
                message="ENOENT: /path/to/file",
                user_message="File not found",
                suggested_action="Verify the file path",
            )


class TestExceptionChaining:
    """Tests that exception chaining works properly with MortonError."""

    def test_exception_chaining_with_raise_from(self) -> None:
        """Exception chaining preserves the original cause."""
        original = ValueError("Original cause")

        try:
            try:
                raise original
            except ValueError as e:
                raise NetworkError(
                    message="Wrapped error",
                    user_message="Connection issue",
                    suggested_action="Retry",
                ) from e
        except NetworkError as chained:
            assert chained.__cause__ is original
            assert isinstance(chained.__cause__, ValueError)

    def test_exception_chaining_with_implicit_context(self) -> None:
        """Implicit exception chaining captures __context__."""
        original = OSError("Disk full")

        try:
            try:
                raise original
            except OSError:
                raise FileSystemError(
                    message="Write failed",
                    user_message="Could not save file",
                    suggested_action="Free up disk space",
                )
        except FileSystemError as chained:
            assert chained.__context__ is original

    def test_chained_exception_attributes_preserved(self) -> None:
        """Chained MortonError retains its own attributes."""
        original = RuntimeError("Low-level failure")

        try:
            try:
                raise original
            except RuntimeError as e:
                raise TransferError(
                    message="Transfer aborted",
                    user_message="File transfer stopped",
                    suggested_action="Please retry the transfer",
                    technical_detail="Aborted at 50%",
                ) from e
        except TransferError as chained:
            assert chained.user_message == "File transfer stopped"
            assert chained.suggested_action == "Please retry the transfer"
            assert chained.technical_detail == "Aborted at 50%"
            assert str(chained) == "Transfer aborted"


class TestIsinstanceHierarchy:
    """Tests for isinstance checks across the exception hierarchy."""

    def test_morton_error_is_instance_of_exception(self) -> None:
        """MortonError instance is an instance of Exception."""
        error = MortonError(
            message="Test",
            user_message="Test",
            suggested_action="Test",
        )

        assert isinstance(error, Exception)
        assert isinstance(error, MortonError)

    def test_subclass_isinstance_checks(self) -> None:
        """Subclass instances pass isinstance checks for MortonError."""
        auth_error = AuthenticationError(
            message="Auth failed",
            user_message="Login failed",
            suggested_action="Try again",
        )

        assert isinstance(auth_error, AuthenticationError)
        assert isinstance(auth_error, MortonError)
        assert isinstance(auth_error, Exception)
        assert not isinstance(auth_error, NetworkError)

    def test_multiple_subclass_isinstance_differentiation(self) -> None:
        """Different subclasses are distinguishable via isinstance."""
        network_err = NetworkError(
            message="Timeout",
            user_message="Connection timed out",
            suggested_action="Check network",
        )
        config_err = ConfigurationError(
            message="Invalid config",
            user_message="Settings error",
            suggested_action="Review settings",
        )

        # Both are MortonError
        assert isinstance(network_err, MortonError)
        assert isinstance(config_err, MortonError)

        # But they are different specific types
        assert isinstance(network_err, NetworkError)
        assert not isinstance(network_err, ConfigurationError)
        assert isinstance(config_err, ConfigurationError)
        assert not isinstance(config_err, NetworkError)

    def test_base_morton_error_not_instance_of_subclass(self) -> None:
        """A MortonError instance is not an instance of its subclasses."""
        base_error = MortonError(
            message="Base error",
            user_message="Error occurred",
            suggested_action="Contact support",
        )

        assert isinstance(base_error, MortonError)
        assert not isinstance(base_error, AuthenticationError)
        assert not isinstance(base_error, PermissionError)
        assert not isinstance(base_error, NetworkError)
        assert not isinstance(base_error, TransferError)
        assert not isinstance(base_error, ConfigurationError)
        assert not isinstance(base_error, FileSystemError)
