# Service Contracts: Dual-Panel File Manager

**Feature**: 001-dual-panel-filemanager
**Date**: 2026-02-04
**Updated**: 2026-02-04 (added AuthService for browser-based OAuth2)

This document defines the internal service interfaces for the application. Since this is a desktop application (not a web service), contracts are defined as Python Protocol classes rather than REST/GraphQL APIs.

## AuthService

Handles OAuth2 browser-based authentication with Google.

```python
from typing import Protocol, Callable
from models import UserSession, AuthState

class AuthService(Protocol):
    """Service for OAuth2 authentication."""

    @property
    def state(self) -> AuthState:
        """Current authentication state."""
        ...

    @property
    def current_user(self) -> UserSession | None:
        """Current authenticated user, or None if signed out."""
        ...

    def sign_in(
        self,
        on_browser_opened: Callable[[], None] | None = None,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None
    ) -> None:
        """
        Initiate browser-based sign-in flow.

        Opens user's default browser to Google OAuth2 consent page.
        Starts local HTTP server to receive callback.
        Runs in background thread; use callbacks for results.

        Args:
            on_browser_opened: Called when browser opens (for UI feedback)
            on_success: Called with UserSession on successful sign-in
            on_error: Called with exception on failure

        Raises:
            AuthenticationError: If already signing in
        """
        ...

    def sign_out(
        self,
        on_complete: Callable[[], None] | None = None
    ) -> None:
        """
        Sign out and clear stored credentials.

        Args:
            on_complete: Called when sign-out completes
        """
        ...

    def refresh_token(
        self,
        on_success: Callable[[UserSession], None] | None = None,
        on_error: Callable[[Exception], None] | None = None
    ) -> None:
        """
        Refresh the access token using stored refresh token.

        Runs in background thread.

        Args:
            on_success: Called with updated UserSession
            on_error: Called if refresh fails (user must sign in again)
        """
        ...

    def load_stored_credentials(self) -> UserSession | None:
        """
        Load credentials from secure storage.

        Called on application startup.

        Returns:
            UserSession if valid credentials exist, None otherwise
        """
        ...

    def get_credentials(self) -> 'google.oauth2.credentials.Credentials':
        """
        Get credentials object for GCS client.

        Automatically refreshes if needed.

        Returns:
            Credentials object for google-cloud-storage

        Raises:
            AuthenticationError: If not authenticated
        """
        ...

    def ensure_authenticated(
        self,
        on_authenticated: Callable[[UserSession], None],
        on_sign_in_required: Callable[[], None]
    ) -> None:
        """
        Ensure user is authenticated before operation.

        If authenticated, calls on_authenticated immediately.
        If not, calls on_sign_in_required (UI should show sign-in prompt).

        Args:
            on_authenticated: Called if already authenticated
            on_sign_in_required: Called if sign-in needed
        """
        ...
```

## LocalFilesystemService

Handles all local file system operations.

```python
from typing import Protocol, Iterator
from pathlib import Path
from models import FileItem

class LocalFilesystemService(Protocol):
    """Service for local filesystem operations."""

    def list_directory(self, path: Path) -> list[FileItem]:
        """
        List contents of a directory.

        Args:
            path: Absolute path to directory

        Returns:
            List of FileItem objects for directory contents

        Raises:
            FileSystemError: If path doesn't exist or isn't accessible
        """
        ...

    def get_file_info(self, path: Path) -> FileItem:
        """
        Get detailed information about a single file/directory.

        Args:
            path: Absolute path to file or directory

        Returns:
            FileItem with full metadata

        Raises:
            FileSystemError: If path doesn't exist
        """
        ...

    def copy_file(
        self,
        source: Path,
        destination: Path,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> None:
        """
        Copy a file to destination.

        Args:
            source: Source file path
            destination: Destination file path
            progress_callback: Optional callback(bytes_copied, total_bytes)

        Raises:
            FileSystemError: On copy failure
        """
        ...

    def copy_directory(
        self,
        source: Path,
        destination: Path,
        progress_callback: Callable[[str, int, int], None] | None = None
    ) -> None:
        """
        Recursively copy a directory.

        Args:
            source: Source directory path
            destination: Destination directory path
            progress_callback: Optional callback(current_file, files_done, total_files)

        Raises:
            FileSystemError: On copy failure
        """
        ...

    def move_file(self, source: Path, destination: Path) -> None:
        """
        Move a file to destination.

        Args:
            source: Source file path
            destination: Destination file path

        Raises:
            FileSystemError: On move failure
        """
        ...

    def delete_file(self, path: Path) -> None:
        """
        Delete a file.

        Args:
            path: File path to delete

        Raises:
            FileSystemError: On delete failure
        """
        ...

    def delete_directory(self, path: Path) -> None:
        """
        Recursively delete a directory.

        Args:
            path: Directory path to delete

        Raises:
            FileSystemError: On delete failure
        """
        ...

    def exists(self, path: Path) -> bool:
        """Check if path exists."""
        ...

    def get_home_directory(self) -> Path:
        """Get user's home directory."""
        ...
```

