from minio import Minio
from ..core.config import settings

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_USE_TLS,
)

# Ensure buckets exist at startup
def ensure_buckets():
    try:
        for bucket in ["cert-temp", "certificates"]:
            if not minio_client.bucket_exists(bucket):
                minio_client.make_bucket(bucket)
        print("✅ MinIO buckets ready.")
    except Exception as e:
        print(f"⚠️  WARNING: MinIO not available ({e}). File upload features will be disabled until MinIO is started.")
