"""MinIO/S3 object storage client for evidence images and video clips."""

import io
import uuid
from pathlib import Path
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from core.config import settings


class StorageClient:
    """Wraps MinIO client for evidence storage."""

    def __init__(self):
        self._client = Minio(
            settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=False,  # HTTP for local dev
        )
        self._bucket = settings.s3_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload_image(self, data: bytes, content_type: str = "image/png",
                     folder: str = "evidence") -> str:
        """Upload image bytes, return object key."""
        key = f"{folder}/{uuid.uuid4().hex}.png"
        self._client.put_object(
            self._bucket, key, io.BytesIO(data), len(data), content_type=content_type
        )
        return key

    def upload_video(self, data: bytes, content_type: str = "video/mp4",
                     folder: str = "clips") -> str:
        """Upload video bytes, return object key."""
        key = f"{folder}/{uuid.uuid4().hex}.mp4"
        self._client.put_object(
            self._bucket, key, io.BytesIO(data), len(data), content_type=content_type
        )
        return key

    def download(self, key: str) -> bytes:
        """Download object by key, return bytes."""
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_presigned_url(self, key: str, expires: timedelta = timedelta(hours=1)) -> str:
        """Get presigned URL for direct client access."""
        return self._client.presigned_get_object(self._bucket, key, expires=expires)

    def delete(self, key: str) -> None:
        """Delete object by key."""
        self._client.remove_object(self._bucket, key)

    def list_objects(self, prefix: str = "") -> list[str]:
        """List object keys with given prefix."""
        return [
            obj.object_name
            for obj in self._client.list_objects(self._bucket, prefix=prefix)
        ]


# Module-level singleton (initialized lazily)
_storage: StorageClient | None = None


def get_storage() -> StorageClient:
    """Get or create storage singleton."""
    global _storage
    if _storage is None:
        _storage = StorageClient()
    return _storage
