"""Unit tests for the GCSBucket dataclass.

Tests cover:
- Basic instantiation with all required fields
- display_location property transformations
- versioning_enabled boolean states
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.models.gcs_bucket import GCSBucket


class TestGCSBucketCreation:
    """Tests for GCSBucket instantiation."""

    def test_create_gcs_bucket_with_all_fields(self) -> None:
        """GCSBucket can be created with all required fields."""
        created = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)

        bucket = GCSBucket(
            name="my-test-bucket",
            project_id="test-project-123",
            location="us-east1",
            storage_class="STANDARD",
            created_time=created,
            versioning_enabled=True,
        )

        assert bucket.name == "my-test-bucket"
        assert bucket.project_id == "test-project-123"
        assert bucket.location == "us-east1"
        assert bucket.storage_class == "STANDARD"
        assert bucket.created_time == created
        assert bucket.versioning_enabled is True


class TestDisplayLocation:
    """Tests for the display_location property."""

    def test_display_location_converts_lowercase_hyphenated(self) -> None:
        """display_location converts 'us-east1' to 'Us East1'."""
        bucket = GCSBucket(
            name="bucket",
            project_id="project",
            location="us-east1",
            storage_class="STANDARD",
            created_time=datetime.now(timezone.utc),
            versioning_enabled=False,
        )

        assert bucket.display_location == "Us East1"

    def test_display_location_converts_uppercase_hyphenated(self) -> None:
        """display_location converts 'US-CENTRAL1' to 'Us Central1'."""
        bucket = GCSBucket(
            name="bucket",
            project_id="project",
            location="US-CENTRAL1",
            storage_class="STANDARD",
            created_time=datetime.now(timezone.utc),
            versioning_enabled=False,
        )

        assert bucket.display_location == "Us Central1"

    def test_display_location_handles_no_hyphens(self) -> None:
        """display_location handles location without hyphens (e.g., 'US')."""
        bucket = GCSBucket(
            name="bucket",
            project_id="project",
            location="US",
            storage_class="STANDARD",
            created_time=datetime.now(timezone.utc),
            versioning_enabled=False,
        )

        assert bucket.display_location == "Us"


class TestVersioningEnabled:
    """Tests for the versioning_enabled field."""

    def test_versioning_enabled_true(self) -> None:
        """GCSBucket with versioning_enabled=True stores that value."""
        bucket = GCSBucket(
            name="versioned-bucket",
            project_id="project",
            location="us-west1",
            storage_class="NEARLINE",
            created_time=datetime.now(timezone.utc),
            versioning_enabled=True,
        )

        assert bucket.versioning_enabled is True

    def test_versioning_enabled_false(self) -> None:
        """GCSBucket with versioning_enabled=False stores that value."""
        bucket = GCSBucket(
            name="unversioned-bucket",
            project_id="project",
            location="eu-west1",
            storage_class="COLDLINE",
            created_time=datetime.now(timezone.utc),
            versioning_enabled=False,
        )

        assert bucket.versioning_enabled is False
