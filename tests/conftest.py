"""Shared pytest fixtures for morton-com tests."""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for file operations."""
    return tmp_path


@pytest.fixture
def sample_local_files(tmp_path: Path) -> Path:
    """Create a set of sample local files for testing."""
    # Create directories
    (tmp_path / "documents").mkdir()
    (tmp_path / "images").mkdir()
    (tmp_path / ".hidden_dir").mkdir()

    # Create files
    (tmp_path / "readme.txt").write_text("Hello, World!")
    (tmp_path / "data.csv").write_text("col1,col2\n1,2\n3,4")
    (tmp_path / "documents" / "report.pdf").write_bytes(b"%PDF-1.4 fake content")
    (tmp_path / "images" / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0 fake jpeg")
    (tmp_path / ".hidden_file").write_text("hidden")

    return tmp_path


@pytest.fixture
def sample_file_item_data() -> dict[str, Any]:
    """Sample data for creating a FileItem."""
    return {
        "name": "test_file.txt",
        "path": Path("/tmp/test_file.txt"),
        "size": 1024,
        "modified_date": datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "created_date": datetime(2026, 1, 10, 8, 0, 0, tzinfo=timezone.utc),
        "is_directory": False,
        "permissions": "rw-r--r--",
        "is_hidden": False,
    }


@pytest.fixture
def sample_gcs_object_data() -> dict[str, Any]:
    """Sample data for creating a GCSObject."""
    return {
        "name": "path/to/file.txt",
        "bucket_name": "my-test-bucket",
        "size": 2048,
        "content_type": "text/plain",
        "storage_class": "STANDARD",
        "created_time": datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        "updated_time": datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        "generation": 1234567890,
        "metadata": {"custom-key": "custom-value"},
        "md5_hash": "abc123==",
    }


@pytest.fixture
def sample_gcs_bucket_data() -> dict[str, Any]:
    """Sample data for creating a GCSBucket."""
    return {
        "name": "my-test-bucket",
        "project_id": "test-project-123",
        "location": "US-CENTRAL1",
        "storage_class": "STANDARD",
        "created_time": datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc),
        "versioning_enabled": False,
    }


@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    """Provide a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_projects_json() -> str:
    """Sample projects.json content."""
    return '''{
  "projects": [
    {
      "project_id": "test-project-123",
      "display_name": "Test Project",
      "default": true
    },
    {
      "project_id": "other-project",
      "display_name": "Other Project"
    }
  ]
}'''


@pytest.fixture
def sample_settings_json() -> str:
    """Sample settings.json content."""
    return '''{
  "max_concurrent_transfers": 3,
  "show_hidden_files": false,
  "confirm_delete": true
}'''
