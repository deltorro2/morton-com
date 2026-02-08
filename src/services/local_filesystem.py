"""Local filesystem service.

Provides file-system operations (list, copy, move, delete) for the local
machine, returning :class:`~src.models.file_item.FileItem` instances and
raising :class:`~src.errors.FileSystemError` on failure.
"""

from __future__ import annotations

import datetime
import os
import platform
import shutil
import stat
from collections.abc import Callable
from pathlib import Path

from src.errors import FileSystemError
from src.models.file_item import FileItem

_COPY_CHUNK_SIZE: int = 8 * 1024 * 1024  # 8 MB

# Permission bit triplets in high-to-low order.
_PERM_BITS: list[tuple[int, str]] = [
    (stat.S_IRUSR, "r"),
    (stat.S_IWUSR, "w"),
    (stat.S_IXUSR, "x"),
    (stat.S_IRGRP, "r"),
    (stat.S_IWGRP, "w"),
    (stat.S_IXGRP, "x"),
    (stat.S_IROTH, "r"),
    (stat.S_IWOTH, "w"),
    (stat.S_IXOTH, "x"),
]


def _format_permissions(mode: int) -> str:
    """Convert a numeric mode to a ``rwxrwxrwx`` string."""
    return "".join(ch if mode & bit else "-" for bit, ch in _PERM_BITS)


def _timestamp_to_utc(ts: float) -> datetime.datetime:
    """Convert a POSIX timestamp to a timezone-aware UTC datetime."""
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)


