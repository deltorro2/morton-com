"""Google Cloud Storage client service.

Wraps the ``google-cloud-storage`` library, providing typed methods for
bucket and object operations with error mapping to MortonError hierarchy.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from src.errors import AuthenticationError, NetworkError, PermissionError, TransferError
from src.models.gcs_bucket import GCSBucket
from src.models.gcs_object import GCSObject

logger = logging.getLogger(__name__)

_PAGE_SIZE = 1000


class GCSClient:
    """Service for Google Cloud Storage operations."""

    def __init__(self) -> None:
        self._client = None
        self._credentials = None

    def set_credentials(self, credentials: object) -> None:
        """Set OAuth2 credentials and create the storage client."""
        from google.cloud import storage

        self._credentials = credentials
        self._client = storage.Client(credentials=credentials)
        logger.info("GCS client initialized")

    def is_authenticated(self) -> bool:
        """Return ``True`` if credentials are set."""
        return self._client is not None

    def _ensure_client(self) -> None:
        if self._client is None:
            raise AuthenticationError(
                message="GCS client not authenticated",
                user_message="You are not signed in.",
                suggested_action="Sign in with Google to access GCS.",
            )

    # ------------------------------------------------------------------
    # Buckets
    # ------------------------------------------------------------------

    def list_buckets(self, project_id: str) -> list[GCSBucket]:
        """List all buckets in a project."""
        self._ensure_client()
        try:
            buckets = list(self._client.list_buckets(project=project_id))
            return [
                GCSBucket(
                    name=b.name,
                    project_id=project_id,
                    location=b.location or "",
                    storage_class=b.storage_class or "STANDARD",
                    created_time=b.time_created,
                    versioning_enabled=b.versioning_enabled or False,
                )
                for b in buckets
            ]
        except Exception as exc:
            raise self._map_exception(exc, f"listing buckets in {project_id}") from exc

    # ------------------------------------------------------------------
    # Objects
    # ------------------------------------------------------------------

    def list_objects(
        self,
        bucket_name: str,
        prefix: str = "",
        delimiter: str = "/",
    ) -> tuple[list[GCSObject], list[str]]:
        """List objects in a bucket with prefix-based folder browsing.

        Returns (objects, prefixes) where prefixes are pseudo-directories.
        """
        self._ensure_client()
        try:
            bucket = self._client.bucket(bucket_name)
            blobs = bucket.list_blobs(
                prefix=prefix,
                delimiter=delimiter,
                max_results=_PAGE_SIZE,
            )

            objects: list[GCSObject] = []
            for blob in blobs:
                # Skip the prefix itself
                if blob.name == prefix:
                    continue
                objects.append(self._blob_to_gcs_object(blob, bucket_name))

            prefixes = list(blobs.prefixes)
            return objects, prefixes

        except Exception as exc:
            raise self._map_exception(
                exc, f"listing objects in {bucket_name}/{prefix}"
            ) from exc

    def get_object_metadata(self, bucket_name: str, object_name: str) -> GCSObject:
        """Get detailed metadata for a single object."""
        self._ensure_client()
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.reload()
            return self._blob_to_gcs_object(blob, bucket_name)
        except Exception as exc:
            raise self._map_exception(
                exc, f"getting metadata for {bucket_name}/{object_name}"
            ) from exc

    def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check if an object exists."""
        self._ensure_client()
        try:
            bucket = self._client.bucket(bucket_name)
            return bucket.blob(object_name).exists()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Upload / Download
    # ------------------------------------------------------------------

    def upload_file(
        self,
        local_path: Path,
        bucket_name: str,
        object_name: str,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> GCSObject:
        """Upload a local file to GCS using resumable upload."""
        self._ensure_client()
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(object_name)

            total_bytes = local_path.stat().st_size

            if progress_callback and total_bytes > 0:
                # Use resumable upload with progress
                blob.upload_from_filename(
                    str(local_path),
                    timeout=300,
                )
                progress_callback(total_bytes, total_bytes)
            else:
                blob.upload_from_filename(str(local_path), timeout=300)

            blob.reload()
            logger.info("Uploaded %s to gs://%s/%s", local_path, bucket_name, object_name)
            return self._blob_to_gcs_object(blob, bucket_name)

        except Exception as exc:
            raise TransferError(
                message=f"Upload failed: {local_path} -> gs://{bucket_name}/{object_name}: {exc}",
                user_message=f'Could not upload "{local_path.name}".',
                suggested_action="Check your network connection and try again.",
                technical_detail=str(exc),
            ) from exc

    def download_file(
        self,
        bucket_name: str,
        object_name: str,
        local_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> None:
        """Download a GCS object to a local file."""
        self._ensure_client()
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.reload()

            total_bytes = blob.size or 0

            blob.download_to_filename(str(local_path), timeout=300)

            if progress_callback and total_bytes > 0:
                progress_callback(total_bytes, total_bytes)

            logger.info(
                "Downloaded gs://%s/%s to %s", bucket_name, object_name, local_path
            )

        except Exception as exc:
            raise TransferError(
                message=f"Download failed: gs://{bucket_name}/{object_name} -> {local_path}: {exc}",
                user_message=f'Could not download "{object_name.rsplit("/", 1)[-1]}".',
                suggested_action="Check your network connection and available disk space.",
                technical_detail=str(exc),
            ) from exc

    def copy_object(
        self,
        source_bucket: str,
        source_name: str,
        dest_bucket: str,
        dest_name: str,
    ) -> GCSObject:
        """Server-side copy of an object within GCS."""
        self._ensure_client()
        try:
            src_bucket = self._client.bucket(source_bucket)
            src_blob = src_bucket.blob(source_name)
            dst_bucket = self._client.bucket(dest_bucket)

            new_blob = src_bucket.copy_blob(src_blob, dst_bucket, dest_name)
            logger.info(
                "Copied gs://%s/%s -> gs://%s/%s",
                source_bucket, source_name, dest_bucket, dest_name,
            )
            return self._blob_to_gcs_object(new_blob, dest_bucket)

        except Exception as exc:
            raise TransferError(
                message=f"GCS copy failed: {source_bucket}/{source_name} -> {dest_bucket}/{dest_name}: {exc}",
                user_message="Could not copy the object within GCS.",
                suggested_action="Check permissions on both buckets.",
                technical_detail=str(exc),
            ) from exc

    def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete a GCS object."""
        self._ensure_client()
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            blob.delete()
            logger.info("Deleted gs://%s/%s", bucket_name, object_name)
        except Exception as exc:
            raise self._map_exception(
                exc, f"deleting gs://{bucket_name}/{object_name}"
            ) from exc

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _blob_to_gcs_object(blob: object, bucket_name: str) -> GCSObject:
        """Convert a google.cloud.storage.Blob to a GCSObject."""
        from datetime import datetime, timezone

        return GCSObject(
            name=blob.name,
            bucket_name=bucket_name,
            size=blob.size or 0,
            content_type=blob.content_type or "",
            storage_class=blob.storage_class or "STANDARD",
            created_time=blob.time_created or datetime.now(timezone.utc),
            updated_time=blob.updated or datetime.now(timezone.utc),
            generation=blob.generation or 0,
            metadata=dict(blob.metadata) if blob.metadata else {},
            md5_hash=blob.md5_hash or "",
        )

    @staticmethod
    def _map_exception(exc: Exception, context: str) -> Exception:
        """Map GCS library exceptions to MortonError subclasses."""
        exc_str = str(exc).lower()

        if "403" in exc_str or "forbidden" in exc_str:
            return PermissionError(
                message=f"Permission denied: {context}: {exc}",
                user_message="You don't have permission for this operation.",
                suggested_action="Check that your account has the required IAM roles.",
                technical_detail=str(exc),
            )
        if "401" in exc_str or "unauthorized" in exc_str:
            return AuthenticationError(
                message=f"Authentication failed: {context}: {exc}",
                user_message="Your session has expired.",
                suggested_action="Sign in again.",
                technical_detail=str(exc),
            )
        if "timeout" in exc_str or "connection" in exc_str:
            return NetworkError(
                message=f"Network error: {context}: {exc}",
                user_message="Network connection failed.",
                suggested_action="Check your internet connection and try again.",
                technical_detail=str(exc),
            )

        return TransferError(
            message=f"GCS operation failed: {context}: {exc}",
            user_message="An error occurred during the GCS operation.",
            suggested_action="Try again or check the application logs.",
            technical_detail=str(exc),
        )
