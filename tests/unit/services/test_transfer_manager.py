"""Unit tests for TransferManager service.

Tests cover:
- Constructor and property validation
- Copy, move, delete operations
- Internal methods for different transfer directions
- Conflict resolution
- Callbacks and status management
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest

from src.errors import TransferError
from src.models import ConflictResolution, OperationType, SourceType, TransferStatus
from src.models.file_item import FileItem
from src.models.gcs_object import GCSObject
from src.models.transfer_operation import TransferDestination, TransferOperation
from src.services.gcs_client import GCSClient
from src.services.local_filesystem import LocalFilesystem
from src.services.transfer_manager import TransferManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_local_fs() -> LocalFilesystem:
    """Create a mock LocalFilesystem with auto-spec."""
    return create_autospec(LocalFilesystem, instance=True)


@pytest.fixture
def mock_gcs_client() -> GCSClient:
    """Create a mock GCSClient with auto-spec."""
    return create_autospec(GCSClient, instance=True)


@pytest.fixture
def sample_file_item(tmp_path: Path) -> FileItem:
    """Create a sample FileItem for testing."""
    return FileItem(
        name="test.txt",
        path=tmp_path / "test.txt",
        size=1024,
        modified_date=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        created_date=datetime(2026, 1, 10, 8, 0, 0, tzinfo=timezone.utc),
        is_directory=False,
        permissions="rw-r--r--",
        is_hidden=False,
    )


@pytest.fixture
def sample_directory_item(tmp_path: Path) -> FileItem:
    """Create a sample directory FileItem for testing."""
    return FileItem(
        name="subdir",
        path=tmp_path / "subdir",
        size=0,
        modified_date=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        created_date=datetime(2026, 1, 10, 8, 0, 0, tzinfo=timezone.utc),
        is_directory=True,
        permissions="rwxr-xr-x",
        is_hidden=False,
    )


@pytest.fixture
def sample_gcs_object() -> GCSObject:
    """Create a sample GCSObject for testing."""
    return GCSObject(
        name="path/to/file.txt",
        bucket_name="test-bucket",
        size=2048,
        content_type="text/plain",
        storage_class="STANDARD",
        created_time=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        updated_time=datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        generation=1234567890,
    )


@pytest.fixture
def sample_gcs_prefix() -> GCSObject:
    """Create a sample GCS prefix (pseudo-directory) for testing."""
    return GCSObject(
        name="path/to/folder/",
        bucket_name="test-bucket",
        size=0,
        content_type="",
        storage_class="STANDARD",
        created_time=datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        updated_time=datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        generation=0,
    )


@pytest.fixture
def local_destination(tmp_path: Path) -> TransferDestination:
    """Create a local TransferDestination."""
    return TransferDestination(
        type=SourceType.LOCAL,
        path=str(tmp_path / "dest"),
    )


@pytest.fixture
def gcs_destination() -> TransferDestination:
    """Create a GCS TransferDestination."""
    return TransferDestination(
        type=SourceType.GCS_BUCKET,
        path="dest/prefix/",
        bucket_name="dest-bucket",
        project_id="test-project",
    )


@pytest.fixture
def transfer_manager(mock_local_fs: LocalFilesystem) -> TransferManager:
    """Create a TransferManager with mocked LocalFilesystem."""
    return TransferManager(local_fs=mock_local_fs, max_concurrent=3)


@pytest.fixture
def transfer_manager_with_gcs(
    mock_local_fs: LocalFilesystem,
    mock_gcs_client: GCSClient,
) -> TransferManager:
    """Create a TransferManager with both mocked LocalFilesystem and GCSClient."""
    return TransferManager(
        local_fs=mock_local_fs,
        gcs_client=mock_gcs_client,
        max_concurrent=3,
    )


# ---------------------------------------------------------------------------
# Test 1: Constructor sets local_fs and max_concurrent
# ---------------------------------------------------------------------------


class TestConstructor:
    """Tests for TransferManager.__init__."""

    def test_constructor_sets_local_fs_and_max_concurrent(
        self,
        mock_local_fs: LocalFilesystem,
    ) -> None:
        """Constructor should set local_fs and max_concurrent correctly."""
        manager = TransferManager(local_fs=mock_local_fs, max_concurrent=5)

        assert manager._local_fs is mock_local_fs
        assert manager.max_concurrent == 5
        assert manager._gcs_client is None

    def test_constructor_with_gcs_client(
        self,
        mock_local_fs: LocalFilesystem,
        mock_gcs_client: GCSClient,
    ) -> None:
        """Constructor should accept optional gcs_client."""
        manager = TransferManager(
            local_fs=mock_local_fs,
            gcs_client=mock_gcs_client,
            max_concurrent=3,
        )

        assert manager._local_fs is mock_local_fs
        assert manager._gcs_client is mock_gcs_client
        assert manager.max_concurrent == 3

    def test_constructor_defaults(self, mock_local_fs: LocalFilesystem) -> None:
        """Constructor should use default max_concurrent of 3."""
        manager = TransferManager(local_fs=mock_local_fs)

        assert manager.max_concurrent == 3


# ---------------------------------------------------------------------------
# Test 2: max_concurrent property clamps to 1-10
# ---------------------------------------------------------------------------


class TestMaxConcurrentProperty:
    """Tests for max_concurrent property clamping."""

    def test_max_concurrent_clamps_below_minimum(
        self,
        mock_local_fs: LocalFilesystem,
    ) -> None:
        """max_concurrent should clamp values below 1 to 1."""
        manager = TransferManager(local_fs=mock_local_fs, max_concurrent=3)
        manager.max_concurrent = 0

        assert manager.max_concurrent == 1

    def test_max_concurrent_clamps_negative(
        self,
        mock_local_fs: LocalFilesystem,
    ) -> None:
        """max_concurrent should clamp negative values to 1."""
        manager = TransferManager(local_fs=mock_local_fs, max_concurrent=3)
        manager.max_concurrent = -5

        assert manager.max_concurrent == 1

    def test_max_concurrent_clamps_above_maximum(
        self,
        mock_local_fs: LocalFilesystem,
    ) -> None:
        """max_concurrent should clamp values above 10 to 10."""
        manager = TransferManager(local_fs=mock_local_fs, max_concurrent=3)
        manager.max_concurrent = 15

        assert manager.max_concurrent == 10

    def test_max_concurrent_accepts_valid_range(
        self,
        mock_local_fs: LocalFilesystem,
    ) -> None:
        """max_concurrent should accept values within 1-10."""
        manager = TransferManager(local_fs=mock_local_fs, max_concurrent=3)

        manager.max_concurrent = 1
        assert manager.max_concurrent == 1

        manager.max_concurrent = 5
        assert manager.max_concurrent == 5

        manager.max_concurrent = 10
        assert manager.max_concurrent == 10


# ---------------------------------------------------------------------------
# Test 3: copy() returns TransferOperation with correct fields
# ---------------------------------------------------------------------------


class TestCopyMethod:
    """Tests for the copy() method."""

    def test_copy_returns_transfer_operation(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """copy() should return a TransferOperation with correct fields."""
        items = [sample_file_item]
        operation = transfer_manager.copy(
            items=items,
            destination=local_destination,
            conflict_resolution=ConflictResolution.OVERWRITE,
        )

        assert isinstance(operation, TransferOperation)
        assert operation.operation_type == OperationType.COPY
        assert operation.source_items == items
        assert operation.destination == local_destination
        # Status may be PENDING or RUNNING depending on executor timing
        assert operation.status in (TransferStatus.PENDING, TransferStatus.RUNNING, TransferStatus.COMPLETED)
        assert operation.files_total == 1
        assert operation.total_bytes == sample_file_item.size
        assert operation.started_at is not None

    def test_copy_operation_id_is_unique(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """Each copy operation should have a unique ID."""
        op1 = transfer_manager.copy([sample_file_item], local_destination)
        op2 = transfer_manager.copy([sample_file_item], local_destination)

        assert op1.id != op2.id


# ---------------------------------------------------------------------------
# Test 4: _run_copy with local to local (mock LocalFilesystem)
# ---------------------------------------------------------------------------


class TestRunCopyLocalToLocal:
    """Tests for _run_copy with local-to-local transfers."""

    def test_run_copy_local_to_local_calls_copy_file(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
        tmp_path: Path,
    ) -> None:
        """_run_copy should call copy_file for file items."""
        items = [sample_file_item]
        op = transfer_manager._create_operation(
            OperationType.COPY, items, local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        mock_local_fs.copy_file.assert_called_once()
        assert op.status == TransferStatus.COMPLETED

    def test_run_copy_local_to_local_calls_copy_directory(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_directory_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should call copy_directory for directory items."""
        items = [sample_directory_item]
        op = transfer_manager._create_operation(
            OperationType.COPY, items, local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        mock_local_fs.copy_directory.assert_called_once()
        assert op.status == TransferStatus.COMPLETED


# ---------------------------------------------------------------------------
# Test 5: _run_copy sets status COMPLETED on success
# ---------------------------------------------------------------------------


class TestRunCopyStatus:
    """Tests for _run_copy status transitions."""

    def test_run_copy_sets_completed_on_success(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should set status to COMPLETED on success."""
        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        assert op.status == TransferStatus.COMPLETED
        assert op.progress_percent == 100.0
        assert op.completed_at is not None


# ---------------------------------------------------------------------------
# Test 6: _run_copy sets status FAILED on exception
# ---------------------------------------------------------------------------


class TestRunCopyFailure:
    """Tests for _run_copy error handling."""

    def test_run_copy_sets_failed_on_exception(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should set status to FAILED on exception."""
        mock_local_fs.copy_file.side_effect = Exception("Copy failed")

        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        assert op.status == TransferStatus.FAILED
        assert "Copy failed" in op.error_message


# ---------------------------------------------------------------------------
# Test 7: _run_copy calls on_progress, on_complete callbacks
# ---------------------------------------------------------------------------


class TestRunCopyCallbacks:
    """Tests for _run_copy callback invocations."""

    def test_run_copy_calls_on_progress(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should call on_progress callback."""
        on_progress = MagicMock()

        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=on_progress,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        on_progress.assert_called()
        call_args = on_progress.call_args[0]
        assert call_args[0] == op

    def test_run_copy_calls_on_complete(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should call on_complete callback on success."""
        on_complete = MagicMock()

        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=on_complete,
            on_error=None,
            on_auth_required=None,
        )

        on_complete.assert_called_once_with(op)

    def test_run_copy_calls_on_error(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should call on_error callback on failure."""
        error = Exception("Test error")
        mock_local_fs.copy_file.side_effect = error
        on_error = MagicMock()

        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=on_error,
            on_auth_required=None,
        )

        on_error.assert_called_once()
        call_args = on_error.call_args[0]
        assert call_args[0] == op
        assert isinstance(call_args[1], Exception)


# ---------------------------------------------------------------------------
# Test 8: _run_copy handles CANCELLED status
# ---------------------------------------------------------------------------


class TestRunCopyCancellation:
    """Tests for _run_copy cancellation handling."""

    def test_run_copy_stops_on_cancelled_status(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_copy should stop processing when status is CANCELLED."""
        items = [sample_file_item, sample_file_item]
        op = transfer_manager._create_operation(
            OperationType.COPY, items, local_destination,
        )

        # Set up mock to cancel after first item
        def cancel_after_first(*args: Any, **kwargs: Any) -> None:
            op.status = TransferStatus.CANCELLED

        mock_local_fs.copy_file.side_effect = cancel_after_first

        transfer_manager._run_copy(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        # Should only be called once because cancelled after first
        assert mock_local_fs.copy_file.call_count == 1
        assert op.status == TransferStatus.CANCELLED


# ---------------------------------------------------------------------------
# Test 9: move() returns TransferOperation with MOVE type
# ---------------------------------------------------------------------------


class TestMoveMethod:
    """Tests for the move() method."""

    def test_move_returns_transfer_operation_with_move_type(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """move() should return a TransferOperation with MOVE type."""
        items = [sample_file_item]
        operation = transfer_manager.move(
            items=items,
            destination=local_destination,
            conflict_resolution=ConflictResolution.OVERWRITE,
        )

        assert isinstance(operation, TransferOperation)
        assert operation.operation_type == OperationType.MOVE
        assert operation.source_items == items
        assert operation.destination == local_destination


# ---------------------------------------------------------------------------
# Test 10: _run_move copies then deletes
# ---------------------------------------------------------------------------


class TestRunMove:
    """Tests for _run_move internal method."""

    def test_run_move_copies_then_deletes(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """_run_move should copy items then delete sources."""
        op = transfer_manager._create_operation(
            OperationType.MOVE, [sample_file_item], local_destination,
        )

        transfer_manager._run_move(
            op=op,
            conflict_resolution=ConflictResolution.OVERWRITE,
            on_progress=None,
            on_conflict=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        # Should call copy_file then delete_file
        mock_local_fs.copy_file.assert_called_once()
        mock_local_fs.delete_file.assert_called_once()
        assert op.status == TransferStatus.COMPLETED


# ---------------------------------------------------------------------------
# Test 11: delete() calls _delete_single_item for each item
# ---------------------------------------------------------------------------


class TestDeleteMethod:
    """Tests for the delete() method."""

    def test_delete_calls_delete_single_item_for_each(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
    ) -> None:
        """delete() should call _delete_single_item for each item."""
        items = [sample_file_item, sample_file_item]

        # Run delete synchronously by calling _run_delete directly
        transfer_manager._run_delete(
            items=items,
            on_progress=None,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        assert mock_local_fs.delete_file.call_count == 2

    def test_delete_calls_on_progress(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
    ) -> None:
        """delete() should call on_progress callback."""
        on_progress = MagicMock()
        items = [sample_file_item, sample_file_item]

        transfer_manager._run_delete(
            items=items,
            on_progress=on_progress,
            on_complete=None,
            on_error=None,
            on_auth_required=None,
        )

        assert on_progress.call_count == 2
        # Check the calls: (current, total)
        on_progress.assert_any_call(1, 2)
        on_progress.assert_any_call(2, 2)

    def test_delete_calls_on_complete(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
    ) -> None:
        """delete() should call on_complete callback."""
        on_complete = MagicMock()

        transfer_manager._run_delete(
            items=[sample_file_item],
            on_progress=None,
            on_complete=on_complete,
            on_error=None,
            on_auth_required=None,
        )

        on_complete.assert_called_once()


# ---------------------------------------------------------------------------
# Test 12: cancel() sets operation status to CANCELLED
# ---------------------------------------------------------------------------


class TestCancelMethod:
    """Tests for the cancel() method."""

    def test_cancel_sets_status_to_cancelled(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """cancel() should set operation status to CANCELLED."""
        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )
        op.status = TransferStatus.RUNNING

        transfer_manager.cancel(op)

        assert op.status == TransferStatus.CANCELLED


# ---------------------------------------------------------------------------
# Test 13: get_active_operations() returns running/pending/paused ops
# ---------------------------------------------------------------------------


class TestGetActiveOperations:
    """Tests for get_active_operations() method."""

    def test_get_active_operations_returns_running_pending_paused(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        local_destination: TransferDestination,
    ) -> None:
        """get_active_operations() should return running, pending, and paused ops."""
        # Create operations with different statuses
        op_pending = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )
        op_pending.status = TransferStatus.PENDING

        op_running = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )
        op_running.status = TransferStatus.RUNNING

        op_paused = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )
        op_paused.status = TransferStatus.PAUSED

        op_completed = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )
        op_completed.status = TransferStatus.COMPLETED

        op_failed = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], local_destination,
        )
        op_failed.status = TransferStatus.FAILED

        active = transfer_manager.get_active_operations()

        assert op_pending in active
        assert op_running in active
        assert op_paused in active
        assert op_completed not in active
        assert op_failed not in active
        assert len(active) == 3


# ---------------------------------------------------------------------------
# Test 14: _copy_local_to_local with conflict SKIP
# ---------------------------------------------------------------------------


class TestCopyLocalToLocalConflicts:
    """Tests for _copy_local_to_local conflict handling."""

    def test_copy_local_to_local_skip_conflict(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        tmp_path: Path,
    ) -> None:
        """_copy_local_to_local should skip when conflict resolution is SKIP."""
        # Create real files for the test
        source_file = tmp_path / "source.txt"
        source_file.write_text("source content")
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        dest_file = dest_dir / "source.txt"
        dest_file.write_text("existing content")

        item = FileItem(
            name="source.txt",
            path=source_file,
            size=14,
            modified_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
            is_directory=False,
            permissions="rw-r--r--",
            is_hidden=False,
        )

        dest = TransferDestination(type=SourceType.LOCAL, path=str(dest_dir))
        op = transfer_manager._create_operation(OperationType.COPY, [item], dest)

        transfer_manager._copy_local_to_local(
            item=item,
            dest=dest,
            op=op,
            conflict_res=ConflictResolution.SKIP,
            on_conflict=None,
        )

        # Should not call copy_file when skipping
        mock_local_fs.copy_file.assert_not_called()


# ---------------------------------------------------------------------------
# Test 15: _copy_local_to_local with conflict RENAME
# ---------------------------------------------------------------------------


class TestCopyLocalToLocalRename:
    """Tests for _copy_local_to_local with RENAME conflict resolution."""

    def test_copy_local_to_local_rename_conflict(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        tmp_path: Path,
    ) -> None:
        """_copy_local_to_local should use renamed path when conflict resolution is RENAME."""
        # Create real files for the test
        source_file = tmp_path / "source.txt"
        source_file.write_text("source content")
        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        dest_file = dest_dir / "source.txt"
        dest_file.write_text("existing content")

        item = FileItem(
            name="source.txt",
            path=source_file,
            size=14,
            modified_date=datetime.now(timezone.utc),
            created_date=datetime.now(timezone.utc),
            is_directory=False,
            permissions="rw-r--r--",
            is_hidden=False,
        )

        dest = TransferDestination(type=SourceType.LOCAL, path=str(dest_dir))
        op = transfer_manager._create_operation(OperationType.COPY, [item], dest)

        transfer_manager._copy_local_to_local(
            item=item,
            dest=dest,
            op=op,
            conflict_res=ConflictResolution.RENAME,
            on_conflict=None,
        )

        # Should call copy_file with renamed destination
        mock_local_fs.copy_file.assert_called_once()
        call_args = mock_local_fs.copy_file.call_args
        dest_path = call_args[0][1]
        assert "source (1).txt" in str(dest_path)


# ---------------------------------------------------------------------------
# Test 16: _copy_local_to_gcs uploads files (mock GCSClient)
# ---------------------------------------------------------------------------


class TestCopyLocalToGcs:
    """Tests for _copy_local_to_gcs method."""

    def test_copy_local_to_gcs_uploads_file(
        self,
        transfer_manager_with_gcs: TransferManager,
        mock_gcs_client: GCSClient,
        sample_file_item: FileItem,
        gcs_destination: TransferDestination,
    ) -> None:
        """_copy_local_to_gcs should upload files to GCS."""
        op = transfer_manager_with_gcs._create_operation(
            OperationType.COPY, [sample_file_item], gcs_destination,
        )

        transfer_manager_with_gcs._copy_local_to_gcs(
            item=sample_file_item,
            dest=gcs_destination,
            op=op,
        )

        mock_gcs_client.upload_file.assert_called_once()
        call_args = mock_gcs_client.upload_file.call_args
        assert call_args[0][0] == sample_file_item.path
        assert call_args[0][1] == gcs_destination.bucket_name

    def test_copy_local_to_gcs_without_client_raises_error(
        self,
        transfer_manager: TransferManager,
        sample_file_item: FileItem,
        gcs_destination: TransferDestination,
    ) -> None:
        """_copy_local_to_gcs should raise TransferError when GCS client is None."""
        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_file_item], gcs_destination,
        )

        with pytest.raises(TransferError) as exc_info:
            transfer_manager._copy_local_to_gcs(
                item=sample_file_item,
                dest=gcs_destination,
                op=op,
            )

        assert "not available" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 17: _copy_gcs_to_local downloads files
