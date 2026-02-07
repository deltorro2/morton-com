"""Unit tests for transfer operation data models."""

from __future__ import annotations

from datetime import datetime, timezone

from src.models import OperationType, SourceType, TransferStatus
from src.models.transfer_operation import TransferDestination, TransferOperation


class TestTransferDestination:
    """Tests for the TransferDestination dataclass."""

    def test_local_destination(self) -> None:
        """TransferDestination with local type has path and empty bucket fields."""
        dest = TransferDestination(
            type=SourceType.LOCAL,
            path="/home/user/downloads",
        )

        assert dest.type == SourceType.LOCAL
        assert dest.path == "/home/user/downloads"
        assert dest.bucket_name == ""
        assert dest.project_id == ""

    def test_gcs_bucket_destination(self) -> None:
        """TransferDestination with GCS_BUCKET type includes bucket_name and project_id."""
        dest = TransferDestination(
            type=SourceType.GCS_BUCKET,
            path="backup/files/",
            bucket_name="my-storage-bucket",
            project_id="gcp-project-123",
        )

        assert dest.type == SourceType.GCS_BUCKET
        assert dest.path == "backup/files/"
        assert dest.bucket_name == "my-storage-bucket"
        assert dest.project_id == "gcp-project-123"


class TestTransferOperation:
    """Tests for the TransferOperation dataclass."""

    def test_required_fields_only(self) -> None:
        """TransferOperation can be created with only required fields (id and operation_type)."""
        op = TransferOperation(
            id="transfer-001",
            operation_type=OperationType.COPY,
        )

        assert op.id == "transfer-001"
        assert op.operation_type == OperationType.COPY
        assert op.source_items == []
        assert op.destination is None

    def test_default_status_is_pending(self) -> None:
        """TransferOperation defaults to PENDING status."""
        op = TransferOperation(
            id="transfer-002",
            operation_type=OperationType.MOVE,
        )

        assert op.status == TransferStatus.PENDING

    def test_all_fields(self) -> None:
        """TransferOperation with all fields explicitly set."""
        destination = TransferDestination(
            type=SourceType.GCS_BUCKET,
            path="archive/",
            bucket_name="backup-bucket",
            project_id="project-456",
        )
        source_items = [{"name": "file1.txt"}, {"name": "file2.txt"}]
        started = datetime(2026, 2, 7, 10, 0, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 2, 7, 10, 5, 0, tzinfo=timezone.utc)

        op = TransferOperation(
            id="transfer-003",
            operation_type=OperationType.COPY,
            source_items=source_items,
            destination=destination,
            status=TransferStatus.COMPLETED,
            progress_percent=100.0,
            current_file="file2.txt",
            current_file_progress=100.0,
            bytes_transferred=5000,
            total_bytes=5000,
            started_at=started,
            completed_at=completed,
            error_message="",
            files_completed=2,
            files_total=2,
        )

        assert op.id == "transfer-003"
        assert op.operation_type == OperationType.COPY
        assert op.source_items == source_items
        assert op.destination == destination
        assert op.status == TransferStatus.COMPLETED
        assert op.progress_percent == 100.0
        assert op.current_file == "file2.txt"
        assert op.current_file_progress == 100.0
        assert op.bytes_transferred == 5000
        assert op.total_bytes == 5000
        assert op.started_at == started
        assert op.completed_at == completed
        assert op.error_message == ""
        assert op.files_completed == 2
        assert op.files_total == 2

    def test_copy_vs_move_operation_type(self) -> None:
        """TransferOperation distinguishes between COPY and MOVE operation types."""
        copy_op = TransferOperation(
            id="copy-op",
            operation_type=OperationType.COPY,
        )
        move_op = TransferOperation(
            id="move-op",
            operation_type=OperationType.MOVE,
        )

        assert copy_op.operation_type == OperationType.COPY
        assert move_op.operation_type == OperationType.MOVE
        assert copy_op.operation_type != move_op.operation_type
        assert copy_op.operation_type.value == "copy"
        assert move_op.operation_type.value == "move"

    def test_progress_fields(self) -> None:
        """TransferOperation tracks progress with multiple fields."""
        op = TransferOperation(
            id="progress-test",
            operation_type=OperationType.COPY,
            progress_percent=45.5,
            current_file="large_video.mp4",
            current_file_progress=72.3,
            bytes_transferred=1_500_000,
            total_bytes=3_300_000,
            files_completed=3,
            files_total=7,
        )

        assert op.progress_percent == 45.5
        assert op.current_file == "large_video.mp4"
        assert op.current_file_progress == 72.3
        assert op.bytes_transferred == 1_500_000
        assert op.total_bytes == 3_300_000
        assert op.files_completed == 3
        assert op.files_total == 7
        # Default values for other fields
        assert op.status == TransferStatus.PENDING
        assert op.error_message == ""

    def test_datetime_fields(self) -> None:
        """TransferOperation datetime fields for started_at and completed_at."""
        # Test with None (default)
        op_pending = TransferOperation(
            id="pending-op",
            operation_type=OperationType.COPY,
        )
        assert op_pending.started_at is None
        assert op_pending.completed_at is None

        # Test with started_at set but not completed
        started = datetime(2026, 2, 7, 14, 30, 0, tzinfo=timezone.utc)
        op_running = TransferOperation(
            id="running-op",
            operation_type=OperationType.MOVE,
            status=TransferStatus.RUNNING,
            started_at=started,
        )
        assert op_running.started_at == started
        assert op_running.completed_at is None

        # Test with both timestamps set
        completed = datetime(2026, 2, 7, 14, 45, 30, tzinfo=timezone.utc)
        op_done = TransferOperation(
            id="done-op",
            operation_type=OperationType.COPY,
            status=TransferStatus.COMPLETED,
            started_at=started,
            completed_at=completed,
        )
        assert op_done.started_at == started
        assert op_done.completed_at == completed
        # Verify time difference
        duration = op_done.completed_at - op_done.started_at
        assert duration.total_seconds() == 930  # 15 minutes and 30 seconds
