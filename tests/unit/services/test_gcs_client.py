"""Unit tests for GCSClient service.

Tests cover authentication, bucket listing, object operations,
file upload/download, copy/delete operations, and exception mapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock, PropertyMock, create_autospec, patch

import pytest

from src.errors import (
    AuthenticationError,
    NetworkError,
    PermissionError,
    TransferError,
)
from src.models.gcs_bucket import GCSBucket
from src.models.gcs_object import GCSObject
from src.services.gcs_client import GCSClient


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def gcs_client() -> GCSClient:
    """Create a fresh GCSClient instance."""
    return GCSClient()


@pytest.fixture
def mock_storage_client() -> MagicMock:
    """Create a mock google.cloud.storage.Client."""
    return MagicMock()


@pytest.fixture
def mock_credentials() -> MagicMock:
    """Create mock OAuth2 credentials."""
    return MagicMock()


@pytest.fixture
def mock_blob() -> MagicMock:
    """Create a mock Blob with typical attributes."""
    blob = MagicMock()
    blob.name = "folder/file.txt"
    blob.size = 1024
    blob.content_type = "text/plain"
    blob.storage_class = "STANDARD"
    blob.time_created = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    blob.updated = datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc)
    blob.generation = 123456789
    blob.metadata = {"key": "value"}
    blob.md5_hash = "abc123=="
    return blob


@pytest.fixture
def mock_bucket_obj() -> MagicMock:
    """Create a mock Bucket with typical attributes."""
    bucket = MagicMock()
    bucket.name = "test-bucket"
    bucket.location = "US-CENTRAL1"
    bucket.storage_class = "STANDARD"
    bucket.time_created = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    bucket.versioning_enabled = False
    return bucket


@pytest.fixture
def authenticated_client(
    gcs_client: GCSClient, mock_credentials: MagicMock
) -> GCSClient:
    """Create an authenticated GCSClient with mocked storage client."""
    mock_storage_module = MagicMock()
    mock_storage_module.Client.return_value = MagicMock()
    with patch.dict("sys.modules", {"google.cloud.storage": mock_storage_module}):
        gcs_client.set_credentials(mock_credentials)
    return gcs_client


# -----------------------------------------------------------------------------
# Test Classes
# -----------------------------------------------------------------------------


class TestInitialState:
    """Tests for initial GCSClient state."""

    def test_is_authenticated_returns_false_initially(
        self, gcs_client: GCSClient
    ) -> None:
        """is_authenticated() returns False when no credentials are set."""
        assert gcs_client.is_authenticated() is False


class TestSetCredentials:
    """Tests for set_credentials method."""

    def test_set_credentials_creates_client_and_authenticates(
        self, gcs_client: GCSClient, mock_credentials: MagicMock
    ) -> None:
        """set_credentials sets client and is_authenticated returns True."""
        mock_storage_module = MagicMock()
        mock_storage_client = MagicMock()
        mock_storage_module.Client.return_value = mock_storage_client

        with patch.dict("sys.modules", {"google.cloud.storage": mock_storage_module}):
            gcs_client.set_credentials(mock_credentials)

            assert gcs_client.is_authenticated() is True
            mock_storage_module.Client.assert_called_once_with(credentials=mock_credentials)


class TestEnsureClient:
    """Tests for _ensure_client method."""

    def test_ensure_client_raises_authentication_error_when_not_set(
        self, gcs_client: GCSClient
    ) -> None:
        """_ensure_client raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError) as exc_info:
            gcs_client._ensure_client()

        assert "not authenticated" in str(exc_info.value)
        assert exc_info.value.user_message == "You are not signed in."