# ---------------------------------------------------------------------------


class TestCopyGcsToLocal:
    """Tests for _copy_gcs_to_local method."""

    def test_copy_gcs_to_local_downloads_file(
        self,
        transfer_manager_with_gcs: TransferManager,
        mock_gcs_client: GCSClient,
        sample_gcs_object: GCSObject,
        local_destination: TransferDestination,
    ) -> None:
        """_copy_gcs_to_local should download files from GCS."""
        op = transfer_manager_with_gcs._create_operation(
            OperationType.COPY, [sample_gcs_object], local_destination,
        )

        transfer_manager_with_gcs._copy_gcs_to_local(
            item=sample_gcs_object,
            dest=local_destination,
            op=op,
        )

        mock_gcs_client.download_file.assert_called_once()
        call_args = mock_gcs_client.download_file.call_args
        assert call_args[0][0] == sample_gcs_object.bucket_name
        assert call_args[0][1] == sample_gcs_object.name

    def test_copy_gcs_to_local_without_client_raises_error(
        self,
        transfer_manager: TransferManager,
        sample_gcs_object: GCSObject,
        local_destination: TransferDestination,
    ) -> None:
        """_copy_gcs_to_local should raise TransferError when GCS client is None."""
        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_gcs_object], local_destination,
        )

        with pytest.raises(TransferError) as exc_info:
            transfer_manager._copy_gcs_to_local(
                item=sample_gcs_object,
                dest=local_destination,
                op=op,
            )

        assert "not available" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 18: _copy_gcs_to_gcs copies within GCS