## GCSClientService

Handles all Google Cloud Storage operations.

```python
from typing import Protocol, Iterator
from models import GCSObject, GCSBucket

class GCSClientService(Protocol):
    """Service for GCS operations."""

    def set_credentials(self, credentials: 'google.oauth2.credentials.Credentials') -> None:
        """
        Set credentials for GCS operations.

        Called after successful authentication.

        Args:
            credentials: OAuth2 credentials from AuthService
        """
        ...

    def is_authenticated(self) -> bool:
        """Check if credentials are set and valid."""
        ...

    def list_buckets(self, project_id: str) -> list[GCSBucket]:
        """
        List all buckets in a project.

        Args:
            project_id: GCP project ID

        Returns:
            List of GCSBucket objects

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If no access to project
        """
        ...

    def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        delimiter: str = "/"
    ) -> tuple[list[GCSObject], list[str]]:
        """
        List objects in a bucket with optional prefix.

        Args:
            bucket_name: Bucket name
            prefix: Object name prefix (folder path)
            delimiter: Delimiter for pseudo-folders (usually "/")

        Returns:
            Tuple of (objects, prefixes) where prefixes are "subdirectories"

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If no access to bucket
            NetworkError: On connection failure
        """
        ...

    def get_object_metadata(self, bucket_name: str, object_name: str) -> GCSObject:
        """
        Get detailed metadata for a single object.

        Args:
            bucket_name: Bucket name
            object_name: Full object name

        Returns:
            GCSObject with full metadata

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If no access
        """
        ...

    def upload_file(
        self,
        local_path: Path,
        bucket_name: str,
        object_name: str,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> GCSObject:
        """
        Upload a local file to GCS.

        Uses resumable upload for files >5MB.

        Args:
            local_path: Local file path
            bucket_name: Destination bucket
            object_name: Destination object name
            progress_callback: Optional callback(bytes_uploaded, total_bytes)

        Returns:
            Created GCSObject

        Raises:
            AuthenticationError: If not authenticated
            TransferError: On upload failure
        """
        ...

    def download_file(
        self,
        bucket_name: str,
        object_name: str,
        local_path: Path,
        progress_callback: Callable[[int, int], None] | None = None
    ) -> None:
        """
        Download a GCS object to local file.

        Args:
            bucket_name: Source bucket
            object_name: Source object name
            local_path: Destination local path
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Raises:
            AuthenticationError: If not authenticated
            TransferError: On download failure
        """
        ...

    def copy_object(
        self,
        source_bucket: str,
        source_name: str,
        dest_bucket: str,
        dest_name: str
    ) -> GCSObject:
        """
        Copy object within GCS (server-side copy).

        Args:
            source_bucket: Source bucket name
            source_name: Source object name
            dest_bucket: Destination bucket name
            dest_name: Destination object name

        Returns:
            Created GCSObject

        Raises:
            AuthenticationError: If not authenticated
            TransferError: On copy failure
        """
        ...

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """
        Delete a GCS object.

        Args:
            bucket_name: Bucket name
            object_name: Object name

        Raises:
            AuthenticationError: If not authenticated
            PermissionError: If no delete access
        """
        ...

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check if object exists."""
        ...
```

## TransferManagerService

Orchestrates file transfer operations across local and GCS.

