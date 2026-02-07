"""Unit tests for GCSObject dataclass."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.gcs_object import GCSObject


class TestGCSObjectCreation:
    """Tests for GCSObject instantiation."""

    def test_create_with_required_fields(self) -> None:
        """GCSObject can be created with all required fields."""
        created = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        updated = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)

        obj = GCSObject(
            name="folder/file.txt",
            bucket_name="my-bucket",
            size=1024,
            content_type="text/plain",
            storage_class="STANDARD",
            created_time=created,
            updated_time=updated,
            generation=123456789,
        )

        assert obj.name == "folder/file.txt"
        assert obj.bucket_name == "my-bucket"
        assert obj.size == 1024
        assert obj.content_type == "text/plain"
        assert obj.storage_class == "STANDARD"
        assert obj.created_time == created
        assert obj.updated_time == updated
        assert obj.generation == 123456789

    def test_default_metadata_is_empty_dict(self) -> None:
        """GCSObject has empty dict as default metadata."""
        obj = _make_gcs_object()

        assert obj.metadata == {}
        assert isinstance(obj.metadata, dict)

    def test_default_md5_hash_is_empty_string(self) -> None:
        """GCSObject has empty string as default md5_hash."""
        obj = _make_gcs_object()

        assert obj.md5_hash == ""


class TestDisplayName:
    """Tests for the display_name property."""

    def test_display_name_returns_last_segment(self) -> None:
        """display_name returns last segment of nested path."""
        obj = _make_gcs_object(name="a/b/file.txt")

        assert obj.display_name == "file.txt"

    def test_display_name_handles_no_slashes(self) -> None:
        """display_name returns full name when no slashes present."""
        obj = _make_gcs_object(name="file.txt")

        assert obj.display_name == "file.txt"

    def test_display_name_handles_prefix_with_trailing_slash(self) -> None:
        """display_name returns folder name for prefix ending with slash."""
        obj = _make_gcs_object(name="a/b/", size=0)

        assert obj.display_name == "b"

    def test_display_name_handles_deeply_nested_path(self) -> None:
        """display_name works correctly with deeply nested paths."""
        obj = _make_gcs_object(name="level1/level2/level3/level4/document.pdf")

        assert obj.display_name == "document.pdf"


class TestPrefix:
    """Tests for the prefix property."""

    def test_prefix_returns_parent_path(self) -> None:
        """prefix returns parent directory path."""
        obj = _make_gcs_object(name="a/b/file.txt")

        assert obj.prefix == "a/b"

    def test_prefix_returns_empty_for_root_level_file(self) -> None:
        """prefix returns empty string for files at root level."""
        obj = _make_gcs_object(name="file.txt")

        assert obj.prefix == ""

    def test_prefix_handles_trailing_slash(self) -> None:
        """prefix returns correct parent for prefix with trailing slash."""
        obj = _make_gcs_object(name="a/b/c/", size=0)

        assert obj.prefix == "a/b"

    def test_prefix_handles_single_level_directory(self) -> None:
        """prefix returns empty for single-level directory prefix."""
        obj = _make_gcs_object(name="folder/", size=0)

        assert obj.prefix == ""


class TestDisplaySize:
    """Tests for the display_size property."""

    def test_display_size_bytes(self) -> None:
        """display_size returns bytes for small sizes."""
        obj = _make_gcs_object(size=512)

        assert obj.display_size == "512 B"

    def test_display_size_zero_bytes(self) -> None:
        """display_size returns 0 B for zero size."""
        obj = _make_gcs_object(size=0)

        assert obj.display_size == "0 B"

    def test_display_size_kilobytes(self) -> None:
        """display_size returns KB for sizes >= 1024."""
        obj = _make_gcs_object(size=1024)
        assert obj.display_size == "1 KB"

        obj2 = _make_gcs_object(size=1536)  # 1.5 KB
        assert obj2.display_size == "1.5 KB"

    def test_display_size_megabytes(self) -> None:
        """display_size returns MB for sizes >= 1MB."""
        obj = _make_gcs_object(size=1 << 20)  # 1 MB
        assert obj.display_size == "1 MB"

        obj2 = _make_gcs_object(size=int(2.5 * (1 << 20)))  # 2.5 MB
        assert obj2.display_size == "2.5 MB"

    def test_display_size_gigabytes(self) -> None:
        """display_size returns GB for sizes >= 1GB."""
        obj = _make_gcs_object(size=1 << 30)  # 1 GB
        assert obj.display_size == "1 GB"

        obj2 = _make_gcs_object(size=int(3.75 * (1 << 30)))  # 3.75 GB
        assert obj2.display_size == "3.8 GB"

    def test_display_size_terabytes(self) -> None:
        """display_size returns TB for sizes >= 1TB."""
        obj = _make_gcs_object(size=1 << 40)  # 1 TB
        assert obj.display_size == "1 TB"

        obj2 = _make_gcs_object(size=int(1.5 * (1 << 40)))  # 1.5 TB
        assert obj2.display_size == "1.5 TB"


class TestIsPrefix:
    """Tests for the is_prefix property."""

    def test_is_prefix_true_when_size_zero_and_trailing_slash(self) -> None:
        """is_prefix returns True when size=0 and name ends with slash."""
        obj = _make_gcs_object(name="folder/subfolder/", size=0)

        assert obj.is_prefix is True

    def test_is_prefix_false_when_size_greater_than_zero(self) -> None:
        """is_prefix returns False when size > 0."""
        obj = _make_gcs_object(name="folder/", size=100)

        assert obj.is_prefix is False

    def test_is_prefix_false_when_no_trailing_slash(self) -> None:
        """is_prefix returns False when name doesn't end with slash."""
        obj = _make_gcs_object(name="folder/file.txt", size=0)

        assert obj.is_prefix is False

    def test_is_prefix_false_for_regular_file(self) -> None:
        """is_prefix returns False for a regular file."""
        obj = _make_gcs_object(name="data.json", size=256)

        assert obj.is_prefix is False


