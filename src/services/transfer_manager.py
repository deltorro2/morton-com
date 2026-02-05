"""Transfer manager service for copy, move, and delete operations.

Orchestrates file transfers between local filesystem and GCS, supporting
all four direction combinations. Uses ThreadPoolExecutor for concurrent
transfers.
"""

from __future__ import annotations

import logging
import os
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.errors import TransferError
from src.models import ConflictResolution, OperationType, SourceType, TransferStatus
from src.models.file_item import FileItem
from src.models.gcs_object import GCSObject
from src.models.transfer_operation import TransferDestination, TransferOperation
from src.services.gcs_client import GCSClient
from src.services.local_filesystem import LocalFilesystem

logger = logging.getLogger(__name__)


class TransferManager:
    """Orchestrates file transfer operations across local and GCS."""

    def __init__(
        self,
        local_fs: LocalFilesystem,
        gcs_client: GCSClient | None = None,
        max_concurrent: int = 3,
    ) -> None:
        self._local_fs = local_fs
        self._gcs_client = gcs_client
        self._max_concurrent = max_concurrent
        self._executor = ThreadPoolExecutor(max_workers=max_concurrent)
        self._active_ops: dict[str, TransferOperation] = {}

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        self._max_concurrent = max(1, min(10, value))

    def copy(
        self,
        items: list[FileItem | GCSObject],
        destination: TransferDestination,
        conflict_resolution: ConflictResolution = ConflictResolution.ASK,
        on_progress: Callable[[TransferOperation], None] | None = None,
        on_conflict: Callable[[str, str], ConflictResolution] | None = None,
        on_complete: Callable[[TransferOperation], None] | None = None,
        on_error: Callable[[TransferOperation, Exception], None] | None = None,
        on_auth_required: Callable[[], None] | None = None,
    ) -> TransferOperation:
        """Start a copy operation in a background thread."""
        op = self._create_operation(OperationType.COPY, items, destination)
        self._executor.submit(
            self._run_copy, op, conflict_resolution,
            on_progress, on_conflict, on_complete, on_error, on_auth_required,
        )
        return op

    def move(
        self,
        items: list[FileItem | GCSObject],
        destination: TransferDestination,
        conflict_resolution: ConflictResolution = ConflictResolution.ASK,
        on_progress: Callable[[TransferOperation], None] | None = None,
        on_conflict: Callable[[str, str], ConflictResolution] | None = None,
        on_complete: Callable[[TransferOperation], None] | None = None,
        on_error: Callable[[TransferOperation, Exception], None] | None = None,
        on_auth_required: Callable[[], None] | None = None,
    ) -> TransferOperation:
        """Start a move operation (copy then delete source)."""
        op = self._create_operation(OperationType.MOVE, items, destination)
        self._executor.submit(
            self._run_move, op, conflict_resolution,
            on_progress, on_conflict, on_complete, on_error, on_auth_required,
        )
        return op

    def delete(
        self,
        items: list[FileItem | GCSObject],
        on_progress: Callable[[int, int], None] | None = None,
        on_complete: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        on_auth_required: Callable[[], None] | None = None,
    ) -> None:
        """Delete files/objects in a background thread."""
        self._executor.submit(
            self._run_delete, items, on_progress, on_complete, on_error, on_auth_required,
        )

    def cancel(self, operation: TransferOperation) -> None:
        """Cancel an in-progress operation."""
        operation.status = TransferStatus.CANCELLED

    def get_active_operations(self) -> list[TransferOperation]:
        """Get all active operations."""
        return [
            op for op in self._active_ops.values()
            if op.status in (TransferStatus.RUNNING, TransferStatus.PAUSED, TransferStatus.PENDING)
        ]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_operation(
        self,
        op_type: OperationType,
        items: list,
        destination: TransferDestination,
    ) -> TransferOperation:
        op = TransferOperation(
            id=str(uuid.uuid4()),
            operation_type=op_type,
            source_items=items,
            destination=destination,
            status=TransferStatus.PENDING,
            files_total=self._count_files(items),
            total_bytes=self._count_bytes(items),
            started_at=datetime.now(timezone.utc),
        )
        self._active_ops[op.id] = op
        return op

    def _run_copy(
        self,
        op: TransferOperation,
        conflict_resolution: ConflictResolution,
        on_progress: Callable | None,
        on_conflict: Callable | None,
        on_complete: Callable | None,
        on_error: Callable | None,
        on_auth_required: Callable | None,
    ) -> None:
        op.status = TransferStatus.RUNNING
        try:
            for item in op.source_items:
                if op.status == TransferStatus.CANCELLED:
                    break
                self._copy_single_item(
                    item, op.destination, op, conflict_resolution, on_conflict,
                )
                op.files_completed += 1
                if on_progress:
                    op.progress_percent = (op.files_completed / op.files_total * 100) if op.files_total else 100
                    on_progress(op)

            if op.status != TransferStatus.CANCELLED:
                op.status = TransferStatus.COMPLETED
                op.progress_percent = 100.0
                op.completed_at = datetime.now(timezone.utc)
                if on_complete:
                    on_complete(op)

        except Exception as exc:
            op.status = TransferStatus.FAILED
            op.error_message = str(exc)
            logger.error("Copy failed: %s", exc)
            if on_error:
                on_error(op, exc)
        finally:
            self._active_ops.pop(op.id, None)

    def _run_move(
        self,
        op: TransferOperation,
        conflict_resolution: ConflictResolution,
        on_progress: Callable | None,
        on_conflict: Callable | None,
        on_complete: Callable | None,
        on_error: Callable | None,
        on_auth_required: Callable | None,
    ) -> None:
        """Move = copy + delete source."""
        op.status = TransferStatus.RUNNING
        try:
            # Phase 1: Copy all items
            for item in op.source_items:
                if op.status == TransferStatus.CANCELLED:
                    break
                self._copy_single_item(
                    item, op.destination, op, conflict_resolution, on_conflict,
                )
                op.files_completed += 1
                if on_progress:
                    op.progress_percent = (op.files_completed / op.files_total * 50) if op.files_total else 50
                    on_progress(op)

            if op.status == TransferStatus.CANCELLED:
                return

            # Phase 2: Delete sources
            for item in op.source_items:
                if op.status == TransferStatus.CANCELLED:
                    break
                self._delete_single_item(item)

            op.status = TransferStatus.COMPLETED
            op.progress_percent = 100.0
            op.completed_at = datetime.now(timezone.utc)
            if on_complete:
                on_complete(op)

        except Exception as exc:
            op.status = TransferStatus.FAILED
            op.error_message = str(exc)
            logger.error("Move failed: %s", exc)
            if on_error:
                on_error(op, exc)
        finally:
            self._active_ops.pop(op.id, None)

    def _run_delete(
        self,
        items: list,
        on_progress: Callable | None,
        on_complete: Callable | None,
        on_error: Callable | None,
        on_auth_required: Callable | None,
    ) -> None:
        total = len(items)
        try:
            for idx, item in enumerate(items):
                self._delete_single_item(item)
                if on_progress:
                    on_progress(idx + 1, total)
            if on_complete:
                on_complete()
        except Exception as exc:
            logger.error("Delete failed: %s", exc)
            if on_error:
                on_error(exc)

    def _copy_single_item(
        self,
        item: FileItem | GCSObject,
        dest: TransferDestination,
        op: TransferOperation,
        conflict_resolution: ConflictResolution,
        on_conflict: Callable | None,
    ) -> None:
        """Copy a single item to the destination."""
        if isinstance(item, FileItem):
            if dest.type == SourceType.LOCAL:
                self._copy_local_to_local(item, dest, op, conflict_resolution, on_conflict)
            elif dest.type == SourceType.GCS_BUCKET:
                self._copy_local_to_gcs(item, dest, op)
        elif isinstance(item, GCSObject):
            if dest.type == SourceType.LOCAL:
                self._copy_gcs_to_local(item, dest, op)
            elif dest.type == SourceType.GCS_BUCKET:
                self._copy_gcs_to_gcs(item, dest, op)

    def _copy_local_to_local(
        self,
        item: FileItem,
        dest: TransferDestination,
        op: TransferOperation,
        conflict_res: ConflictResolution,
        on_conflict: Callable | None,
    ) -> None:
        dst_path = Path(dest.path) / item.name
        if dst_path.exists():
            resolution = self._resolve_conflict(
                str(item.path), str(dst_path), conflict_res, on_conflict,
            )
            if resolution == ConflictResolution.SKIP:
                return
            elif resolution == ConflictResolution.RENAME:
                dst_path = self._get_renamed_path(dst_path)

        op.current_file = item.name
        if item.is_directory:
            self._local_fs.copy_directory(item.path, dst_path)
        else:
            self._local_fs.copy_file(
                item.path, dst_path,
                progress_callback=lambda cur, tot: self._update_file_progress(op, cur, tot),
            )

    def _copy_local_to_gcs(
        self,
        item: FileItem,
        dest: TransferDestination,
        op: TransferOperation,
    ) -> None:
        if self._gcs_client is None:
            raise TransferError(
                message="GCS client not available",
                user_message="Cannot upload — not signed in.",
                suggested_action="Sign in with Google first.",
            )
        op.current_file = item.name
        if item.is_directory:
            # Recursive upload
            for root, dirs, files in os.walk(item.path):
                for fname in files:
                    local_file = Path(root) / fname
                    relative = local_file.relative_to(item.path.parent)
                    object_name = dest.path + str(relative).replace(os.sep, "/")
                    self._gcs_client.upload_file(local_file, dest.bucket_name, object_name)
        else:
            object_name = dest.path + item.name
            self._gcs_client.upload_file(
                item.path, dest.bucket_name, object_name,
                progress_callback=lambda cur, tot: self._update_file_progress(op, cur, tot),
            )

    def _copy_gcs_to_local(
        self,
        item: GCSObject,
        dest: TransferDestination,
        op: TransferOperation,
    ) -> None:
        if self._gcs_client is None:
            raise TransferError(
                message="GCS client not available",
                user_message="Cannot download — not signed in.",
                suggested_action="Sign in with Google first.",
            )
        op.current_file = item.display_name
        if item.is_prefix:
            # Download all objects under prefix
            objects, prefixes = self._gcs_client.list_objects(
                item.bucket_name, prefix=item.name, delimiter="",
            )
            for obj in objects:
                relative = obj.name[len(item.name):]
                local_path = Path(dest.path) / relative
                local_path.parent.mkdir(parents=True, exist_ok=True)
                self._gcs_client.download_file(
                    obj.bucket_name, obj.name, local_path,
                )
        else:
            local_path = Path(dest.path) / item.display_name
            self._gcs_client.download_file(
                item.bucket_name, item.name, local_path,
                progress_callback=lambda cur, tot: self._update_file_progress(op, cur, tot),
            )

    def _copy_gcs_to_gcs(
        self,
        item: GCSObject,
        dest: TransferDestination,
        op: TransferOperation,
    ) -> None:
        if self._gcs_client is None:
            raise TransferError(
                message="GCS client not available",
                user_message="Cannot copy — not signed in.",
                suggested_action="Sign in with Google first.",
            )
        op.current_file = item.display_name
        if item.is_prefix:
            objects, _ = self._gcs_client.list_objects(
                item.bucket_name, prefix=item.name, delimiter="",
            )
            for obj in objects:
                relative = obj.name[len(item.name):]
                dest_name = dest.path + relative
                self._gcs_client.copy_object(
                    obj.bucket_name, obj.name, dest.bucket_name, dest_name,
                )
        else:
            dest_name = dest.path + item.display_name
            self._gcs_client.copy_object(
                item.bucket_name, item.name, dest.bucket_name, dest_name,
            )

    def _delete_single_item(self, item: FileItem | GCSObject) -> None:
        if isinstance(item, FileItem):
            if item.is_directory:
                self._local_fs.delete_directory(item.path)
            else:
                self._local_fs.delete_file(item.path)
        elif isinstance(item, GCSObject):
            if self._gcs_client is None:
                raise TransferError(
                    message="GCS client not available",
                    user_message="Cannot delete — not signed in.",
                    suggested_action="Sign in with Google first.",
                )
            if item.is_prefix:
                objects, _ = self._gcs_client.list_objects(
                    item.bucket_name, prefix=item.name, delimiter="",
                )
                for obj in objects:
                    self._gcs_client.delete_object(obj.bucket_name, obj.name)
            else:
                self._gcs_client.delete_object(item.bucket_name, item.name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_conflict(
        source: str,
        dest: str,
        default: ConflictResolution,
        on_conflict: Callable | None,
    ) -> ConflictResolution:
        if default != ConflictResolution.ASK:
            return default
        if on_conflict:
            return on_conflict(source, dest)
        return ConflictResolution.OVERWRITE

    @staticmethod
    def _get_renamed_path(path: Path) -> Path:
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    @staticmethod
    def _update_file_progress(op: TransferOperation, current: int, total: int) -> None:
        if total > 0:
            op.current_file_progress = current / total * 100
            op.bytes_transferred += current

    @staticmethod
    def _count_files(items: list) -> int:
        return len(items)

    @staticmethod
    def _count_bytes(items: list) -> int:
        total = 0
        for item in items:
            if hasattr(item, "size"):
                total += item.size
        return total
