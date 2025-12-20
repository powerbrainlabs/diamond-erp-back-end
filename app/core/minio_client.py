from minio import Minio
import asyncio
from ..core.config import settings

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_USE_TLS,
)

# Ensure buckets exist at startup
async def ensure_buckets():
    loop = asyncio.get_event_loop()
    for bucket in ["cert-temp", "certificates"]:
        try:
            exists = await loop.run_in_executor(None, minio_client.bucket_exists, bucket)
            if not exists:
                await loop.run_in_executor(None, minio_client.make_bucket, bucket)
                print(f"Created MinIO bucket: {bucket}")
        except Exception as e:
            print(f"Warning: Could not ensure bucket {bucket}: {e}")