class TestListBuckets:
    """Tests for list_buckets method."""

    def test_list_buckets_returns_list_of_gcs_bucket(
        self, authenticated_client: GCSClient, mock_bucket_obj: MagicMock
    ) -> None:
        """list_buckets returns list of GCSBucket objects."""
        authenticated_client._client.list_buckets.return_value = [mock_bucket_obj]

        result = authenticated_client.list_buckets("test-project")

        assert len(result) == 1
        assert isinstance(result[0], GCSBucket)
        assert result[0].name == "test-bucket"
        assert result[0].project_id == "test-project"
        assert result[0].location == "US-CENTRAL1"
        authenticated_client._client.list_buckets.assert_called_once_with(
            project="test-project"
        )

    def test_list_buckets_raises_mapped_exception_on_error(
        self, authenticated_client: GCSClient
    ) -> None:
        """list_buckets raises mapped exception when GCS API fails."""
        authenticated_client._client.list_buckets.side_effect = Exception(
            "403 Forbidden"
        )

        with pytest.raises(PermissionError) as exc_info:
            authenticated_client.list_buckets("test-project")

        assert "Permission denied" in str(exc_info.value)


class TestListObjects:
    """Tests for list_objects method."""

    def test_list_objects_returns_objects_and_prefixes(
        self, authenticated_client: GCSClient, mock_blob: MagicMock
    ) -> None:
        """list_objects returns tuple of objects and prefixes."""
        mock_bucket = MagicMock()
        mock_blobs_iterator = MagicMock()
        mock_blobs_iterator.__iter__ = Mock(return_value=iter([mock_blob]))
        mock_blobs_iterator.prefixes = ["folder1/", "folder2/"]
        mock_bucket.list_blobs.return_value = mock_blobs_iterator
        authenticated_client._client.bucket.return_value = mock_bucket

        objects, prefixes = authenticated_client.list_objects(
            "test-bucket", prefix="data/", delimiter="/"
        )

        assert len(objects) == 1
        assert isinstance(objects[0], GCSObject)
        assert objects[0].name == "folder/file.txt"
        assert prefixes == ["folder1/", "folder2/"]
        mock_bucket.list_blobs.assert_called_once()

    def test_list_objects_skips_prefix_itself(
        self, authenticated_client: GCSClient
    ) -> None:
        """list_objects skips the blob matching the prefix exactly."""
        mock_bucket = MagicMock()
        prefix_blob = MagicMock()
        prefix_blob.name = "data/"
        prefix_blob.size = 0
        prefix_blob.content_type = ""
        prefix_blob.storage_class = "STANDARD"
        prefix_blob.time_created = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        prefix_blob.updated = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        prefix_blob.generation = 1
        prefix_blob.metadata = None
        prefix_blob.md5_hash = ""

        file_blob = MagicMock()
        file_blob.name = "data/file.txt"
        file_blob.size = 100
        file_blob.content_type = "text/plain"
        file_blob.storage_class = "STANDARD"
        file_blob.time_created = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        file_blob.updated = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        file_blob.generation = 2
        file_blob.metadata = None
        file_blob.md5_hash = ""

        mock_blobs_iterator = MagicMock()
        mock_blobs_iterator.__iter__ = Mock(
            return_value=iter([prefix_blob, file_blob])
        )
        mock_blobs_iterator.prefixes = []
        mock_bucket.list_blobs.return_value = mock_blobs_iterator
        authenticated_client._client.bucket.return_value = mock_bucket

        objects, _ = authenticated_client.list_objects(
            "test-bucket", prefix="data/", delimiter="/"
        )

        assert len(objects) == 1
        assert objects[0].name == "data/file.txt"


class TestGetObjectMetadata:
    """Tests for get_object_metadata method."""

    def test_get_object_metadata_returns_gcs_object(
        self, authenticated_client: GCSClient, mock_blob: MagicMock
    ) -> None:
        """get_object_metadata returns GCSObject with metadata."""
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        result = authenticated_client.get_object_metadata("test-bucket", "folder/file.txt")

        assert isinstance(result, GCSObject)
        assert result.name == "folder/file.txt"
        assert result.bucket_name == "test-bucket"
        assert result.size == 1024
        mock_blob.reload.assert_called_once()


class TestObjectExists:
    """Tests for object_exists method."""

    def test_object_exists_returns_true_when_exists(
        self, authenticated_client: GCSClient
    ) -> None:
        """object_exists returns True when blob exists."""
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        result = authenticated_client.object_exists("test-bucket", "file.txt")

        assert result is True

    def test_object_exists_returns_false_when_not_exists(
        self, authenticated_client: GCSClient
    ) -> None:
        """object_exists returns False when blob does not exist."""
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        result = authenticated_client.object_exists("test-bucket", "nonexistent.txt")

        assert result is False

    def test_object_exists_returns_false_on_exception(
        self, authenticated_client: GCSClient
    ) -> None:
        """object_exists returns False when exception occurs."""
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.exists.side_effect = Exception("Network error")
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        result = authenticated_client.object_exists("test-bucket", "file.txt")

        assert result is False


