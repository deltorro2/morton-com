"""Transfer operation data models.

Defines the destination descriptor and the full transfer-operation state
used to track file copies and moves between local and GCS locations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.models import OperationType, SourceType, TransferStatus


@dataclass
class TransferDestination:
    """Where a transfer operation writes its output.

    Parameters
    ----------
    type:
        Kind of destination (local file-system or GCS).
    path:
        Destination path or object prefix.
    bucket_name:
        Target GCS bucket (empty for local destinations).
    project_id:
        Target Google Cloud project (empty for local destinations).
    """

    type: SourceType
    path: str
    bucket_name: str = ""
    project_id: str = ""


@dataclass
class TransferOperation:
    """Full state of an in-progress or completed transfer.

    Parameters
    ----------
    id:
        Unique operation identifier.
    operation_type:
        Whether this is a copy or move.
    source_items:
        Items being transferred.
    destination:
        Where items are being written.
    status:
        Current lifecycle status.
    progress_percent:
        Overall progress as a percentage (0.0 -- 100.0).
    current_file:
        Name of the file currently being transferred.
    current_file_progress:
        Progress of the current individual file (0.0 -- 100.0).
    bytes_transferred:
        Total bytes transferred so far.
    total_bytes:
        Total bytes expected across all files.
    started_at:
        Timestamp when the operation began, or ``None``.
    completed_at:
        Timestamp when the operation finished, or ``None``.
    error_message:
        Error description if the operation failed.
    files_completed:
        Number of individual files that have finished transferring.
    files_total:
        Total number of individual files in the operation.
    """

    id: str
    operation_type: OperationType
    source_items: list[Any] = field(default_factory=list)
    destination: TransferDestination | None = None
    status: TransferStatus = TransferStatus.PENDING
    progress_percent: float = 0.0
    current_file: str = ""
    current_file_progress: float = 0.0
    bytes_transferred: int = 0
    total_bytes: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str = ""
    files_completed: int = 0
    files_total: int = 0
