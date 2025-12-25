from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Query
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime
import uuid

from pydantic import BaseModel
from ..core.minio_client import minio_client
from minio.commonconfig import CopySource
from ..db.database import get_db
from ..utils.minio_helpers import get_presigned_url
from ..utils.serializers import serialize_mongo_doc
from ..utils.qr_generator import save_qr_code_to_minio
from ..utils.certificate_number import next_certificate_number
from ..core.config import settings
from ..core.dependencies import require_staff

router = APIRouter(prefix="/api/certifications", tags=["Certifications"])


def promote_file_from_temp(file_id: str) -> str:
    """
    Move file from cert-temp → certificates bucket and return permanent URL.
    Returns None if file doesn't exist (graceful handling).
    """
    src_bucket = "cert-temp"
    dest_bucket = "certificates"
    try:
        # Check if file exists before trying to copy
        try:
            minio_client.stat_object(src_bucket, file_id)
        except Exception as stat_err:
            # File doesn't exist - return None instead of raising error
            print(f"Warning: File {file_id} not found in {src_bucket}: {stat_err}")
            return None
        
        source = CopySource(src_bucket, file_id)
        minio_client.copy_object(dest_bucket, file_id, source)
        minio_client.remove_object(src_bucket, file_id)
        return f"{dest_bucket}/{file_id}"
    except Exception as e:
        # If copy fails, don't raise error - just return None
        print(f"Warning: Failed to promote file {file_id}: {str(e)}")
        return None


# 🧱 Single Create (still valid for diamond)
class CertificationCreate(BaseModel):
    type: str
    client_id: str
    fields: Dict[str, Any]
    photo_file_id: Optional[str] = None
    logo_file_id: Optional[str] = None
    photo_edit_completed: Optional[bool] = False


@router.post("", status_code=201)
async def create_certification(
    payload: CertificationCreate,
    #   current_user: dict = Depends(require_staff)
):
    db = await get_db()

    client = await db.clients.find_one({"uuid": payload.client_id, "is_deleted": False})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Promote files only if file_id is provided and file exists
    photo_url = None
    if payload.photo_file_id:
        photo_url = promote_file_from_temp(payload.photo_file_id)
        if not photo_url:
            # File doesn't exist - this is okay, certificate can be created without photo
            print(f"Warning: Photo file {payload.photo_file_id} not found, creating certificate without photo")
    
    logo_url = None
    if payload.logo_file_id:
        logo_url = promote_file_from_temp(payload.logo_file_id)
        if not logo_url:
            # File doesn't exist - this is okay, certificate can be created without logo
            print(f"Warning: Logo file {payload.logo_file_id} not found, creating certificate without logo")

    # Generate certificate UUID
    cert_uuid = str(uuid.uuid4())
    
    # Generate certificate number
    cert_number = await next_certificate_number()
    
    # Generate QR code URL - use frontend URL from config or default
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
    qr_code_url = f"{frontend_url}/certificate/{cert_uuid}"
    
    # Generate and save QR code to MinIO
    qr_code_url_path = save_qr_code_to_minio(cert_uuid, qr_code_url, size=200)
    
    # Add certificate number to fields if not already present
    fields_with_cert_no = payload.fields.copy() if payload.fields else {}
    if "certificate_no" not in fields_with_cert_no and "certificate_number" not in fields_with_cert_no:
        fields_with_cert_no["certificate_no"] = cert_number
        fields_with_cert_no["certificate_number"] = cert_number
    
    now = datetime.utcnow()
    doc = {
        "uuid": cert_uuid,
        "type": payload.type,
        "client_id": payload.client_id,
        "fields": fields_with_cert_no,
        "photo_url": photo_url,
        "brand_logo_url": logo_url,
        "qr_code_url": qr_code_url_path,  # Store QR code path in MinIO
        "photo_edit_completed": payload.photo_edit_completed or False,
        "is_deleted": False,
        "is_rejected": False,
        "created_at": now,
        "updated_at": now,
    }

    await db.certifications.insert_one(doc)
    return {"detail": "Certification created", "uuid": doc["uuid"]}


# 🧱 Bulk Create
@router.post("/bulk", status_code=201)
async def create_bulk_certifications(payload: List[Dict[str, Any]]):
    db = await get_db()
    now = datetime.utcnow()
    inserted_docs = []
    promoted_files = []

    try:
        for cert in payload:
            # Validate type & client
            client = await db.clients.find_one({"uuid": cert["client_id"], "is_deleted": False})
            if not client:
                raise HTTPException(status_code=404, detail=f"Client {cert['client_id']} not found")

            # Promote images if available
            photo_url = promote_file_from_temp(cert.get("photo_file_id")) if cert.get("photo_file_id") else None
            logo_url = promote_file_from_temp(cert.get("logo_file_id")) if cert.get("logo_file_id") else None
            if photo_url: promoted_files.append(("certificates", photo_url.split("/", 1)[1]))
            if logo_url: promoted_files.append(("certificates", logo_url.split("/", 1)[1]))

            # Generate certificate UUID
            cert_uuid = str(uuid.uuid4())
            
            # Generate certificate number
            cert_number = await next_certificate_number()
            
            # Generate QR code URL
            frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
            qr_code_url = f"{frontend_url}/certificate/{cert_uuid}"
            
            # Generate and save QR code to MinIO
            qr_code_url_path = save_qr_code_to_minio(cert_uuid, qr_code_url, size=200)
            
            # Add certificate number to fields if not already present
            fields_with_cert_no = cert.get("fields", {}).copy()
            if "certificate_no" not in fields_with_cert_no and "certificate_number" not in fields_with_cert_no:
                fields_with_cert_no["certificate_no"] = cert_number
                fields_with_cert_no["certificate_number"] = cert_number
            
            inserted_docs.append({
                "uuid": cert_uuid,
                "type": cert["type"],
                "client_id": cert["client_id"],
                "fields": fields_with_cert_no,
                "photo_url": photo_url,
                "brand_logo_url": logo_url,
                "qr_code_url": qr_code_url_path,
                "is_deleted": False,
                "is_rejected": False,
                "created_at": now,
                "updated_at": now
            })

        await db.certifications.insert_many(inserted_docs)
        return {"detail": f"{len(inserted_docs)} certifications created"}

    except Exception as e:
        # Rollback promoted files on error
        for bucket, key in promoted_files:
            try:
                minio_client.remove_object(bucket, key)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Bulk certification creation failed: {str(e)}")



