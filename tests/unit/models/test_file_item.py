"""Unit tests for the FileItem dataclass and helper functions.

Tests cover:
- FileItem creation with all fields
- display_size property for various file sizes and directories
- extension property for files with/without extensions and directories
- icon_type property for various file types and case-insensitivity
- is_hidden and permissions fields
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.models.file_item import FileItem, _format_size


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_datetime() -> datetime:
    """A fixed datetime for tests."""
    return datetime(2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def file_item_defaults(base_datetime: datetime) -> dict:
    """Default values for creating a FileItem."""
    return {
        "name": "example.txt",
        "path": Path("/home/user/example.txt"),
        "size": 1024,
        "modified_date": base_datetime,
        "created_date": base_datetime,
        "is_directory": False,
        "permissions": "rw-r--r--",
        "is_hidden": False,
    }


# ---------------------------------------------------------------------------
# Test: Basic FileItem creation with all fields
# ---------------------------------------------------------------------------


class TestFileItemCreation:
    """Tests for basic FileItem instantiation."""

    def test_create_file_item_with_all_fields(
        self, file_item_defaults: dict, base_datetime: datetime
    ) -> None:
        """Test that a FileItem can be created with all required fields."""
        item = FileItem(**file_item_defaults)

        assert item.name == "example.txt"
        assert item.path == Path("/home/user/example.txt")
        assert item.size == 1024
        assert item.modified_date == base_datetime
        assert item.created_date == base_datetime
        assert item.is_directory is False
        assert item.permissions == "rw-r--r--"
        assert item.is_hidden is False

    def test_create_file_item_with_path_object(
        self, file_item_defaults: dict
    ) -> None:
        """Test FileItem creation with pathlib.Path object."""
        test_path = Path("/var/log/system.log")
        file_item_defaults["path"] = test_path
        file_item_defaults["name"] = "system.log"

        item = FileItem(**file_item_defaults)

        assert isinstance(item.path, Path)
        assert item.path == test_path
        assert str(item.path) == "/var/log/system.log"

    def test_is_hidden_field_true(self, file_item_defaults: dict) -> None:
        """Test FileItem with is_hidden set to True."""
        file_item_defaults["name"] = ".bashrc"
        file_item_defaults["is_hidden"] = True

        item = FileItem(**file_item_defaults)

        assert item.is_hidden is True
        assert item.name == ".bashrc"

    def test_permissions_field(self, file_item_defaults: dict) -> None:
        """Test FileItem with various permission strings."""
        file_item_defaults["permissions"] = "rwxrwxrwx"

        item = FileItem(**file_item_defaults)

        assert item.permissions == "rwxrwxrwx"


# ---------------------------------------------------------------------------
# Test: display_size property
# ---------------------------------------------------------------------------


class TestDisplaySize:
    """Tests for the display_size property."""

    def test_display_size_returns_empty_for_directories(
        self, file_item_defaults: dict
    ) -> None:
        """Test that display_size returns empty string for directories."""
        file_item_defaults["is_directory"] = True
        file_item_defaults["size"] = 0

        item = FileItem(**file_item_defaults)

        assert item.display_size == ""

    def test_display_size_returns_bytes_for_small_files(
        self, file_item_defaults: dict
    ) -> None:
        """Test display_size returns bytes for files < 1024 bytes."""
        file_item_defaults["size"] = 500

        item = FileItem(**file_item_defaults)

        assert item.display_size == "500 B"

    def test_display_size_returns_kb_for_kilobyte_files(
        self, file_item_defaults: dict
    ) -> None:
        """Test display_size returns KB for files >= 1024 bytes."""
        file_item_defaults["size"] = 1536  # 1.5 KB

        item = FileItem(**file_item_defaults)

        assert item.display_size == "1.5 KB"

    def test_display_size_returns_mb_for_megabyte_files(
        self, file_item_defaults: dict
    ) -> None:
        """Test display_size returns MB for files >= 1MB."""
        file_item_defaults["size"] = 2 * 1024 * 1024  # 2 MB

        item = FileItem(**file_item_defaults)

        assert item.display_size == "2 MB"

    def test_display_size_returns_gb_for_gigabyte_files(
        self, file_item_defaults: dict
    ) -> None:
        """Test display_size returns GB for files >= 1GB."""
        file_item_defaults["size"] = 3 * 1024 * 1024 * 1024  # 3 GB

        item = FileItem(**file_item_defaults)

        assert item.display_size == "3 GB"

    def test_display_size_returns_tb_for_terabyte_files(
        self, file_item_defaults: dict
    ) -> None:
        """Test display_size returns TB for files >= 1TB."""
        file_item_defaults["size"] = 2 * 1024 * 1024 * 1024 * 1024  # 2 TB

        item = FileItem(**file_item_defaults)

        assert item.display_size == "2 TB"

    def test_display_size_strips_trailing_zeros(
        self, file_item_defaults: dict
    ) -> None:
        """Test that display_size strips trailing zeros (e.g. '2 MB' not '2.0 MB')."""
        file_item_defaults["size"] = 2 * 1024 * 1024  # Exactly 2 MB

        item = FileItem(**file_item_defaults)

        assert item.display_size == "2 MB"
        assert ".0" not in item.display_size


# ---------------------------------------------------------------------------
# Test: _format_size helper function
# ---------------------------------------------------------------------------


class TestFormatSizeHelper:
    """Tests for the _format_size helper function."""

    def test_format_size_zero_bytes(self) -> None:
        """Test _format_size with zero bytes."""
        assert _format_size(0) == "0 B"

    def test_format_size_bytes(self) -> None:
        """Test _format_size for small files in bytes."""
        assert _format_size(500) == "500 B"
        assert _format_size(1023) == "1023 B"

    def test_format_size_kilobytes(self) -> None:
        """Test _format_size for kilobyte-sized files."""
        assert _format_size(1024) == "1 KB"
        assert _format_size(1536) == "1.5 KB"

    def test_format_size_megabytes(self) -> None:
        """Test _format_size for megabyte-sized files."""
        assert _format_size(1024 * 1024) == "1 MB"
        assert _format_size(int(1.5 * 1024 * 1024)) == "1.5 MB"

    def test_format_size_gigabytes(self) -> None:
        """Test _format_size for gigabyte-sized files."""
        assert _format_size(1024 * 1024 * 1024) == "1 GB"

    def test_format_size_terabytes(self) -> None:
        """Test _format_size for terabyte-sized files."""
        assert _format_size(1024 * 1024 * 1024 * 1024) == "1 TB"


# ---------------------------------------------------------------------------
# Test: extension property
# ---------------------------------------------------------------------------


class TestExtension:
    """Tests for the extension property."""

    def test_extension_returns_empty_for_directories(
        self, file_item_defaults: dict
    ) -> None:
        """Test that extension returns empty string for directories."""
        file_item_defaults["is_directory"] = True
        file_item_defaults["name"] = "my_folder"

        item = FileItem(**file_item_defaults)

        assert item.extension == ""

    def test_extension_returns_empty_for_files_without_extension(
        self, file_item_defaults: dict
    ) -> None:
        """Test extension returns empty for files without an extension."""
        file_item_defaults["name"] = "Makefile"

        item = FileItem(**file_item_defaults)

        assert item.extension == ""

    def test_extension_returns_extension_without_dot(
        self, file_item_defaults: dict
    ) -> None:
        """Test extension returns the extension without leading dot."""
        file_item_defaults["name"] = "document.txt"

        item = FileItem(**file_item_defaults)

        assert item.extension == "txt"
        assert not item.extension.startswith(".")


# ---------------------------------------------------------------------------
# Test: icon_type property
# ---------------------------------------------------------------------------


class TestIconType:
    """Tests for the icon_type property."""

    def test_icon_type_returns_folder_for_directories(
        self, file_item_defaults: dict
    ) -> None:
        """Test that icon_type returns 'folder' for directories."""
        file_item_defaults["is_directory"] = True
        file_item_defaults["name"] = "documents"

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "folder"

    @pytest.mark.parametrize(
        "filename",
        ["photo.jpg", "image.jpeg", "logo.png", "animation.gif", "icon.svg", "bitmap.bmp", "modern.webp"],
    )
    def test_icon_type_returns_image_for_image_extensions(
        self, file_item_defaults: dict, filename: str
    ) -> None:
        """Test icon_type returns 'image' for image file extensions."""
        file_item_defaults["name"] = filename

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "image"

    @pytest.mark.parametrize(
        "filename",
        ["report.pdf", "letter.doc", "essay.docx", "notes.txt", "formatted.rtf"],
    )
    def test_icon_type_returns_document_for_document_extensions(
        self, file_item_defaults: dict, filename: str
    ) -> None:
        """Test icon_type returns 'document' for document file extensions."""
        file_item_defaults["name"] = filename

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "document"

    @pytest.mark.parametrize(
        "filename",
        ["data.xls", "spreadsheet.xlsx", "export.csv"],
    )
    def test_icon_type_returns_spreadsheet_for_spreadsheet_extensions(
        self, file_item_defaults: dict, filename: str
    ) -> None:
        """Test icon_type returns 'spreadsheet' for spreadsheet extensions."""
        file_item_defaults["name"] = filename

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "spreadsheet"

    @pytest.mark.parametrize(
        "filename",
        ["archive.zip", "backup.tar", "compressed.gz", "data.rar", "archive.7z"],
    )
    def test_icon_type_returns_archive_for_archive_extensions(
        self, file_item_defaults: dict, filename: str
    ) -> None:
        """Test icon_type returns 'archive' for archive file extensions."""
        file_item_defaults["name"] = filename

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "archive"

    @pytest.mark.parametrize(
        "filename",
        ["script.py", "app.js", "module.ts", "index.html", "styles.css", "Main.java", "program.cpp", "header.h", "main.rs", "server.go"],
    )
    def test_icon_type_returns_code_for_code_extensions(
        self, file_item_defaults: dict, filename: str
    ) -> None:
        """Test icon_type returns 'code' for code file extensions."""
        file_item_defaults["name"] = filename

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "code"

    def test_icon_type_returns_file_for_unknown_extensions(
        self, file_item_defaults: dict
    ) -> None:
        """Test icon_type returns 'file' for unknown/unrecognized extensions."""
        file_item_defaults["name"] = "mystery.xyz"

        item = FileItem(**file_item_defaults)

        assert item.icon_type == "file"

    @pytest.mark.parametrize(
        "filename,expected_type",
        [
            ("IMAGE.JPG", "image"),
            ("DOCUMENT.PDF", "document"),
            ("Data.CSV", "spreadsheet"),
            ("Archive.ZIP", "archive"),
            ("Script.PY", "code"),
        ],
    )
    def test_icon_type_is_case_insensitive(
        self, file_item_defaults: dict, filename: str, expected_type: str
    ) -> None:
        """Test that icon_type is case-insensitive for file extensions."""
        file_item_defaults["name"] = filename

        item = FileItem(**file_item_defaults)

        assert item.icon_type == expected_type
