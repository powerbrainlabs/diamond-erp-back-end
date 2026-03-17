from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime
import uuid

from pydantic import BaseModel
from ..core.minio_client import CopySource

from ..db.database import get_db
from ..core.dependencies import require_staff
from ..core.minio_client import minio_client
from ..utils.minio_helpers import get_presigned_url
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/api/photos", tags=["Job Photos"])


def _promote_from_temp(temp_file_id: str, dest_file_id: str) -> str:
    src_bucket = "cert-temp"
    dest_bucket = "job-photos"
    try:
        try:
            minio_client.stat_object(src_bucket, temp_file_id)
        except Exception:
            raise HTTPException(
                status_code=404,
                detail=f"Temp file not found: {temp_file_id}. Please re-upload.",
            )
        source = CopySource(src_bucket, temp_file_id)
        minio_client.copy_object(dest_bucket, dest_file_id, source)
        minio_client.remove_object(src_bucket, temp_file_id)
        return f"{dest_bucket}/{dest_file_id}"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File promotion failed: {str(e)}")


def _attach_signed_url(doc: dict) -> dict:
    doc["photo_signed_url"] = get_presigned_url("job-photos", doc["file_id"])
    return doc


# ── Request models ────────────────────────────────────────────────────────────

class PhotoCreate(BaseModel):
    """Legacy: create a published photo in one step (requires job_id)."""
    job_id: str
    name: str
    description: Optional[str] = None
    temp_file_id: str


class PhotoCreateDraft(BaseModel):
    """Create a draft photo without a job assignment."""
    temp_file_id: str
    name: Optional[str] = None


class PhotoUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class PhotoUpdateFile(BaseModel):
    """Replace the stored image file (e.g. after BG removal or re-edit)."""
    temp_file_id: str


class PhotoPublish(BaseModel):
    """Promote a draft photo to published by assigning it to a job."""
    job_id: str
    name: str
    description: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_doc(
    photo_uuid: str,
    dest_file_id: str,
    photo_url: str,
    name: str,
    description: str,
    current_user: dict,
    status: str,
    job_id: Optional[str] = None,
    job_number: Optional[str] = None,
) -> dict:
    now = datetime.utcnow()
    return {
        "uuid": photo_uuid,
        "status": status,            # "draft" | "published"
        "job_id": job_id or "",
        "job_number": job_number or "",
        "name": name,
        "description": description,
        "file_id": dest_file_id,
        "photo_url": photo_url,
        "used_in_certificates": [],  # list of certificate UUIDs
        "created_at": now,
        "updated_at": now,
        "created_by": {
            "user_id": current_user.get("uuid"),
            "name": current_user.get("name"),
            "email": current_user.get("email"),
        },
        "is_deleted": False,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/draft", status_code=201)
async def create_draft_photo(
    payload: PhotoCreateDraft,
    current_user: dict = Depends(require_staff),
):
    """Create a draft photo without a job assignment."""
    db = await get_db()

    photo_uuid = str(uuid.uuid4())
    name = (payload.name or "draft").strip() or "draft"
    safe_name = name.replace(" ", "_").replace("/", "-")[:60]
    dest_file_id = f"{photo_uuid}_{safe_name}"

    photo_url = _promote_from_temp(payload.temp_file_id, dest_file_id)

    doc = _make_doc(
        photo_uuid=photo_uuid,
        dest_file_id=dest_file_id,
        photo_url=photo_url,
        name=name,
        description="",
        current_user=current_user,
        status="draft",
    )
    await db.job_photos.insert_one(doc)

    result = serialize_mongo_doc(doc)
    return _attach_signed_url(result)


@router.post("", status_code=201)
async def create_photo(
    payload: PhotoCreate,
    current_user: dict = Depends(require_staff),
):
    """Legacy: create a published photo in one step."""
    db = await get_db()

    job = await db.jobs.find_one({"uuid": payload.job_id, "is_deleted": False})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    photo_uuid = str(uuid.uuid4())
    safe_name = payload.name.replace(" ", "_").replace("/", "-")[:60]
    dest_file_id = f"{photo_uuid}_{safe_name}"

    photo_url = _promote_from_temp(payload.temp_file_id, dest_file_id)

    doc = _make_doc(
        photo_uuid=photo_uuid,
        dest_file_id=dest_file_id,
        photo_url=photo_url,
        name=payload.name,
        description=payload.description or "",
        current_user=current_user,
        status="published",
        job_id=payload.job_id,
        job_number=job.get("job_number", ""),
    )
    await db.job_photos.insert_one(doc)

    result = serialize_mongo_doc(doc)
    return _attach_signed_url(result)


@router.get("")
async def list_photos(
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),  # "draft" | "published" | None (all)
    current_user: dict = Depends(require_staff),
):
    db = await get_db()

    query = {"is_deleted": False}
    if job_id:
        query["job_id"] = job_id
    if status:
        query["status"] = status

    cursor = db.job_photos.find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=500)

    results = [_attach_signed_url(serialize_mongo_doc(doc)) for doc in docs]
    return {"data": results, "total": len(results)}