# ---------------------------------------------------------------------------


class TestCopyGcsToGcs:
    """Tests for _copy_gcs_to_gcs method."""

    def test_copy_gcs_to_gcs_copies_object(
        self,
        transfer_manager_with_gcs: TransferManager,
        mock_gcs_client: GCSClient,
        sample_gcs_object: GCSObject,
        gcs_destination: TransferDestination,
    ) -> None:
        """_copy_gcs_to_gcs should copy objects within GCS."""
        op = transfer_manager_with_gcs._create_operation(
            OperationType.COPY, [sample_gcs_object], gcs_destination,
        )

        transfer_manager_with_gcs._copy_gcs_to_gcs(
            item=sample_gcs_object,
            dest=gcs_destination,
            op=op,
        )

        mock_gcs_client.copy_object.assert_called_once()
        call_args = mock_gcs_client.copy_object.call_args
        assert call_args[0][0] == sample_gcs_object.bucket_name
        assert call_args[0][1] == sample_gcs_object.name
        assert call_args[0][2] == gcs_destination.bucket_name

    def test_copy_gcs_to_gcs_without_client_raises_error(
        self,
        transfer_manager: TransferManager,
        sample_gcs_object: GCSObject,
        gcs_destination: TransferDestination,
    ) -> None:
        """_copy_gcs_to_gcs should raise TransferError when GCS client is None."""
        op = transfer_manager._create_operation(
            OperationType.COPY, [sample_gcs_object], gcs_destination,
        )

        with pytest.raises(TransferError) as exc_info:
            transfer_manager._copy_gcs_to_gcs(
                item=sample_gcs_object,
                dest=gcs_destination,
                op=op,
            )

        assert "not available" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Test 19: _delete_single_item for FileItem (file and directory)
