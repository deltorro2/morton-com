"""Unit tests for the LocalFilesystem service class.

Tests cover:
- list_directory sorting behavior (directories first, then files, alphabetically)
- list_directory hidden file filtering
- list_directory error handling for non-existent paths and files
- get_file_info for files and directories
- copy_file with and without progress callback
- copy_directory with and without progress callback
- move_file operations
- delete_file and delete_directory operations
- exists() method
- get_home_directory() method
- _format_permissions helper function
- _timestamp_to_utc helper function
"""

from __future__ import annotations

import stat
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.errors import FileSystemError
from src.models.file_item import FileItem
from src.services.local_filesystem import (
    LocalFilesystem,
    _format_permissions,
    _timestamp_to_utc,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def local_fs() -> LocalFilesystem:
    """Create a LocalFilesystem instance for testing."""
    return LocalFilesystem()


@pytest.fixture
def sample_directory(tmp_path: Path) -> Path:
    """Create a sample directory structure for testing.

    Structure:
        tmp_path/
            alpha_dir/
            beta_dir/
            .hidden_dir/
            alpha_file.txt
            beta_file.txt
            .hidden_file.txt
    """
    # Create directories
    (tmp_path / "alpha_dir").mkdir()
    (tmp_path / "beta_dir").mkdir()
    (tmp_path / ".hidden_dir").mkdir()

    # Create files
    (tmp_path / "alpha_file.txt").write_text("alpha content")
    (tmp_path / "beta_file.txt").write_text("beta content")
    (tmp_path / ".hidden_file.txt").write_text("hidden content")

    return tmp_path


@pytest.fixture
def nested_directory(tmp_path: Path) -> Path:
    """Create a nested directory structure for copy/delete tests.

    Structure:
        tmp_path/
            source/
                subdir1/
                    file1.txt
                subdir2/
                    file2.txt
                root_file.txt
    """
    source = tmp_path / "source"
    source.mkdir()
    (source / "subdir1").mkdir()
    (source / "subdir2").mkdir()
    (source / "subdir1" / "file1.txt").write_text("content 1")
    (source / "subdir2" / "file2.txt").write_text("content 2")
    (source / "root_file.txt").write_text("root content")

    return tmp_path


# ---------------------------------------------------------------------------
# Tests: list_directory
# ---------------------------------------------------------------------------


class TestListDirectory:
    """Tests for the list_directory method."""

    def test_list_directory_returns_directories_first_then_files_sorted_alphabetically(
        self, local_fs: LocalFilesystem, sample_directory: Path
    ) -> None:
        """Test that list_directory returns directories first, then files, sorted alphabetically."""
        result = local_fs.list_directory(sample_directory, show_hidden=True)

        # Separate dirs and files
        dirs = [item for item in result if item.is_directory]
        files = [item for item in result if not item.is_directory]

        # Check that all dirs come before all files
        dir_indices = [result.index(d) for d in dirs]
        file_indices = [result.index(f) for f in files]

        if dirs and files:
            assert max(dir_indices) < min(file_indices)

        # Check dirs are sorted alphabetically (case-insensitive)
        dir_names = [d.name for d in dirs]
        assert dir_names == sorted(dir_names, key=str.lower)

        # Check files are sorted alphabetically (case-insensitive)
        file_names = [f.name for f in files]
        assert file_names == sorted(file_names, key=str.lower)

    def test_list_directory_with_show_hidden_false_excludes_hidden_files(
        self, local_fs: LocalFilesystem, sample_directory: Path
    ) -> None:
        """Test that show_hidden=False excludes hidden files and directories."""
        result = local_fs.list_directory(sample_directory, show_hidden=False)

        names = [item.name for item in result]

        assert ".hidden_dir" not in names
        assert ".hidden_file.txt" not in names
        assert "alpha_dir" in names
        assert "beta_file.txt" in names

    def test_list_directory_with_show_hidden_true_includes_hidden_files(
        self, local_fs: LocalFilesystem, sample_directory: Path
    ) -> None:
        """Test that show_hidden=True (default) includes hidden files."""
        result = local_fs.list_directory(sample_directory, show_hidden=True)

        names = [item.name for item in result]

        assert ".hidden_dir" in names
        assert ".hidden_file.txt" in names

    def test_list_directory_on_non_existent_path_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that list_directory raises FileSystemError for non-existent path."""
        non_existent = tmp_path / "does_not_exist"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.list_directory(non_existent)

        assert "does not exist" in str(exc_info.value)
        assert exc_info.value.user_message is not None

    def test_list_directory_on_file_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that list_directory raises FileSystemError when path is a file."""
        file_path = tmp_path / "some_file.txt"
        file_path.write_text("content")

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.list_directory(file_path)

        assert "is not a folder" in exc_info.value.user_message

    def test_list_directory_returns_file_items(
        self, local_fs: LocalFilesystem, sample_directory: Path
    ) -> None:
        """Test that list_directory returns FileItem instances."""
        result = local_fs.list_directory(sample_directory)

        assert all(isinstance(item, FileItem) for item in result)


# ---------------------------------------------------------------------------
# Tests: get_file_info
# ---------------------------------------------------------------------------


class TestGetFileInfo:
    """Tests for the get_file_info method."""

    def test_get_file_info_returns_correct_file_item_for_file(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that get_file_info returns correct FileItem for a file."""
        file_path = tmp_path / "test_file.txt"
        file_content = "test content here"
        file_path.write_text(file_content)

        result = local_fs.get_file_info(file_path)

        assert isinstance(result, FileItem)
        assert result.name == "test_file.txt"
        assert result.path == file_path.resolve()
        assert result.size == len(file_content)
        assert result.is_directory is False
        assert result.is_hidden is False
        assert isinstance(result.modified_date, datetime)
        assert isinstance(result.created_date, datetime)
        assert len(result.permissions) == 9  # rwxrwxrwx format

    def test_get_file_info_returns_correct_file_item_for_directory(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that get_file_info returns correct FileItem for a directory."""
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        result = local_fs.get_file_info(dir_path)

        assert isinstance(result, FileItem)
        assert result.name == "test_dir"
        assert result.path == dir_path.resolve()
        assert result.size == 0  # Directories report size as 0
        assert result.is_directory is True
        assert result.is_hidden is False

    def test_get_file_info_on_non_existent_path_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that get_file_info raises FileSystemError for non-existent path."""
        non_existent = tmp_path / "missing_file.txt"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.get_file_info(non_existent)

        assert "was not found" in exc_info.value.user_message

    def test_get_file_info_detects_hidden_files(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that get_file_info correctly identifies hidden files."""
        hidden_file = tmp_path / ".hidden"
        hidden_file.write_text("secret")

        result = local_fs.get_file_info(hidden_file)

        assert result.is_hidden is True


# ---------------------------------------------------------------------------
# Tests: copy_file
# ---------------------------------------------------------------------------


class TestCopyFile:
    """Tests for the copy_file method."""

    def test_copy_file_copies_file_content(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that copy_file copies file content correctly."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "destination.txt"
        content = "file content to copy"
        source.write_text(content)

        local_fs.copy_file(source, destination)

        assert destination.exists()
        assert destination.read_text() == content

    def test_copy_file_with_progress_callback_gets_called(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that copy_file calls progress_callback during copy."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "destination.txt"
        content = "x" * 1000  # 1000 bytes
        source.write_text(content)

        callback = MagicMock()

        local_fs.copy_file(source, destination, progress_callback=callback)

        assert destination.exists()
        assert callback.called
        # Callback should be called with (bytes_copied, total_bytes)
        args = callback.call_args[0]
        assert len(args) == 2
        assert args[0] == len(content)  # bytes copied
        assert args[1] == len(content)  # total bytes

    def test_copy_file_on_non_existent_source_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that copy_file raises FileSystemError for non-existent source."""
        source = tmp_path / "missing.txt"
        destination = tmp_path / "destination.txt"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.copy_file(source, destination)

        assert "was not found" in exc_info.value.user_message

    def test_copy_file_on_directory_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that copy_file raises FileSystemError when source is a directory."""
        source_dir = tmp_path / "source_dir"
        source_dir.mkdir()
        destination = tmp_path / "destination"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.copy_file(source_dir, destination)

        assert "is not a regular file" in exc_info.value.user_message


# ---------------------------------------------------------------------------
# Tests: copy_directory
# ---------------------------------------------------------------------------


class TestCopyDirectory:
    """Tests for the copy_directory method."""

    def test_copy_directory_copies_directory_tree(
        self, local_fs: LocalFilesystem, nested_directory: Path
    ) -> None:
        """Test that copy_directory copies entire directory tree."""
        source = nested_directory / "source"
        destination = nested_directory / "destination"

        local_fs.copy_directory(source, destination)

        assert destination.exists()
        assert (destination / "subdir1").is_dir()
        assert (destination / "subdir2").is_dir()
        assert (destination / "subdir1" / "file1.txt").read_text() == "content 1"
        assert (destination / "subdir2" / "file2.txt").read_text() == "content 2"
        assert (destination / "root_file.txt").read_text() == "root content"

    def test_copy_directory_with_progress_callback(
        self, local_fs: LocalFilesystem, nested_directory: Path
    ) -> None:
        """Test that copy_directory calls progress_callback for each file."""
        source = nested_directory / "source"
        destination = nested_directory / "destination"

        callback = MagicMock()

        local_fs.copy_directory(source, destination, progress_callback=callback)

        # Should be called 3 times (3 files in the structure)
        assert callback.call_count == 3
        # Each call should have (filename, files_done, total_files)
        for call in callback.call_args_list:
            args = call[0]
            assert len(args) == 3
            assert isinstance(args[0], str)  # filename
            assert isinstance(args[1], int)  # files_done
            assert isinstance(args[2], int)  # total_files

    def test_copy_directory_on_non_existent_source_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that copy_directory raises FileSystemError for non-existent source."""
        source = tmp_path / "missing_dir"
        destination = tmp_path / "destination"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.copy_directory(source, destination)

        assert "was not found" in exc_info.value.user_message

    def test_copy_directory_on_file_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that copy_directory raises FileSystemError when source is a file."""
        source_file = tmp_path / "source.txt"
        source_file.write_text("content")
        destination = tmp_path / "destination"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.copy_directory(source_file, destination)

        assert "is not a folder" in exc_info.value.user_message


# ---------------------------------------------------------------------------
# Tests: move_file
# ---------------------------------------------------------------------------


class TestMoveFile:
    """Tests for the move_file method."""

    def test_move_file_moves_file(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that move_file moves the file to destination."""
        source = tmp_path / "source.txt"
        destination = tmp_path / "destination.txt"
        content = "file to move"
        source.write_text(content)

        local_fs.move_file(source, destination)

        assert not source.exists()
        assert destination.exists()
        assert destination.read_text() == content

    def test_move_file_on_non_existent_source_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that move_file raises FileSystemError for non-existent source."""
        source = tmp_path / "missing.txt"
        destination = tmp_path / "destination.txt"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.move_file(source, destination)

        assert "was not found" in exc_info.value.user_message


# ---------------------------------------------------------------------------
# Tests: delete_file
# ---------------------------------------------------------------------------


class TestDeleteFile:
    """Tests for the delete_file method."""

    def test_delete_file_deletes_file(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that delete_file deletes the file."""
        file_path = tmp_path / "to_delete.txt"
        file_path.write_text("delete me")

        local_fs.delete_file(file_path)

        assert not file_path.exists()

    def test_delete_file_on_non_existent_path_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that delete_file raises FileSystemError for non-existent path."""
        file_path = tmp_path / "missing.txt"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.delete_file(file_path)

        assert "was not found" in exc_info.value.user_message

    def test_delete_file_on_directory_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that delete_file raises FileSystemError when path is a directory."""
        dir_path = tmp_path / "a_directory"
        dir_path.mkdir()

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.delete_file(dir_path)

        assert "is not a regular file" in exc_info.value.user_message


# ---------------------------------------------------------------------------
# Tests: delete_directory
# ---------------------------------------------------------------------------


class TestDeleteDirectory:
    """Tests for the delete_directory method."""

    def test_delete_directory_deletes_directory_recursively(
        self, local_fs: LocalFilesystem, nested_directory: Path
    ) -> None:
        """Test that delete_directory deletes directory and all contents."""
        source = nested_directory / "source"

        assert source.exists()
        assert (source / "subdir1" / "file1.txt").exists()

        local_fs.delete_directory(source)

        assert not source.exists()

    def test_delete_directory_on_non_existent_path_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that delete_directory raises FileSystemError for non-existent path."""
        dir_path = tmp_path / "missing_dir"

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.delete_directory(dir_path)

        assert "was not found" in exc_info.value.user_message

    def test_delete_directory_on_file_raises_filesystem_error(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that delete_directory raises FileSystemError when path is a file."""
        file_path = tmp_path / "a_file.txt"
        file_path.write_text("content")

        with pytest.raises(FileSystemError) as exc_info:
            local_fs.delete_directory(file_path)

        assert "is not a folder" in exc_info.value.user_message


# ---------------------------------------------------------------------------
# Tests: exists
# ---------------------------------------------------------------------------


class TestExists:
    """Tests for the exists method."""

    def test_exists_returns_true_for_existing_file(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that exists returns True for an existing file."""
        file_path = tmp_path / "existing.txt"
        file_path.write_text("content")

        assert local_fs.exists(file_path) is True

    def test_exists_returns_true_for_existing_directory(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that exists returns True for an existing directory."""
        dir_path = tmp_path / "existing_dir"
        dir_path.mkdir()

        assert local_fs.exists(dir_path) is True

    def test_exists_returns_false_for_non_existent_path(
        self, local_fs: LocalFilesystem, tmp_path: Path
    ) -> None:
        """Test that exists returns False for non-existent path."""
        non_existent = tmp_path / "missing"

        assert local_fs.exists(non_existent) is False


# ---------------------------------------------------------------------------
# Tests: get_home_directory
# ---------------------------------------------------------------------------


class TestGetHomeDirectory:
    """Tests for the get_home_directory method."""

    def test_get_home_directory_returns_path_home(
        self, local_fs: LocalFilesystem
    ) -> None:
        """Test that get_home_directory returns Path.home()."""
        result = local_fs.get_home_directory()

        assert result == Path.home()
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# Tests: _format_permissions helper
# ---------------------------------------------------------------------------


class TestFormatPermissions:
    """Tests for the _format_permissions helper function."""

    def test_format_permissions_all_permissions(self) -> None:
        """Test _format_permissions with all permissions set."""
        mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO  # 0o777
        result = _format_permissions(mode)

        assert result == "rwxrwxrwx"

    def test_format_permissions_no_permissions(self) -> None:
        """Test _format_permissions with no permissions."""
        mode = 0
        result = _format_permissions(mode)

        assert result == "---------"

    def test_format_permissions_read_only(self) -> None:
        """Test _format_permissions with read-only for owner."""
        mode = stat.S_IRUSR  # 0o400
        result = _format_permissions(mode)

        assert result == "r--------"

    def test_format_permissions_typical_file(self) -> None:
        """Test _format_permissions with typical file permissions (644)."""
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH  # 0o644
        result = _format_permissions(mode)

        assert result == "rw-r--r--"

    def test_format_permissions_executable(self) -> None:
        """Test _format_permissions with executable permissions (755)."""
        mode = (
            stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        )  # 0o755
        result = _format_permissions(mode)

        assert result == "rwxr-xr-x"


# ---------------------------------------------------------------------------
# Tests: _timestamp_to_utc helper
# ---------------------------------------------------------------------------


class TestTimestampToUtc:
    """Tests for the _timestamp_to_utc helper function."""

    def test_timestamp_to_utc_returns_timezone_aware_datetime(self) -> None:
        """Test that _timestamp_to_utc returns a timezone-aware UTC datetime."""
        timestamp = 1609459200.0  # 2021-01-01 00:00:00 UTC

        result = _timestamp_to_utc(timestamp)

        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_timestamp_to_utc_converts_correctly(self) -> None:
        """Test that _timestamp_to_utc converts timestamp correctly."""
        # Known timestamp: 2021-01-01 00:00:00 UTC
        timestamp = 1609459200.0

        result = _timestamp_to_utc(timestamp)

        assert result.year == 2021
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_timestamp_to_utc_zero_timestamp(self) -> None:
        """Test _timestamp_to_utc with zero timestamp (Unix epoch)."""
        timestamp = 0.0

        result = _timestamp_to_utc(timestamp)

        assert result.year == 1970
        assert result.month == 1
        assert result.day == 1
