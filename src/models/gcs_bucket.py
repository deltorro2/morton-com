"""Google Cloud Storage bucket data model.

Represents a single GCS bucket with its core metadata and a display-friendly
location property.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GCSBucket:
    """A Google Cloud Storage bucket.

    Parameters
    ----------
    name:
        Globally-unique bucket name.
    project_id:
        Google Cloud project that owns the bucket.
    location:
        GCS location identifier, e.g. ``"us-east1"``.
    storage_class:
        Default storage class (``STANDARD``, ``NEARLINE``, etc.).
    created_time:
        Timestamp when the bucket was created.
    versioning_enabled:
        ``True`` when object versioning is turned on.
    """

    name: str
    project_id: str
    location: str
    storage_class: str
    created_time: datetime
    versioning_enabled: bool

    @property
    def display_location(self) -> str:
        """Human-friendly location string.

        Replaces hyphens with spaces and applies title case, e.g.
        ``"us-east1"`` becomes ``"Us East1"``.
        """
        return self.location.replace("-", " ").title()