```python
from typing import Protocol, Callable
from models import TransferOperation, FileItem, GCSObject, TransferDestination, ConflictResolution

class TransferManagerService(Protocol):
    """Service for managing file transfers."""

    def copy(
        self,
        items: list[FileItem | GCSObject],
        destination: TransferDestination,
        conflict_resolution: ConflictResolution = ConflictResolution.ASK,
        on_progress: Callable[[TransferOperation], None] | None = None,
        on_conflict: Callable[[str, str], ConflictResolution] | None = None,
        on_complete: Callable[[TransferOperation], None] | None = None,
        on_error: Callable[[TransferOperation, Exception], None] | None = None,
        on_auth_required: Callable[[], None] | None = None
    ) -> TransferOperation:
        """
        Start a copy operation.

        Args:
            items: Files/objects to copy
            destination: Target location
            conflict_resolution: Default conflict handling
            on_progress: Progress update callback
            on_conflict: Called when file exists at destination
            on_complete: Called when operation completes
            on_error: Called on errors
            on_auth_required: Called if GCS operation needs authentication

        Returns:
            TransferOperation tracking the copy
        """
        ...

    def move(
        self,
        items: list[FileItem | GCSObject],
        destination: TransferDestination,
        conflict_resolution: ConflictResolution = ConflictResolution.ASK,
        on_progress: Callable[[TransferOperation], None] | None = None,
        on_conflict: Callable[[str, str], ConflictResolution] | None = None,
        on_complete: Callable[[TransferOperation], None] | None = None,
        on_error: Callable[[TransferOperation, Exception], None] | None = None,
        on_auth_required: Callable[[], None] | None = None
    ) -> TransferOperation:
        """
        Start a move operation (copy + delete source).

        Args:
            items: Files/objects to move
            destination: Target location
            conflict_resolution: Default conflict handling
            on_progress: Progress update callback
            on_conflict: Called when file exists at destination
            on_complete: Called when operation completes
            on_error: Called on errors
            on_auth_required: Called if GCS operation needs authentication

        Returns:
            TransferOperation tracking the move
        """
        ...

    def delete(
        self,
        items: list[FileItem | GCSObject],
        on_progress: Callable[[int, int], None] | None = None,
        on_complete: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_auth_required: Callable[[], None] | None = None
    ) -> None:
        """
        Delete files/objects.

        Args:
            items: Files/objects to delete
            on_progress: Callback(deleted_count, total_count)
            on_complete: Called when all deleted
            on_error: Called on errors
            on_auth_required: Called if GCS operation needs authentication
        """
        ...

    def cancel(self, operation: TransferOperation) -> None:
        """
        Cancel an in-progress operation.

        Args:
            operation: Operation to cancel
        """
        ...

    def pause(self, operation: TransferOperation) -> None:
        """
        Pause an in-progress operation.

        Args:
            operation: Operation to pause
        """
        ...

    def resume(self, operation: TransferOperation) -> None:
        """
        Resume a paused operation.

        Args:
            operation: Operation to resume
        """
        ...

    def get_active_operations(self) -> list[TransferOperation]:
        """Get all active (running/paused) operations."""
        ...

    @property
    def max_concurrent(self) -> int:
        """Maximum concurrent transfers."""
        ...

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        """Set maximum concurrent transfers (1-10)."""
        ...
```

## ConfigManagerService

Handles configuration loading and saving.

```python
from typing import Protocol
from pathlib import Path
from models import Configuration, ProjectConfig

class ConfigManagerService(Protocol):
    """Service for configuration management."""

    def load(self) -> Configuration:
        """
        Load configuration from disk.

        Returns:
            Configuration object (defaults if file doesn't exist)
        """
        ...

    def save(self, config: Configuration) -> None:
        """
        Save configuration to disk.

        Args:
            config: Configuration to save

        Raises:
            ConfigurationError: On save failure
        """
        ...

    def get_config_directory(self) -> Path:
        """Get platform-appropriate config directory path."""
        ...

    def add_project(self, project: ProjectConfig) -> None:
        """
        Add a GCP project to configuration.

        Args:
            project: Project configuration to add
        """
        ...

    def remove_project(self, project_id: str) -> None:
        """
        Remove a GCP project from configuration.

        Args:
            project_id: Project ID to remove
        """
        ...

    def get_projects(self) -> list[ProjectConfig]:
        """Get all configured projects."""
        ...
```

## PlatformService

Handles platform-specific functionality.