# ---------------------------------------------------------------------------


class TestDeleteSingleItemFileItem:
    """Tests for _delete_single_item with FileItem."""

    def test_delete_single_item_deletes_file(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_file_item: FileItem,
    ) -> None:
        """_delete_single_item should call delete_file for file items."""
        transfer_manager._delete_single_item(sample_file_item)

        mock_local_fs.delete_file.assert_called_once_with(sample_file_item.path)
        mock_local_fs.delete_directory.assert_not_called()

    def test_delete_single_item_deletes_directory(
        self,
        transfer_manager: TransferManager,
        mock_local_fs: LocalFilesystem,
        sample_directory_item: FileItem,
    ) -> None:
        """_delete_single_item should call delete_directory for directory items."""
        transfer_manager._delete_single_item(sample_directory_item)

        mock_local_fs.delete_directory.assert_called_once_with(
            sample_directory_item.path
        )
        mock_local_fs.delete_file.assert_not_called()


# ---------------------------------------------------------------------------
# Test 20: _delete_single_item for GCSObject
# ---------------------------------------------------------------------------


class TestDeleteSingleItemGcsObject:
    """Tests for _delete_single_item with GCSObject."""

    def test_delete_single_item_deletes_gcs_object(
        self,
        transfer_manager_with_gcs: TransferManager,
        mock_gcs_client: GCSClient,
        sample_gcs_object: GCSObject,
    ) -> None:
        """_delete_single_item should call delete_object for GCS objects."""
        transfer_manager_with_gcs._delete_single_item(sample_gcs_object)

        mock_gcs_client.delete_object.assert_called_once_with(
            sample_gcs_object.bucket_name,
            sample_gcs_object.name,
        )

    def test_delete_single_item_gcs_without_client_raises_error(
        self,
        transfer_manager: TransferManager,
        sample_gcs_object: GCSObject,
    ) -> None:
        """_delete_single_item should raise TransferError when GCS client is None."""
        with pytest.raises(TransferError) as exc_info:
            transfer_manager._delete_single_item(sample_gcs_object)

        assert "not available" in str(exc_info.value)

    def test_delete_single_item_deletes_gcs_prefix(
        self,
        transfer_manager_with_gcs: TransferManager,
        mock_gcs_client: GCSClient,
        sample_gcs_prefix: GCSObject,
        sample_gcs_object: GCSObject,
    ) -> None:
        """_delete_single_item should delete all objects under a GCS prefix."""
        # Mock list_objects to return some objects
        mock_gcs_client.list_objects.return_value = (
            [sample_gcs_object],
            [],
        )

        transfer_manager_with_gcs._delete_single_item(sample_gcs_prefix)

        mock_gcs_client.list_objects.assert_called_once()
        mock_gcs_client.delete_object.assert_called()