class TestUploadFile:
    """Tests for upload_file method."""

    def test_upload_file_uploads_and_returns_gcs_object(
        self, authenticated_client: GCSClient, tmp_path: Path
    ) -> None:
        """upload_file uploads file and returns GCSObject."""
        test_file = tmp_path / "upload_test.txt"
        test_file.write_text("test content")

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.name = "upload_test.txt"
        mock_blob.size = 12
        mock_blob.content_type = "text/plain"
        mock_blob.storage_class = "STANDARD"
        mock_blob.time_created = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_blob.updated = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_blob.generation = 1
        mock_blob.metadata = None
        mock_blob.md5_hash = ""
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        result = authenticated_client.upload_file(
            test_file, "test-bucket", "upload_test.txt"
        )

        assert isinstance(result, GCSObject)
        assert result.name == "upload_test.txt"
        mock_blob.upload_from_filename.assert_called_once()
        mock_blob.reload.assert_called_once()

    def test_upload_file_with_progress_callback(
        self, authenticated_client: GCSClient, tmp_path: Path
    ) -> None:
        """upload_file calls progress_callback with total bytes."""
        test_file = tmp_path / "upload_test.txt"
        test_file.write_text("test content")
        file_size = test_file.stat().st_size

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.name = "upload_test.txt"
        mock_blob.size = file_size
        mock_blob.content_type = "text/plain"
        mock_blob.storage_class = "STANDARD"
        mock_blob.time_created = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_blob.updated = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_blob.generation = 1
        mock_blob.metadata = None
        mock_blob.md5_hash = ""
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        progress_callback = MagicMock()

        authenticated_client.upload_file(
            test_file,
            "test-bucket",
            "upload_test.txt",
            progress_callback=progress_callback,
        )

        progress_callback.assert_called_once_with(file_size, file_size)

    def test_upload_file_raises_transfer_error_on_failure(
        self, authenticated_client: GCSClient, tmp_path: Path
    ) -> None:
        """upload_file raises TransferError when upload fails."""
        test_file = tmp_path / "upload_test.txt"
        test_file.write_text("test content")

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.upload_from_filename.side_effect = Exception("Upload failed")
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        with pytest.raises(TransferError) as exc_info:
            authenticated_client.upload_file(
                test_file, "test-bucket", "upload_test.txt"
            )

        assert "Upload failed" in str(exc_info.value)
        assert "Could not upload" in exc_info.value.user_message


class TestDownloadFile:
    """Tests for download_file method."""

    def test_download_file_downloads_to_local_path(
        self, authenticated_client: GCSClient, tmp_path: Path
    ) -> None:
        """download_file downloads file to specified local path."""
        local_path = tmp_path / "downloaded.txt"

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.size = 100
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        authenticated_client.download_file(
            "test-bucket", "folder/file.txt", local_path
        )

        mock_blob.reload.assert_called_once()
        mock_blob.download_to_filename.assert_called_once_with(str(local_path), timeout=300)

    def test_download_file_with_progress_callback(
        self, authenticated_client: GCSClient, tmp_path: Path
    ) -> None:
        """download_file calls progress_callback with total bytes."""
        local_path = tmp_path / "downloaded.txt"

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.size = 500
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        progress_callback = MagicMock()

        authenticated_client.download_file(
            "test-bucket",
            "folder/file.txt",
            local_path,
            progress_callback=progress_callback,
        )

        progress_callback.assert_called_once_with(500, 500)

    def test_download_file_raises_transfer_error_on_failure(
        self, authenticated_client: GCSClient, tmp_path: Path
    ) -> None:
        """download_file raises TransferError when download fails."""
        local_path = tmp_path / "downloaded.txt"

        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.size = 100
        mock_blob.download_to_filename.side_effect = Exception("Download failed")
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        with pytest.raises(TransferError) as exc_info:
            authenticated_client.download_file(
                "test-bucket", "folder/file.txt", local_path
            )

        assert "Download failed" in str(exc_info.value)
        assert "Could not download" in exc_info.value.user_message


