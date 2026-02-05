"""Panel state data model.

Captures the full mutable state of a single file-browser panel, including
its source type, current location, item list, selection, sort order, and
loading / error indicators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.models import SourceType


@dataclass
class PanelState:
    """State of one file-browser panel.

    Parameters
    ----------
    id:
        Unique identifier for this panel (e.g. ``"left"``, ``"right"``).
    source_type:
        What the panel is currently displaying.
    location:
        Current path or prefix being shown.
    project_id:
        Active Google Cloud project (GCS panels only).
    bucket_name:
        Active bucket name (GCS bucket panels only).
    items:
        List of items currently displayed (``FileItem`` or ``GCSObject``).
    selected_indices:
        Indices of items currently selected by the user.
    sort_column:
        Column name by which items are sorted.
    sort_ascending:
        ``True`` for ascending sort order.
    loading:
        ``True`` while the panel is loading content.
    error:
        Error message to display, or ``""`` when there is no error.
    """

    id: str
    source_type: SourceType
    location: str = ""
    project_id: str = ""
    bucket_name: str = ""
    items: list[Any] = field(default_factory=list)
    selected_indices: set[int] = field(default_factory=set)
    sort_column: str = "name"
    sort_ascending: bool = True
    loading: bool = False
    error: str = ""
