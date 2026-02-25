import io
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import uuid
import httpx
import logging

from app.utils.minio_helpers import get_presigned_url
from ..core.minio_client import minio_client
from ..core.config import settings

logger = logging.getLogger(__name__)

# Default values for background removal API
REMBG_API_URL = "https://begon.webeazzy.com/api/process-image"
REMBG_API_KEY = "sk-jBqRqnHAD5JECKpUP8NklxUTmns6d1M57ZoXgI0DW3M"


async def _remove_bg_api(image_data: bytes, filename: str) -> bytes:
    """
    Call Webeazzy RemBG API to remove background.

    API Endpoint: https://begon.webeazzy.com/api/process-image
    Auth: X-API-Key header
    """
    api_key = settings.REMBG_API_KEY or REMBG_API_KEY

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                settings.REMBG_API_URL or REMBG_API_URL,
                headers={
                    "X-API-Key": api_key
                },
                files={
                    "file": (filename, image_data)
                }
            )

        if response.status_code == 200:
            logger.info(f"Background removed via RemBG API: {filename}")
            return response.content
        elif response.status_code == 401 or response.status_code == 403:
            raise RuntimeError(
                f"RemBG API: Authentication failed (status {response.status_code})"
            )
        elif response.status_code == 429:
            raise RuntimeError(
                "RemBG API: Rate limit exceeded. Please try again later."
            )
        else:
            detail = response.text[:200] if response.text else "Unknown error"
            raise RuntimeError(
                f"RemBG API failed: {response.status_code} - {detail}"
            )

    except httpx.TimeoutException:
        raise RuntimeError("RemBG API: Request timed out (120 seconds)")
    except httpx.ConnectError:
        raise RuntimeError("RemBG API: Could not connect to server")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"RemBG API error: {str(e)}")

router = APIRouter(prefix="/api/files", tags=["Files"])

@router.post("/upload-temp")
async def upload_temp_file(files: List[UploadFile] = File(...)):
    """
    Upload one or multiple files to temporary MinIO bucket (cert-temp).
    Returns an array of uploaded file details with their temp file IDs.
    """
    uploaded = []

    for file in files:
        try:
            file_id = f"{uuid.uuid4()}_{file.filename}"

            # Read bytes into memory (MinIO requires length)
            file_bytes = await file.read()
            file_stream = io.BytesIO(file_bytes)

            minio_client.put_object(
                bucket_name="cert-temp",
                object_name=file_id,
                data=file_stream,
                length=len(file_bytes),
                content_type=file.content_type or "application/octet-stream"
            )

            # Verify the file was uploaded successfully
            try:
                minio_client.stat_object("cert-temp", file_id)
            except Exception as verify_error:
                raise HTTPException(
                    status_code=500,
                    detail=f"File upload verification failed for {file.filename}: {str(verify_error)}"
                )

            uploaded.append({
                "file_id": file_id,
                "bucket": "cert-temp",
                "filename": file.filename,
                "content_type": file.content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            })

            print(f"✅ Successfully uploaded file: {file_id} to cert-temp bucket")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed for {file.filename}: {str(e)}")

    return {"uploaded": uploaded}



# /api/files/presigned/<bucket>/<file_id>
@router.get("/proxy/{bucket}/{file_id:path}")
async def proxy_file(bucket: str, file_id: str):
    """
    Proxy endpoint for serving files from MinIO.
    Used by the frontend to display images without exposing direct MinIO URLs.
    """
    try:
        response = minio_client.get_object(bucket, file_id)
        file_data = response.read()
        content_type = response.headers.get("content-type", "application/octet-stream")

        # Build headers, including cache-related headers from MinIO
        headers = {
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
        }

        # Pass through ETag and Last-Modified if available
        if "etag" in response.headers:
            headers["ETag"] = response.headers["etag"]
        if "last-modified" in response.headers:
            headers["Last-Modified"] = response.headers["last-modified"]

        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=content_type,
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


@router.get("/presigned/{bucket}/{file_id}")
async def get_presigned_file(bucket: str, file_id: str):
    try:
        url = get_presigned_url(bucket, file_id)  # <-- you already have this helper
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/verify-temp/{file_id}")
async def verify_temp_file(file_id: str):
    """
    Verify if a file exists in the cert-temp bucket.
    Useful for debugging upload issues.
    """
    try:
        stat = minio_client.stat_object("cert-temp", file_id)
        return {
            "exists": True,
            "file_id": file_id,
            "bucket": "cert-temp",
            "size": stat.size,
            "last_modified": stat.last_modified.isoformat() if stat.last_modified else None,
            "content_type": stat.content_type
        }
    except Exception as e:
        return {
            "exists": False,
            "file_id": file_id,
            "bucket": "cert-temp",
            "error": str(e)
        }


@router.post("/remove-background")
async def remove_background(image: UploadFile = File(...)):
    """
    Remove background from an image using the begon.webeazzy.com API.
    Returns the processed image with transparent background.
    """
    try:
        # Read the uploaded file
        file_bytes = await image.read()
        
        # Call the background removal API
        filename = image.filename or "image.png"
        processed_image = await _remove_bg_api(file_bytes, filename)
        
        # Return the processed image
        return StreamingResponse(
            io.BytesIO(processed_image),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=nobg_{filename}"
            }
        )
            
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {str(e)}")
