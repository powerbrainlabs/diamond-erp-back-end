from datetime import timedelta
from minio import Minio
from ..core.minio_client import minio_client
from ..core.config import settings

def get_presigned_url(bucket: str, object_name: str, expires: int = 3600) -> str:
    """
    Generate a URL for accessing a MinIO object through backend proxy endpoint.
    Returns absolute HTTPS URL so it works from any frontend (local, Vercel, etc).
    """
    # Use backend URL from config (configurable via BACKEND_URL env var)
    # Example: https://backend-sta.gac.powerbrainlabs.com
    backend_url = settings.BACKEND_URL

    # Return absolute proxy URL so it works from any domain
    # Example: https://backend-sta.gac.powerbrainlabs.com/api/files/proxy/certificates/file_id
    return f"{backend_url}/api/files/proxy/{bucket}/{object_name}"