class TestCopyObject:
    """Tests for copy_object method."""

    def test_copy_object_copies_and_returns_gcs_object(
        self, authenticated_client: GCSClient
    ) -> None:
        """copy_object performs server-side copy and returns GCSObject."""
        mock_src_bucket = MagicMock()
        mock_dst_bucket = MagicMock()
        mock_src_blob = MagicMock()
        mock_new_blob = MagicMock()
        mock_new_blob.name = "dest/file.txt"
        mock_new_blob.size = 1024
        mock_new_blob.content_type = "text/plain"
        mock_new_blob.storage_class = "STANDARD"
        mock_new_blob.time_created = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_new_blob.updated = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        mock_new_blob.generation = 2
        mock_new_blob.metadata = None
        mock_new_blob.md5_hash = ""

        mock_src_bucket.blob.return_value = mock_src_blob
        mock_src_bucket.copy_blob.return_value = mock_new_blob

        def bucket_side_effect(name: str) -> MagicMock:
            if name == "source-bucket":
                return mock_src_bucket
            return mock_dst_bucket

        authenticated_client._client.bucket.side_effect = bucket_side_effect

        result = authenticated_client.copy_object(
            "source-bucket", "src/file.txt", "dest-bucket", "dest/file.txt"
        )

        assert isinstance(result, GCSObject)
        assert result.name == "dest/file.txt"
        mock_src_bucket.copy_blob.assert_called_once_with(
            mock_src_blob, mock_dst_bucket, "dest/file.txt"
        )

    def test_copy_object_raises_transfer_error_on_failure(
        self, authenticated_client: GCSClient
    ) -> None:
        """copy_object raises TransferError when copy fails."""
        mock_bucket = MagicMock()
        mock_bucket.copy_blob.side_effect = Exception("Copy failed")
        authenticated_client._client.bucket.return_value = mock_bucket

        with pytest.raises(TransferError) as exc_info:
            authenticated_client.copy_object(
                "source-bucket", "src/file.txt", "dest-bucket", "dest/file.txt"
            )

        assert "copy failed" in str(exc_info.value).lower()


class TestDeleteObject:
    """Tests for delete_object method."""

    def test_delete_object_deletes_blob(
        self, authenticated_client: GCSClient
    ) -> None:
        """delete_object calls blob.delete()."""
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        authenticated_client._client.bucket.return_value = mock_bucket

        authenticated_client.delete_object("test-bucket", "folder/file.txt")

        mock_bucket.blob.assert_called_once_with("folder/file.txt")
        mock_blob.delete.assert_called_once()


class TestMapException:
    """Tests for _map_exception static method."""

    def test_map_exception_maps_403_to_permission_error(self) -> None:
        """_map_exception maps 403 Forbidden to PermissionError."""
        exc = Exception("403 Forbidden: Access denied")

        result = GCSClient._map_exception(exc, "listing buckets")

        assert isinstance(result, PermissionError)
        assert "Permission denied" in str(result)
        assert "listing buckets" in str(result)

    def test_map_exception_maps_forbidden_to_permission_error(self) -> None:
        """_map_exception maps 'forbidden' keyword to PermissionError."""
        exc = Exception("Access forbidden for this resource")

        result = GCSClient._map_exception(exc, "accessing object")

        assert isinstance(result, PermissionError)

    def test_map_exception_maps_401_to_authentication_error(self) -> None:
        """_map_exception maps 401 Unauthorized to AuthenticationError."""
        exc = Exception("401 Unauthorized: Invalid credentials")

        result = GCSClient._map_exception(exc, "listing objects")

        assert isinstance(result, AuthenticationError)
        assert "Authentication failed" in str(result)

    def test_map_exception_maps_unauthorized_to_authentication_error(self) -> None:
        """_map_exception maps 'unauthorized' keyword to AuthenticationError."""
        exc = Exception("Request unauthorized")

        result = GCSClient._map_exception(exc, "fetching metadata")

        assert isinstance(result, AuthenticationError)

    def test_map_exception_maps_timeout_to_network_error(self) -> None:
        """_map_exception maps timeout to NetworkError."""
        exc = Exception("Connection timeout after 30s")

        result = GCSClient._map_exception(exc, "downloading file")

        assert isinstance(result, NetworkError)
        assert "Network error" in str(result)

    def test_map_exception_maps_connection_to_network_error(self) -> None:
        """_map_exception maps connection error to NetworkError."""
        exc = Exception("Connection refused by server")

        result = GCSClient._map_exception(exc, "uploading file")

        assert isinstance(result, NetworkError)

    def test_map_exception_maps_unknown_to_transfer_error(self) -> None:
        """_map_exception maps unknown exceptions to TransferError."""
        exc = Exception("Some unknown error occurred")

        result = GCSClient._map_exception(exc, "processing request")

        assert isinstance(result, TransferError)
        assert "GCS operation failed" in str(result)


