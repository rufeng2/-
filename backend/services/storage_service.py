"""Local document cache backed by optional MinIO object storage."""
from pathlib import Path
import shutil
from uuid import uuid4

from backend.config import settings
from backend.utils.logger import logger


class StorageService:
    def __init__(self):
        self.local_dir = Path(settings.UPLOAD_DIR).resolve()
        self.local_dir.mkdir(parents=True, exist_ok=True)

    def _client(self):
        import boto3
        return boto3.client(
            "s3",
            endpoint_url=("https://" if settings.MINIO_SECURE else "http://") + settings.MINIO_ENDPOINT,
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
        )

    def save(self, content: bytes, suffix: str, prefix: str = "") -> str:
        path = self.local_dir / f"{prefix}{uuid4().hex}{suffix}"
        path.write_bytes(content)
        if settings.USE_MINIO:
            try:
                client = self._client()
                try:
                    client.head_bucket(Bucket=settings.MINIO_BUCKET)
                except Exception:
                    client.create_bucket(Bucket=settings.MINIO_BUCKET)
                client.upload_file(str(path), settings.MINIO_BUCKET, path.name)
            except Exception:
                path.unlink(missing_ok=True)
                raise
        return str(path)

    async def save_upload(self, upload, suffix: str, max_bytes: int) -> tuple[str, int]:
        """Stream an UploadFile to disk with an enforced size limit."""
        path = self.local_dir / f"{uuid4().hex}{suffix}"
        total = 0
        try:
            with path.open("wb") as target:
                while True:
                    chunk = await upload.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("upload_too_large")
                    target.write(chunk)
            if settings.USE_MINIO:
                client = self._client()
                try:
                    client.head_bucket(Bucket=settings.MINIO_BUCKET)
                except Exception:
                    client.create_bucket(Bucket=settings.MINIO_BUCKET)
                client.upload_file(str(path), settings.MINIO_BUCKET, path.name)
            return str(path), total
        except Exception:
            path.unlink(missing_ok=True)
            raise
    def delete(self, storage_path: str) -> None:
        path = Path(storage_path).resolve()
        path.unlink(missing_ok=True)
        asset_dir = (path.parent / f"{path.stem}_assets").resolve()
        if asset_dir.parent == path.parent and asset_dir.name.endswith("_assets") and asset_dir.exists():
            shutil.rmtree(asset_dir)
        if settings.USE_MINIO:
            try:
                self._client().delete_object(Bucket=settings.MINIO_BUCKET, Key=path.name)
            except Exception as exc:
                logger.warning(f"MinIO delete failed: {exc}")


storage_service = StorageService()