# ---------------------------------------------------------------------------
# Test 21: _resolve_conflict returns default if not ASK
# ---------------------------------------------------------------------------


class TestResolveConflict:
    """Tests for _resolve_conflict static method."""

    def test_resolve_conflict_returns_default_if_not_ask(self) -> None:
        """_resolve_conflict should return the default resolution if not ASK."""
        result = TransferManager._resolve_conflict(
            source="/src/file.txt",
            dest="/dst/file.txt",
            default=ConflictResolution.OVERWRITE,
            on_conflict=None,
        )

        assert result == ConflictResolution.OVERWRITE

    def test_resolve_conflict_returns_skip_if_default_skip(self) -> None:
        """_resolve_conflict should return SKIP when default is SKIP."""
        result = TransferManager._resolve_conflict(
            source="/src/file.txt",
            dest="/dst/file.txt",
            default=ConflictResolution.SKIP,
            on_conflict=None,
        )

        assert result == ConflictResolution.SKIP

    def test_resolve_conflict_calls_callback_when_ask(self) -> None:
        """_resolve_conflict should call on_conflict callback when ASK."""
        on_conflict = MagicMock(return_value=ConflictResolution.RENAME)

        result = TransferManager._resolve_conflict(
            source="/src/file.txt",
            dest="/dst/file.txt",
            default=ConflictResolution.ASK,
            on_conflict=on_conflict,
        )

        on_conflict.assert_called_once_with("/src/file.txt", "/dst/file.txt")
        assert result == ConflictResolution.RENAME

    def test_resolve_conflict_returns_overwrite_when_ask_no_callback(self) -> None:
        """_resolve_conflict should return OVERWRITE when ASK but no callback."""
        result = TransferManager._resolve_conflict(
            source="/src/file.txt",
            dest="/dst/file.txt",
            default=ConflictResolution.ASK,
            on_conflict=None,
        )

        assert result == ConflictResolution.OVERWRITE


