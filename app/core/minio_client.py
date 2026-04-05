"""
Cloudflare R2 client — drop-in replacement for the MinIO client.
Exposes the same interface (put_object, get_object, stat_object,
copy_object, remove_object, bucket_exists, make_bucket) so existing
API files need no changes beyond swapping the CopySource import.
"""
import io
from dataclasses import dataclass
from datetime import timezone

import boto3
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError

from ..core.config import settings


# ── CopySource ─────────────────────────────────────────────────────────────
# photos.py and certification.py import this from here instead of minio.commonconfig

@dataclass
class CopySource:
    bucket_name: str
    object_name: str


# ── Response wrappers ───────────────────────────────────────────────────────

class StatObject:
    """Mimics minio StatObject."""
    def __init__(self, head: dict):
        self.size = head["ContentLength"]
        self.content_type = head.get("ContentType", "application/octet-stream")
        lm = head.get("LastModified")
        self.last_modified = lm.astimezone(timezone.utc) if lm else None


class GetObjectResponse:
    """Mimics the response returned by minio_client.get_object()."""
    def __init__(self, response: dict):
        self._body = response["Body"]
        lm = response.get("LastModified")
        self.headers = {
            "content-type": response.get("ContentType", "application/octet-stream"),
            "etag": response.get("ETag", ""),
            "last-modified": lm.strftime("%a, %d %b %Y %H:%M:%S GMT") if lm else "",
        }

    def read(self) -> bytes:
        return self._body.read()

    def __iter__(self):
        return self._body.__iter__()


# ── R2 client ───────────────────────────────────────────────────────────────

class R2Client:
    """boto3-backed S3 client targeting Cloudflare R2."""

    def __init__(self):
        self._s3 = None
        self._backend_name = None

    def _build_r2_client(self):
        return boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.R2_ACCESS_KEY_ID,
            aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )

    def _build_minio_client(self):
        protocol = "https" if settings.MINIO_USE_TLS else "http"
        return boto3.client(
            "s3",
            endpoint_url=f"{protocol}://{settings.MINIO_ENDPOINT}",
            aws_access_key_id=settings.MINIO_ACCESS_KEY,
            aws_secret_access_key=settings.MINIO_SECRET_KEY,
            region_name="us-east-1",
            config=BotocoreConfig(signature_version="s3v4"),
        )

    def _get_s3(self, force_backend: str | None = None):
        if self._s3 is not None:
            return self._s3

        backend = (force_backend or settings.STORAGE_BACKEND).lower()
        use_r2 = backend == "r2" or (backend == "auto" and bool(settings.R2_ACCOUNT_ID))

        if use_r2:
            if not settings.R2_ACCOUNT_ID:
                raise RuntimeError("STORAGE_BACKEND=r2 but R2_ACCOUNT_ID is not set")
            self._s3 = self._build_r2_client()
            self._backend_name = "r2"
            print("☁️  Storage: Cloudflare R2")
        else:
            self._s3 = self._build_minio_client()
            self._backend_name = "minio"
            print(f"🗄️  Storage: MinIO at {settings.MINIO_ENDPOINT}")

        return self._s3

    def reset(self):
        self._s3 = None
        self._backend_name = None

    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str):
        self._get_s3().put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=data,
            ContentLength=length,
            ContentType=content_type,
        )

    def get_object(self, bucket: str, key: str) -> GetObjectResponse:
        response = self._get_s3().get_object(Bucket=bucket, Key=key)
        return GetObjectResponse(response)

    def stat_object(self, bucket: str, key: str) -> StatObject:
        response = self._get_s3().head_object(Bucket=bucket, Key=key)
        return StatObject(response)

    def copy_object(self, dest_bucket: str, dest_key: str, source: CopySource):
        self._get_s3().copy_object(
            Bucket=dest_bucket,
            Key=dest_key,
            CopySource={"Bucket": source.bucket_name, "Key": source.object_name},
        )

    def remove_object(self, bucket: str, key: str):
        self._get_s3().delete_object(Bucket=bucket, Key=key)

    def bucket_exists(self, bucket: str) -> bool:
        try:
            self._get_s3().head_bucket(Bucket=bucket)
            return True
        except ClientError:
            return False

    def make_bucket(self, bucket: str):
        self._get_s3().create_bucket(Bucket=bucket)


minio_client = R2Client()


def ensure_buckets():
    backend = settings.STORAGE_BACKEND.lower()
    try:
        for bucket in ["cert-temp", "certificates", "job-photos"]:
            if not minio_client.bucket_exists(bucket):
                minio_client.make_bucket(bucket)
        storage_label = "R2" if minio_client._backend_name == "r2" else "MinIO"
        print(f"✅ {storage_label} buckets ready.")
    except Exception as e:
        if backend == "auto":
            print(f"⚠️  WARNING: R2 not available ({e}). Falling back to MinIO.")
            try:
                minio_client.reset()
                minio_client._get_s3(force_backend="minio")
                for bucket in ["cert-temp", "certificates", "job-photos"]:
                    if not minio_client.bucket_exists(bucket):
                        minio_client.make_bucket(bucket)
                print("✅ MinIO buckets ready after fallback.")
                return
            except Exception as minio_error:
                print(f"⚠️  WARNING: MinIO fallback also failed ({minio_error}). File upload features will be disabled.")
                return
        print(f"⚠️  WARNING: Storage backend unavailable ({e}). File upload features will be disabled.")