```python
from typing import Protocol
from pathlib import Path

class PlatformService(Protocol):
    """Service for platform-specific operations."""

    def get_config_directory(self) -> Path:
        """
        Get platform-appropriate config directory.

        Returns:
            ~/.config/morton-com on macOS
            %APPDATA%/morton-com on Windows
        """
        ...

    def get_modifier_key(self) -> str:
        """
        Get platform modifier key name.

        Returns:
            "Cmd" on macOS, "Ctrl" on Windows
        """
        ...

    def get_modifier_symbol(self) -> str:
        """
        Get platform modifier key symbol.

        Returns:
            "⌘" on macOS, "Ctrl+" on Windows
        """
        ...

    def get_dialog_button_order(self) -> tuple[str, str]:
        """
        Get platform-appropriate dialog button order.

        Returns:
            ("Cancel", "OK") on macOS
            ("OK", "Cancel") on Windows
        """
        ...

    def is_dark_mode(self) -> bool:
        """
        Detect system dark mode preference.

        Returns:
            True if dark mode enabled
        """
        ...

    def get_default_font_family(self) -> str:
        """
        Get platform default UI font.

        Returns:
            Font family name appropriate for platform
        """
        ...

    def open_browser(self, url: str) -> None:
        """
        Open URL in default browser.

        Used for OAuth2 authentication flow.

        Args:
            url: URL to open
        """
        ...

    def open_file_externally(self, path: Path) -> None:
        """
        Open file with default system application.

        Args:
            path: File path to open
        """
        ...

    def reveal_in_finder(self, path: Path) -> None:
        """
        Reveal file in system file manager.

        Args:
            path: File path to reveal
        """
        ...
```

## CredentialStorageService

Handles secure storage of OAuth2 credentials.

```python
from typing import Protocol
from models import UserSession

class CredentialStorageService(Protocol):
    """Service for secure credential storage."""

    def save(self, session: UserSession) -> None:
        """
        Save user session credentials securely.

        Encrypts tokens before storage using platform keyring.

        Args:
            session: UserSession to save

        Raises:
            ConfigurationError: On save failure
        """
        ...

    def load(self) -> UserSession | None:
        """
        Load stored credentials.

        Decrypts tokens using platform keyring.

        Returns:
            UserSession if valid credentials exist, None otherwise
        """
        ...

    def clear(self) -> None:
        """
        Remove stored credentials.

        Called on sign-out.
        """
        ...

    def has_credentials(self) -> bool:
        """Check if credentials are stored."""
        ...
```

## Error Types

```python
class MortonError(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        user_message: str,
        suggested_action: str,
        technical_detail: str = ""
    ):
        super().__init__(message)
        self.user_message = user_message
        self.suggested_action = suggested_action
        self.technical_detail = technical_detail


class AuthenticationError(MortonError):
    """GCP credentials not available or invalid."""
    pass


class PermissionError(MortonError):
    """Access denied to resource."""
    pass


class NetworkError(MortonError):
    """Network connectivity or timeout issue."""
    pass


class TransferError(MortonError):
    """File transfer operation failed."""
    pass


class ConfigurationError(MortonError):
    """Configuration file error."""
    pass


class FileSystemError(MortonError):
    """Local filesystem operation error."""
    pass
```

## Callback Patterns

All long-running operations use callbacks for progress reporting. The UI layer schedules these callbacks to run on the main thread using `tkinter.after()`.

```python
# Progress callback types
ProgressCallback = Callable[[int, int], None]  # (current, total)
FileProgressCallback = Callable[[str, int, int], None]  # (filename, current, total)
OperationProgressCallback = Callable[[TransferOperation], None]
ConflictCallback = Callable[[str, str], ConflictResolution]  # (source, dest) -> resolution
CompletionCallback = Callable[[], None]
ErrorCallback = Callable[[Exception], None]
AuthRequiredCallback = Callable[[], None]  # Called when GCS op needs sign-in
```

## Thread Safety

- All service methods are designed to be called from worker threads
- UI callbacks must be marshaled to main thread via `root.after()`
- `TransferOperation` objects are thread-safe for status reads
- `UserSession` is immutable after creation; state changes create new instances
- Configuration changes trigger save on main thread
- AuthService manages auth state transitions atomically