class TestMetadataField:
    """Tests for the metadata field."""

    def test_metadata_with_custom_values(self) -> None:
        """metadata field stores custom key-value pairs."""
        metadata = {
            "author": "test-user",
            "version": "1.0",
            "custom-header": "value",
        }
        obj = _make_gcs_object(metadata=metadata)

        assert obj.metadata == metadata
        assert obj.metadata["author"] == "test-user"
        assert obj.metadata["version"] == "1.0"
        assert len(obj.metadata) == 3


class TestMD5HashField:
    """Tests for the md5_hash field."""

    def test_md5_hash_with_value(self) -> None:
        """md5_hash field stores the hash value."""
        hash_value = "rL0Y20zC+Fzt72VPzMSk2A=="
        obj = _make_gcs_object(md5_hash=hash_value)

        assert obj.md5_hash == hash_value


class TestGenerationField:
    """Tests for the generation field."""

    def test_generation_stores_value(self) -> None:
        """generation field stores the GCS generation number."""
        obj = _make_gcs_object(generation=9876543210)

        assert obj.generation == 9876543210

    def test_generation_as_large_integer(self) -> None:
        """generation field handles large integer values."""
        large_gen = 16749832740985732
        obj = _make_gcs_object(generation=large_gen)

        assert obj.generation == large_gen


def _make_gcs_object(
    name: str = "test/file.txt",
    bucket_name: str = "test-bucket",
    size: int = 1024,
    content_type: str = "application/octet-stream",
    storage_class: str = "STANDARD",
    created_time: datetime | None = None,
    updated_time: datetime | None = None,
    generation: int = 1,
    metadata: dict[str, str] | None = None,
    md5_hash: str = "",
) -> GCSObject:
    """Factory helper to create GCSObject with sensible defaults."""
    if created_time is None:
        created_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    if updated_time is None:
        updated_time = datetime(2026, 1, 2, 0, 0, 0, tzinfo=timezone.utc)

    kwargs: dict = {
        "name": name,
        "bucket_name": bucket_name,
        "size": size,
        "content_type": content_type,
        "storage_class": storage_class,
        "created_time": created_time,
        "updated_time": updated_time,
        "generation": generation,
    }
    if metadata is not None:
        kwargs["metadata"] = metadata
    if md5_hash:
        kwargs["md5_hash"] = md5_hash

    return GCSObject(**kwargs)