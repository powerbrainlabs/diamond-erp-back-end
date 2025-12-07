import io
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from datetime import datetime
import uuid

from app.utils.minio_helpers import get_presigned_url
from ..core.minio_client import minio_client

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
                content_type=file.content_type
            )

            uploaded.append({
                "file_id": file_id,
                "bucket": "cert-temp",
                "filename": file.filename,
                "content_type": file.content_type,
                "uploaded_at": datetime.utcnow().isoformat()
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed for {file.filename}: {str(e)}")

    return {"uploaded": uploaded}



# /api/files/presigned/<bucket>/<file_id>
@router.get("/presigned/{bucket}/{file_id}")
async def get_presigned_file(bucket: str, file_id: str):
    try:
        url = get_presigned_url(bucket, file_id)  # <-- you already have this helper
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
