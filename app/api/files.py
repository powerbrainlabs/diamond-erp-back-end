import io
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from datetime import datetime
import uuid
import httpx
import logging
from PIL import Image

from app.utils.minio_helpers import get_presigned_url
from ..core.minio_client import minio_client
from ..core.config import settings

logger = logging.getLogger(__name__)


def compress_image(image_bytes: bytes, filename: str, max_width: int = 1200, quality: int = 75) -> tuple[bytes, str]:
    """
    Compress image to reduce file size while maintaining reasonable quality.

    Args:
        image_bytes: Raw image bytes
        filename: Original filename to preserve extension
        max_width: Maximum width in pixels (aspect ratio preserved)
        quality: JPEG/WebP quality (1-100, default 75 for good balance)

    Returns:
        Tuple of (compressed_bytes, content_type)
    """
    try:
        # Open image from bytes
        img = Image.open(io.BytesIO(image_bytes))

        # Convert RGBA to RGB if needed (for JPEG compatibility)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if width exceeds max_width (preserve aspect ratio)
        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # Save compressed image
        output = io.BytesIO()

        # Determine output format
        filename_lower = filename.lower()
        if filename_lower.endswith('.png'):
            img.save(output, format='PNG', optimize=True)
            content_type = 'image/png'
        elif filename_lower.endswith('.webp'):
            img.save(output, format='WEBP', quality=quality)
            content_type = 'image/webp'
        else:  # Default to JPEG for jpg, jpeg, and unknown formats
            img.save(output, format='JPEG', quality=quality, optimize=True)
            content_type = 'image/jpeg'

        compressed_bytes = output.getvalue()
        original_size = len(image_bytes)
        compressed_size = len(compressed_bytes)
        ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

        logger.info(f"📦 Image compressed: {filename} | {original_size:,} → {compressed_size:,} bytes ({ratio:.1f}% reduction)")

        return compressed_bytes, content_type

    except Exception as e:
        logger.warning(f"⚠️ Image compression failed for {filename}: {str(e)}, uploading original")
        # Return original bytes if compression fails
        return image_bytes, "application/octet-stream"


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
    Automatically compresses images to optimize storage and loading times.
    Returns an array of uploaded file details with their temp file IDs.
    """
    uploaded = []

    for file in files:
        try:
            file_id = f"{uuid.uuid4()}_{file.filename}"

            # Read bytes into memory
            file_bytes = await file.read()
            content_type = file.content_type or "application/octet-stream"

            # Compress images (JPEG, PNG, WebP, etc.)
            if content_type.startswith('image/'):
                file_bytes, content_type = compress_image(file_bytes, file.filename)

            file_stream = io.BytesIO(file_bytes)

            minio_client.put_object(
                bucket_name="cert-temp",
                object_name=file_id,
                data=file_stream,
                length=len(file_bytes),
                content_type=content_type
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
                "content_type": content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            })

            logger.info(f"✅ Successfully uploaded file: {file_id} to cert-temp bucket")

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


@router.get("/download/{bucket}/{file_id:path}")
async def download_file(bucket: str, file_id: str):
    """
    Stream a file directly from MinIO. Used by frontend for PDF generation
    to avoid CORS issues with presigned URLs.
    """
    try:
        response = minio_client.get_object(bucket, file_id)
        stat = minio_client.stat_object(bucket, file_id)
        content_type = stat.content_type or "application/octet-stream"

        return StreamingResponse(
            response,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")


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
    Returns the processed image with transparent background (optimized/compressed).
    """
    try:
        # Read the uploaded file
        file_bytes = await image.read()

        # Call the background removal API
        filename = image.filename or "image.png"
        processed_image = await _remove_bg_api(file_bytes, filename)

        # Compress the output image to reduce file size
        # For PNG with transparency, we still optimize it
        try:
            img = Image.open(io.BytesIO(processed_image))
            output = io.BytesIO()
            # Save with optimization for PNG (maintains transparency)
            img.save(output, format='PNG', optimize=True)
            processed_image = output.getvalue()
            logger.info(f"📦 Background-removed image optimized: {len(file_bytes):,} → {len(processed_image):,} bytes")
        except Exception as compress_error:
            logger.warning(f"⚠️ PNG optimization failed: {str(compress_error)}, returning original")

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
