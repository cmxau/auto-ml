import threading
import boto3
from botocore.client import Config
from typing import BinaryIO

from app.config import settings


class StorageService:
    def __init__(self):
        self._client = None
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = boto3.client(
                        "s3",
                        endpoint_url=f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}",
                        aws_access_key_id=settings.MINIO_ACCESS_KEY,
                        aws_secret_access_key=settings.MINIO_SECRET_KEY,
                        config=Config(signature_version="s3v4"),
                        region_name="us-east-1",
                    )
        return self._client

    @property
    def bucket(self):
        return settings.MINIO_BUCKET

    def ensure_bucket(self):
        """Create bucket if it doesn't exist. Call at startup."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)

    def upload_file(self, file_obj: BinaryIO, key: str, content_type: str) -> str:
        self.client.upload_fileobj(
            file_obj,
            self.bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    def download_file(self, key: str) -> bytes:
        resp = self.client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        url = self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        public_endpoint = settings.MINIO_PUBLIC_ENDPOINT or settings.MINIO_ENDPOINT
        if public_endpoint != settings.MINIO_ENDPOINT:
            internal = f"{'https' if settings.MINIO_USE_SSL else 'http'}://{settings.MINIO_ENDPOINT}"
            public = f"{'https' if settings.MINIO_USE_SSL else 'http'}://{public_endpoint}"
            url = url.replace(internal, public, 1)
        return url


storage = StorageService()


def resolve_format(storage_uri: str, fallback: str) -> str:
    """Detect file format from storage URI extension; fall back to dataset.file_format."""
    lower = (storage_uri or "").lower().split("?")[0]
    if lower.endswith(".csv"):
        return "csv"
    if lower.endswith(".xlsx") or lower.endswith(".xls"):
        return "xlsx"
    if lower.endswith(".json"):
        return "json"
    return fallback