# ---------------------------------------------------------------------------
# Test 22: _get_renamed_path increments counter
# ---------------------------------------------------------------------------


class TestGetRenamedPath:
    """Tests for _get_renamed_path static method."""

    def test_get_renamed_path_increments_counter(self, tmp_path: Path) -> None:
        """_get_renamed_path should increment counter until unique path found."""
        # Create existing files
        (tmp_path / "file.txt").write_text("original")
        (tmp_path / "file (1).txt").write_text("first copy")

        original_path = tmp_path / "file.txt"
        renamed = TransferManager._get_renamed_path(original_path)

        assert renamed == tmp_path / "file (2).txt"

    def test_get_renamed_path_first_rename(self, tmp_path: Path) -> None:
        """_get_renamed_path should return (1) suffix for first rename."""
        (tmp_path / "file.txt").write_text("original")

        original_path = tmp_path / "file.txt"
        renamed = TransferManager._get_renamed_path(original_path)

        assert renamed == tmp_path / "file (1).txt"

    def test_get_renamed_path_preserves_extension(self, tmp_path: Path) -> None:
        """_get_renamed_path should preserve the file extension."""
        (tmp_path / "document.pdf").write_text("fake pdf")

        original_path = tmp_path / "document.pdf"
        renamed = TransferManager._get_renamed_path(original_path)

        assert renamed == tmp_path / "document (1).pdf"
        assert renamed.suffix == ".pdf"

    def test_get_renamed_path_handles_no_extension(self, tmp_path: Path) -> None:
        """_get_renamed_path should handle files without extension."""
        (tmp_path / "README").write_text("readme content")

        original_path = tmp_path / "README"
        renamed = TransferManager._get_renamed_path(original_path)

        assert renamed == tmp_path / "README (1)"