class LocalFilesystem:
    """Service for local filesystem operations."""

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_file_item(path: Path) -> FileItem:
        """Construct a :class:`FileItem` from *path*.

        On macOS ``st_birthtime`` is used for the creation date; on other
        platforms ``st_ctime`` is used as a fallback.
        """
        resolved = path.resolve()
        try:
            st = resolved.stat()
        except OSError as exc:
            raise FileSystemError(
                message=f"Cannot stat path: {resolved} -- {exc}",
                user_message=f'Unable to read information for "{resolved.name}".',
                suggested_action="Check that the file exists and you have read permission.",
                technical_detail=str(exc),
            ) from exc

        is_dir = stat.S_ISDIR(st.st_mode)

        # Creation timestamp: prefer st_birthtime (macOS) when available.
        if platform.system() == "Darwin":
            created_ts: float = st.st_birthtime  # type: ignore[attr-defined]
        else:
            created_ts = st.st_ctime

        return FileItem(
            name=resolved.name,
            path=resolved,
            size=0 if is_dir else st.st_size,
            modified_date=_timestamp_to_utc(st.st_mtime),
            created_date=_timestamp_to_utc(created_ts),
            is_directory=is_dir,
            permissions=_format_permissions(st.st_mode),
            is_hidden=resolved.name.startswith("."),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def list_directory(
        self,
        path: Path,
        show_hidden: bool = True,
    ) -> list[FileItem]:
        """List the contents of *path*.

        Returns directories first, then files, each group sorted
        alphabetically (case-insensitive).

        Parameters
        ----------
        path:
            Directory to list.
        show_hidden:
            When ``False``, entries whose name starts with ``"."`` are
            excluded.

        Raises
        ------
        FileSystemError
            If *path* does not exist or is not accessible.
        """
        resolved = path.resolve()

        if not resolved.exists():
            raise FileSystemError(
                message=f"Directory does not exist: {resolved}",
                user_message=f'The folder "{resolved.name}" does not exist.',
                suggested_action="Verify the path and try again.",
            )
        if not resolved.is_dir():
            raise FileSystemError(
                message=f"Path is not a directory: {resolved}",
                user_message=f'"{resolved.name}" is not a folder.',
                suggested_action="Select a folder instead of a file.",
            )

        try:
            entries = list(resolved.iterdir())
        except OSError as exc:
            raise FileSystemError(
                message=f"Cannot list directory: {resolved} -- {exc}",
                user_message=f'Unable to open the folder "{resolved.name}".',
                suggested_action="Check that you have read permission for this folder.",
                technical_detail=str(exc),
            ) from exc

        items: list[FileItem] = []
        for entry in entries:
            if not show_hidden and entry.name.startswith("."):
                continue
            try:
                items.append(self._build_file_item(entry))
            except FileSystemError:
                # Skip entries we cannot stat (e.g. broken symlinks).
                continue

        # Directories first, then files; each group sorted alphabetically.
        dirs = sorted(
            (i for i in items if i.is_directory),
            key=lambda i: i.name.lower(),
        )
        files = sorted(
            (i for i in items if not i.is_directory),
            key=lambda i: i.name.lower(),
        )
        return dirs + files

    def get_file_info(self, path: Path) -> FileItem:
        """Return a :class:`FileItem` for a single path.

        Raises
        ------
        FileSystemError
            If *path* does not exist.
        """
        resolved = path.resolve()
        if not resolved.exists():
            raise FileSystemError(
                message=f"Path does not exist: {resolved}",
                user_message=f'"{resolved.name}" was not found.',
                suggested_action="Verify the path and try again.",
            )
        return self._build_file_item(resolved)

    # ------------------------------------------------------------------
    # Copy
    # ------------------------------------------------------------------

    def copy_file(
        self,
        source: Path,
        destination: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Copy a single file from *source* to *destination*.

        When *progress_callback* is supplied it is called after every 8 MB
        chunk with ``(bytes_copied_so_far, total_bytes)``.  When it is
        ``None``, :func:`shutil.copy2` is used for efficiency.

        Raises
        ------
        FileSystemError
            On any I/O failure.
        """
        src = source.resolve()
        dst = destination.resolve()

        if not src.exists():
            raise FileSystemError(
                message=f"Source file does not exist: {src}",
                user_message=f'The file "{src.name}" was not found.',
                suggested_action="Verify the source path and try again.",
            )
        if not src.is_file():
            raise FileSystemError(
                message=f"Source is not a file: {src}",
                user_message=f'"{src.name}" is not a regular file.',
                suggested_action="Use copy_directory for folders.",
            )

        try:
            if progress_callback is None:
                shutil.copy2(src, dst)
                return

            total_bytes = src.stat().st_size
            bytes_copied = 0

            with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                while True:
                    chunk = fsrc.read(_COPY_CHUNK_SIZE)
                    if not chunk:
                        break
                    fdst.write(chunk)
                    bytes_copied += len(chunk)
                    progress_callback(bytes_copied, total_bytes)

            # Preserve metadata (timestamps, permissions).
            shutil.copystat(src, dst)

        except FileNotFoundError as exc:
            raise FileSystemError(
                message=f"File not found during copy: {exc}",
                user_message="A file was not found during the copy operation.",
                suggested_action="Ensure both source and destination paths are valid.",
                technical_detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise FileSystemError(
                message=f"Permission denied during copy: {exc}",
                user_message="Permission denied while copying the file.",
                suggested_action="Check file and folder permissions, then retry.",
                technical_detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileSystemError(
                message=f"Failed to copy {src} -> {dst}: {exc}",
                user_message=f'Could not copy "{src.name}".',
                suggested_action="Check available disk space and permissions.",
                technical_detail=str(exc),
            ) from exc

    def copy_directory(
        self,
        source: Path,
        destination: Path,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> None:
        """Recursively copy a directory tree.

        *progress_callback*, when provided, is invoked after each file
        with ``(current_file_name, files_done, total_files)``.

        Raises
        ------
        FileSystemError
            On any I/O failure.
        """
        src = source.resolve()
        dst = destination.resolve()

        if not src.exists():
            raise FileSystemError(
                message=f"Source directory does not exist: {src}",
                user_message=f'The folder "{src.name}" was not found.',
                suggested_action="Verify the source path and try again.",
            )
        if not src.is_dir():
            raise FileSystemError(
                message=f"Source is not a directory: {src}",
                user_message=f'"{src.name}" is not a folder.',
                suggested_action="Use copy_file for single files.",
            )

        try:
            # Count total files for progress reporting.
            total_files = sum(
                len(files) for _, _, files in os.walk(src)
            )
            files_done = 0

            for dirpath, dirnames, filenames in os.walk(src):
                current_src = Path(dirpath)
                relative = current_src.relative_to(src)
                current_dst = dst / relative

                # Create the mirror directory.
                current_dst.mkdir(parents=True, exist_ok=True)

                for filename in filenames:
                    src_file = current_src / filename
                    dst_file = current_dst / filename
                    shutil.copy2(src_file, dst_file)
                    files_done += 1
                    if progress_callback is not None:
                        progress_callback(filename, files_done, total_files)

            # Preserve directory-level metadata after all contents are copied.
            shutil.copystat(src, dst)

        except FileNotFoundError as exc:
            raise FileSystemError(
                message=f"File not found during directory copy: {exc}",
                user_message="A file or folder was not found during the copy.",
                suggested_action="Ensure the source still exists and try again.",
                technical_detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise FileSystemError(
                message=f"Permission denied during directory copy: {exc}",
                user_message="Permission denied while copying the folder.",
                suggested_action="Check folder permissions, then retry.",
                technical_detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileSystemError(
                message=f"Failed to copy directory {src} -> {dst}: {exc}",
                user_message=f'Could not copy the folder "{src.name}".',
                suggested_action="Check available disk space and permissions.",
                technical_detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Move / Delete
    # ------------------------------------------------------------------

    def move_file(self, source: Path, destination: Path) -> None:
        """Move *source* to *destination*.

        Raises
        ------
        FileSystemError
            On any I/O failure.
        """
        src = source.resolve()
        dst = destination.resolve()

        if not src.exists():
            raise FileSystemError(
                message=f"Source does not exist: {src}",
                user_message=f'"{src.name}" was not found.',
                suggested_action="Verify the source path and try again.",
            )

        try:
            shutil.move(str(src), str(dst))
        except FileNotFoundError as exc:
            raise FileSystemError(
                message=f"File not found during move: {exc}",
                user_message="A file was not found during the move operation.",
                suggested_action="Ensure the source and destination paths are valid.",
                technical_detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise FileSystemError(
                message=f"Permission denied during move: {exc}",
                user_message="Permission denied while moving the file.",
                suggested_action="Check file and folder permissions, then retry.",
                technical_detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileSystemError(
                message=f"Failed to move {src} -> {dst}: {exc}",
                user_message=f'Could not move "{src.name}".',
                suggested_action="Check available disk space and permissions.",
                technical_detail=str(exc),
            ) from exc

    def delete_file(self, path: Path) -> None:
        """Delete a single file.

        Raises
        ------
        FileSystemError
            If *path* does not exist, is not a file, or cannot be deleted.
        """
        resolved = path.resolve()

        if not resolved.exists():
            raise FileSystemError(
                message=f"File does not exist: {resolved}",
                user_message=f'"{resolved.name}" was not found.',
                suggested_action="Verify the path and try again.",
            )
        if not resolved.is_file():
            raise FileSystemError(
                message=f"Path is not a file: {resolved}",
                user_message=f'"{resolved.name}" is not a regular file.',
                suggested_action="Use delete_directory for folders.",
            )

        try:
            resolved.unlink()
        except PermissionError as exc:
            raise FileSystemError(
                message=f"Permission denied deleting file: {resolved} -- {exc}",
                user_message=f'Permission denied while deleting "{resolved.name}".',
                suggested_action="Check file permissions, then retry.",
                technical_detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileSystemError(
                message=f"Failed to delete file: {resolved} -- {exc}",
                user_message=f'Could not delete "{resolved.name}".',
                suggested_action="Close any programs using this file and retry.",
                technical_detail=str(exc),
            ) from exc

    def delete_directory(self, path: Path) -> None:
        """Recursively delete a directory and all of its contents.

        Raises
        ------
        FileSystemError
            If *path* does not exist, is not a directory, or cannot be
            deleted.
        """
        resolved = path.resolve()

        if not resolved.exists():
            raise FileSystemError(
                message=f"Directory does not exist: {resolved}",
                user_message=f'The folder "{resolved.name}" was not found.',
                suggested_action="Verify the path and try again.",
            )
        if not resolved.is_dir():
            raise FileSystemError(
                message=f"Path is not a directory: {resolved}",
                user_message=f'"{resolved.name}" is not a folder.',
                suggested_action="Use delete_file for files.",
            )

        try:
            shutil.rmtree(resolved)
        except PermissionError as exc:
            raise FileSystemError(
                message=f"Permission denied deleting directory: {resolved} -- {exc}",
                user_message=f'Permission denied while deleting "{resolved.name}".',
                suggested_action="Check folder permissions, then retry.",
                technical_detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileSystemError(
                message=f"Failed to delete directory: {resolved} -- {exc}",
                user_message=f'Could not delete the folder "{resolved.name}".',
                suggested_action="Close any programs using files in this folder and retry.",
                technical_detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_directory(self, path: Path) -> None:
        """Create a new directory at *path*.

        Multi-level paths (e.g. ``a/b/c``) are supported via
        ``parents=True``.  ``exist_ok`` is ``False`` so that an error
        is raised when the directory already exists.

        Raises
        ------
        FileSystemError
            If the directory already exists, permission is denied,
            or another OS error occurs.
        """
        try:
            path.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise FileSystemError(
                message=f"Directory already exists: {path}",
                user_message=f'The folder "{path.name}" already exists.',
                suggested_action="Choose a different name.",
                technical_detail=str(exc),
            ) from exc
        except PermissionError as exc:
            raise FileSystemError(
                message=f"Permission denied creating directory: {path} -- {exc}",
                user_message=f'Permission denied while creating "{path.name}".',
                suggested_action="Check folder permissions, then retry.",
                technical_detail=str(exc),
            ) from exc
        except OSError as exc:
            raise FileSystemError(
                message=f"Failed to create directory: {path} -- {exc}",
                user_message=f'Could not create the folder "{path.name}".',
                suggested_action="Check the path is valid and try again.",
                technical_detail=str(exc),
            ) from exc

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def exists(self, path: Path) -> bool:
        """Return ``True`` if *path* exists on the local filesystem."""
        return path.resolve().exists()

    def get_home_directory(self) -> Path:
        """Return the current user's home directory."""
        return Path.home()
