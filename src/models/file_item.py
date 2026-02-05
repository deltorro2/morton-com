"""Local file-system item data model.

Represents a single file or directory entry with derived display helpers
for human-readable sizes, icon classification, and extension extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

_SIZE_UNITS: list[tuple[int, str]] = [
    (1 << 40, "TB"),
    (1 << 30, "GB"),
    (1 << 20, "MB"),
    (1 << 10, "KB"),
]

_EXTENSION_ICON_MAP: dict[str, str] = {
    ext: category
    for category, extensions in {
        "image": ("jpg", "jpeg", "png", "gif", "svg", "bmp", "webp"),
        "document": ("pdf", "doc", "docx", "txt", "rtf"),
        "spreadsheet": ("xls", "xlsx", "csv"),
        "archive": ("zip", "tar", "gz", "rar", "7z"),
        "code": ("py", "js", "ts", "html", "css", "java", "cpp", "h", "rs", "go"),
    }.items()
    for ext in extensions
}


def _format_size(size: int) -> str:
    """Return a human-readable size string such as ``1.5 MB``."""
    for threshold, unit in _SIZE_UNITS:
        if size >= threshold:
            value = size / threshold
            # Drop the decimal when it is ".0"
            formatted = f"{value:.1f}".rstrip("0").rstrip(".")
            return f"{formatted} {unit}"
    return f"{size} B"


@dataclass
class FileItem:
    """A local file-system entry (file or directory).

    Parameters
    ----------
    name:
        Base name of the file or directory.
    path:
        Absolute path on the local file-system.
    size:
        Size in bytes (0 for directories).
    modified_date:
        Last-modified timestamp.
    created_date:
        Creation timestamp.
    is_directory:
        ``True`` when this item is a directory.
    permissions:
        POSIX-style permission string, e.g. ``"rwxr-xr-x"``.
    is_hidden:
        ``True`` when the item is hidden (e.g. name starts with ``"."``).
    """

    name: str
    path: Path
    size: int
    modified_date: datetime
    created_date: datetime
    is_directory: bool
    permissions: str
    is_hidden: bool

    @property
    def display_size(self) -> str:
        """Human-readable size.  Returns ``""`` for directories."""
        if self.is_directory:
            return ""
        return _format_size(self.size)

    @property
    def extension(self) -> str:
        """File extension without the leading dot.  ``""`` for directories."""
        if self.is_directory:
            return ""
        suffix = Path(self.name).suffix
        return suffix.lstrip(".") if suffix else ""

    @property
    def icon_type(self) -> str:
        """Icon category for UI rendering.

        Returns ``"folder"`` for directories, otherwise one of ``"image"``,
        ``"document"``, ``"spreadsheet"``, ``"archive"``, ``"code"``, or
        the fallback ``"file"``.
        """
        if self.is_directory:
            return "folder"
        return _EXTENSION_ICON_MAP.get(self.extension.lower(), "file")
