from datetime import timedelta
from ..core.minio_client import minio_client

def get_presigned_url(bucket: str, object_name: str, expires: int = 3600) -> str:
    """Generate a temporary URL for accessing a MinIO object."""
    return minio_client.presigned_get_object(bucket, object_name, expires=timedelta(seconds=expires))