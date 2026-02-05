"""Google Cloud Storage object data model.

Represents a single blob (or pseudo-directory prefix) inside a GCS bucket,
with convenience properties for display rendering and prefix navigation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

_SIZE_UNITS: list[tuple[int, str]] = [
    (1 << 40, "TB"),
    (1 << 30, "GB"),
    (1 << 20, "MB"),
    (1 << 10, "KB"),
]


def _format_size(size: int) -> str:
    """Return a human-readable size string such as ``1.5 MB``."""
    for threshold, unit in _SIZE_UNITS:
        if size >= threshold:
            value = size / threshold
            formatted = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{formatted} {unit}"
    return f"{size} B"


@dataclass
class GCSObject:
    """A Google Cloud Storage blob.

    Parameters
    ----------
    name:
        Full object name (key) inside the bucket, e.g. ``"a/b/file.txt"``.
    bucket_name:
        Name of the containing bucket.
    size:
        Size in bytes.
    content_type:
        MIME content type of the object.
    storage_class:
        GCS storage class (``STANDARD``, ``NEARLINE``, etc.).
    created_time:
        Timestamp when the object was created.
    updated_time:
        Timestamp of the most recent update.
    generation:
        GCS object generation number.
    metadata:
        User-defined metadata key-value pairs.
    md5_hash:
        Base64-encoded MD5 hash of the object data.
    """

    name: str
    bucket_name: str
    size: int
    content_type: str
    storage_class: str
    created_time: datetime
    updated_time: datetime
    generation: int
    metadata: dict[str, str] = field(default_factory=dict)
    md5_hash: str = ""

    @property
    def display_name(self) -> str:
        """Last path segment of the object name.

        For ``"a/b/file.txt"`` this returns ``"file.txt"``.
        For a prefix like ``"a/b/"`` this returns ``"b"``.
        """
        stripped = self.name.rstrip("/")
        if "/" in stripped:
            return stripped.rsplit("/", 1)[1]
        return stripped

    @property
    def prefix(self) -> str:
        """Parent 'folder' prefix.

        For ``"a/b/file.txt"`` this returns ``"a/b"``.
        Returns ``""`` when there is no ``/`` in the name.
        """
        stripped = self.name.rstrip("/")
        if "/" in stripped:
            return stripped.rsplit("/", 1)[0]
        return ""

    @property
    def display_size(self) -> str:
        """Human-readable size string."""
        return _format_size(self.size)

    @property
    def is_prefix(self) -> bool:
        """``True`` when this object represents a directory-like prefix."""
        return self.size == 0 and self.name.endswith("/")