ALLOWED_SORTS = {
    "created_at": "created_at",
    "type": "type",
}

def attach_presigned_urls(doc):
    """
    Inject presigned URLs for photo, logo, and QR code if present.
    """
    # Photo
    if doc.get("photo_url"):
        try:
            bucket, file_id = doc["photo_url"].split("/", 1)
            doc["photo_signed_url"] = get_presigned_url(bucket, file_id)
        except:
            doc["photo_signed_url"] = None

    # Logo
    if doc.get("brand_logo_url"):
        try:
            bucket, file_id = doc["brand_logo_url"].split("/", 1)
            doc["brand_logo_signed_url"] = get_presigned_url(bucket, file_id)
        except:
            doc["brand_logo_signed_url"] = None

    # QR Code
    if doc.get("qr_code_url"):
        try:
            bucket, file_id = doc["qr_code_url"].split("/", 1)
            doc["qr_code_signed_url"] = get_presigned_url(bucket, file_id)
        except:
            doc["qr_code_signed_url"] = None

    return doc


@router.get("")
async def list_certifications(
    search: Optional[str] = None,
    type: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    """
    Fetch paginated certifications with filters,
    now with presigned URLs included.
    """
    db = await get_db()
    filt = {"is_deleted": False}

    # Filter by certificate type
    if type:
        filt["type"] = type

    # Search on type & fields
    if search:
        filt["$or"] = [
            {"fields": {"$regex": search, "$options": "i"}},
            {"type": {"$regex": search, "$options": "i"}},
        ]

    sort_field = ALLOWED_SORTS.get(sort_by, "created_at")
    sort_dir = -1 if order == "desc" else 1

    total = await db.certifications.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)

    cursor = (
        db.certifications.find(filt)
        .sort([(sort_field, sort_dir)])
        .skip(skip)
        .limit(limit)
    )

    items = []
    async for doc in cursor:
        # Join with clients
        client = await db.clients.find_one({"uuid": doc["client_id"], "is_deleted": False})
        doc["client"] = {"id": client["uuid"], "name": client["name"]} if client else None

        serialized = serialize_mongo_doc(doc)

        # 🔥 Add presigned URLs
        serialized = attach_presigned_urls(serialized)

        items.append(serialized)

    total_pages = (total + limit - 1) // limit

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "data": items,
    }


@router.get("/{uuid}")
async def get_certification(uuid: str):
    """
    Get a single certificate by UUID (public endpoint for QR code viewing)
    """
    db = await get_db()
    doc = await db.certifications.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Certification not found")
    
    serialized = serialize_mongo_doc(doc)
    
    # Add presigned URLs
    serialized = attach_presigned_urls(serialized)
    
    return serialized


# ✅ Stats: Overview
@router.get("/stats")
async def certificate_stats(current_user: dict = Depends(require_staff)):
    """
    Get certificate statistics
    """
    db = await get_db()
    
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "by_type": [{"$group": {"_id": "$type", "count": {"$sum": 1}}}],
            "created_today": [
                {"$match": {"created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}}},
                {"$count": "count"}
            ],
            "pending_photo_edit": [
                {"$match": {"photo_edit_completed": False, "photo_url": {"$ne": None}}},
                {"$count": "count"}
            ],
        }}
    ]
    res = await db.certifications.aggregate(pipeline).to_list(1)
    agg = res[0] if res else {}
    
    def _get(lst): return lst[0]["count"] if lst else 0
    
    return {
        "total_certificates": _get(agg.get("total", [])),
        "by_type": {d["_id"]: d["count"] for d in agg.get("by_type", [])},
        "created_today": _get(agg.get("created_today", [])),
        "pending_photo_edit": _get(agg.get("pending_photo_edit", [])),
    }


# ✅ Stats: Daily Certificate Count
@router.get("/stats/daily")
async def certificate_stats_daily(current_user: dict = Depends(require_staff)):
    """
    Get daily certificate creation count
    """
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$limit": 30}  # Last 30 days
    ]
    res = await db.certifications.aggregate(pipeline).to_list(None)
    return {"daily": res}


@router.patch("/{uuid}/reject")
async def reject_certificate(uuid: str, current_user: dict = Depends(require_staff)):
    """
    Mark a certificate as rejected.
    When rejected, the certificate will show a rejection message instead of details.
    """
    db = await get_db()

    # Find the certificate
    cert = await db.certifications.find_one({"uuid": uuid, "is_deleted": False})
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # Check if already rejected
    if cert.get("is_rejected"):
        raise HTTPException(status_code=400, detail="Certificate is already rejected")

    # Update the certificate to mark as rejected
    result = await db.certifications.update_one(
        {"uuid": uuid},
        {
            "$set": {
                "is_rejected": True,
                "rejected_at": datetime.utcnow(),
                "rejected_by": current_user.get("uuid"),
                "updated_at": datetime.utcnow()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Failed to reject certificate")

    return {"detail": "Certificate rejected successfully", "uuid": uuid}
