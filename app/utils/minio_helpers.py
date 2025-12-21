from datetime import timedelta
from minio import Minio
from ..core.minio_client import minio_client
from ..core.config import settings
import os

def get_presigned_url(bucket: str, object_name: str, expires: int = 3600) -> str:
    """
    Generate a URL for accessing a MinIO object.
    Uses backend proxy endpoint to avoid signature validation issues with nginx.
    """
    # Use backend proxy endpoint instead of presigned URL
    # This avoids signature validation issues when proxying through nginx
    public_host = os.getenv("MINIO_PUBLIC_HOST", "staging.gac.powerbrainlabs.com")
    
    # Return proxy URL: /api/files/proxy/bucket/file_id
    # Frontend will use relative path, so it works from any client
    # Since frontend calls backend-sta.gac.powerbrainlabs.com, this relative path works
    return f"/api/files/proxy/{bucket}/{object_name}"