class TestBlobToGcsObject:
    """Tests for _blob_to_gcs_object static method."""

    def test_blob_to_gcs_object_converts_blob(self, mock_blob: MagicMock) -> None:
        """_blob_to_gcs_object correctly converts a blob to GCSObject."""
        result = GCSClient._blob_to_gcs_object(mock_blob, "test-bucket")

        assert isinstance(result, GCSObject)
        assert result.name == "folder/file.txt"
        assert result.bucket_name == "test-bucket"
        assert result.size == 1024
        assert result.content_type == "text/plain"
        assert result.storage_class == "STANDARD"
        assert result.generation == 123456789
        assert result.metadata == {"key": "value"}
        assert result.md5_hash == "abc123=="

    def test_blob_to_gcs_object_handles_none_values(self) -> None:
        """_blob_to_gcs_object handles None values gracefully."""
        mock_blob = MagicMock()
        mock_blob.name = "file.txt"
        mock_blob.size = None
        mock_blob.content_type = None
        mock_blob.storage_class = None
        mock_blob.time_created = None
        mock_blob.updated = None
        mock_blob.generation = None
        mock_blob.metadata = None
        mock_blob.md5_hash = None

        result = GCSClient._blob_to_gcs_object(mock_blob, "bucket")

        assert result.name == "file.txt"
        assert result.size == 0
        assert result.content_type == ""
        assert result.storage_class == "STANDARD"
        assert result.metadata == {}
        assert result.md5_hash == ""


class TestAuthenticationRequired:
    """Tests verifying methods require authentication."""

    def test_list_buckets_requires_authentication(
        self, gcs_client: GCSClient
    ) -> None:
        """list_buckets raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.list_buckets("test-project")

    def test_list_objects_requires_authentication(
        self, gcs_client: GCSClient
    ) -> None:
        """list_objects raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.list_objects("test-bucket")

    def test_get_object_metadata_requires_authentication(
        self, gcs_client: GCSClient
    ) -> None:
        """get_object_metadata raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.get_object_metadata("test-bucket", "file.txt")

    def test_object_exists_requires_authentication(
        self, gcs_client: GCSClient
    ) -> None:
        """object_exists raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.object_exists("test-bucket", "file.txt")

    def test_upload_file_requires_authentication(
        self, gcs_client: GCSClient, tmp_path: Path
    ) -> None:
        """upload_file raises AuthenticationError when not authenticated."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        with pytest.raises(AuthenticationError):
            gcs_client.upload_file(test_file, "test-bucket", "test.txt")

    def test_download_file_requires_authentication(
        self, gcs_client: GCSClient, tmp_path: Path
    ) -> None:
        """download_file raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.download_file("test-bucket", "file.txt", tmp_path / "out.txt")

    def test_copy_object_requires_authentication(
        self, gcs_client: GCSClient
    ) -> None:
        """copy_object raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.copy_object("src-bucket", "src.txt", "dst-bucket", "dst.txt")

    def test_delete_object_requires_authentication(
        self, gcs_client: GCSClient
    ) -> None:
        """delete_object raises AuthenticationError when not authenticated."""
        with pytest.raises(AuthenticationError):
            gcs_client.delete_object("test-bucket", "file.txt")
