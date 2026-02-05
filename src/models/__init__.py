"""Data models and enumerations for morton-com."""

from __future__ import annotations

from enum import Enum


class SourceType(Enum):
    """What a panel displays."""

    LOCAL = "local"
    GCS_PROJECT = "gcs_project"
    GCS_BUCKET = "gcs_bucket"


class OperationType(Enum):
    """Type of file transfer operation."""

    COPY = "copy"
    MOVE = "move"


class TransferStatus(Enum):
    """Status of a transfer operation."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ConflictResolution(Enum):
    """How to handle file conflicts at destination."""

    OVERWRITE = "overwrite"
    SKIP = "skip"
    RENAME = "rename"
    ASK = "ask"


class AuthState(Enum):
    """User authentication state."""

    SIGNED_OUT = "signed_out"
    SIGNING_IN = "signing_in"
    SIGNED_IN = "signed_in"
    REFRESHING = "refreshing"