@router.get("/{photo_uuid}")
async def get_photo(
    photo_uuid: str,
    current_user: dict = Depends(require_staff),
):
    db = await get_db()
    doc = await db.job_photos.find_one({"uuid": photo_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")
    result = serialize_mongo_doc(doc)
    return _attach_signed_url(result)


@router.patch("/{photo_uuid}/file")
async def update_photo_file(
    photo_uuid: str,
    payload: PhotoUpdateFile,
    current_user: dict = Depends(require_staff),
):
    """Replace a photo's stored image (after re-edit or BG removal)."""
    db = await get_db()
    doc = await db.job_photos.find_one({"uuid": photo_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Remove old file from MinIO
    try:
        minio_client.remove_object("job-photos", doc["file_id"])
    except Exception:
        pass

    # Promote new temp file
    new_dest_file_id = f"{photo_uuid}_{doc.get('name', 'photo').replace(' ', '_')[:60]}_v{int(datetime.utcnow().timestamp())}"
    _promote_from_temp(payload.temp_file_id, new_dest_file_id)

    await db.job_photos.update_one(
        {"uuid": photo_uuid},
        {"$set": {
            "file_id": new_dest_file_id,
            "photo_url": f"job-photos/{new_dest_file_id}",
            "updated_at": datetime.utcnow(),
        }},
    )

    updated = await db.job_photos.find_one({"uuid": photo_uuid})
    result = serialize_mongo_doc(updated)
    return _attach_signed_url(result)


@router.patch("/{photo_uuid}/publish")
async def publish_photo(
    photo_uuid: str,
    payload: PhotoPublish,
    current_user: dict = Depends(require_staff),
):
    """Promote a draft photo to published by assigning a job."""
    db = await get_db()
    doc = await db.job_photos.find_one({"uuid": photo_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")
    if doc.get("status") == "published":
        raise HTTPException(status_code=400, detail="Photo is already published")

    job = await db.jobs.find_one({"uuid": payload.job_id, "is_deleted": False})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.job_photos.update_one(
        {"uuid": photo_uuid},
        {"$set": {
            "status": "published",
            "job_id": payload.job_id,
            "job_number": job.get("job_number", ""),
            "name": payload.name,
            "description": payload.description or doc.get("description", ""),
            "updated_at": datetime.utcnow(),
        }},
    )

    updated = await db.job_photos.find_one({"uuid": photo_uuid})
    result = serialize_mongo_doc(updated)
    return _attach_signed_url(result)


@router.patch("/{photo_uuid}")
async def update_photo(
    photo_uuid: str,
    payload: PhotoUpdate,
    current_user: dict = Depends(require_staff),
):
    db = await get_db()
    doc = await db.job_photos.find_one({"uuid": photo_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")

    updates: dict = {"updated_at": datetime.utcnow()}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.description is not None:
        updates["description"] = payload.description

    await db.job_photos.update_one({"uuid": photo_uuid}, {"$set": updates})

    updated = await db.job_photos.find_one({"uuid": photo_uuid})
    result = serialize_mongo_doc(updated)
    return _attach_signed_url(result)


@router.delete("/{photo_uuid}", status_code=204)
async def delete_photo(
    photo_uuid: str,
    current_user: dict = Depends(require_staff),
):
    db = await get_db()
    doc = await db.job_photos.find_one({"uuid": photo_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Photo not found")

    try:
        minio_client.remove_object("job-photos", doc["file_id"])
    except Exception:
        pass

    await db.job_photos.update_one(
        {"uuid": photo_uuid},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    return None