# ---------------------------------------------------------------------------
# Additional helper method tests
# ---------------------------------------------------------------------------


class TestHelperMethods:
    """Tests for helper methods."""

    def test_update_file_progress(self) -> None:
        """_update_file_progress should update operation progress fields."""
        op = TransferOperation(
            id="test-id",
            operation_type=OperationType.COPY,
            current_file_progress=0.0,
            bytes_transferred=0,
        )

        TransferManager._update_file_progress(op, 500, 1000)

        assert op.current_file_progress == 50.0
        assert op.bytes_transferred == 500

    def test_update_file_progress_zero_total(self) -> None:
        """_update_file_progress should not update when total is 0."""
        op = TransferOperation(
            id="test-id",
            operation_type=OperationType.COPY,
            current_file_progress=25.0,
            bytes_transferred=100,
        )

        TransferManager._update_file_progress(op, 0, 0)

        # Should remain unchanged
        assert op.current_file_progress == 25.0

    def test_count_files(self, sample_file_item: FileItem) -> None:
        """_count_files should return the number of items."""
        items = [sample_file_item, sample_file_item, sample_file_item]

        count = TransferManager._count_files(items)

        assert count == 3

    def test_count_bytes(
        self,
        sample_file_item: FileItem,
        sample_gcs_object: GCSObject,
    ) -> None:
        """_count_bytes should sum sizes of items with size attribute."""
        items = [sample_file_item, sample_gcs_object]

        total = TransferManager._count_bytes(items)

        assert total == sample_file_item.size + sample_gcs_object.size

    def test_count_bytes_empty_list(self) -> None:
        """_count_bytes should return 0 for empty list."""
        total = TransferManager._count_bytes([])

        assert total == 0
