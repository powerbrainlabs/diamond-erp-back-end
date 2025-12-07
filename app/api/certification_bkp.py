from app.utils.minio_helpers import get_presigned_url
from app.utils.serializers import serialize_mongo_doc
from fastapi import APIRouter, Depends, HTTPException, Form, Query
from datetime import datetime
import uuid
from ..core.dependencies import require_staff
from ..db.database import get_db
from ..core.minio_client import minio_client
from minio.commonconfig import CopySource

# from ..utils.serializers import dump_certification

router = APIRouter(prefix="/api/certifications", tags=["Certifications"])

def promote_file_from_temp(file_id: str) -> str:
    """Move file from cert-temp → certificates bucket and return permanent URL."""
    src_bucket = "cert-temp"
    dest_bucket = "certificates"
    try:
        # ✅ Correct usage with CopySource
        source = CopySource(src_bucket, file_id)

        # Copy object server-side
        minio_client.copy_object(
            dest_bucket,
            file_id,
            source
        )

        # Remove original from temp bucket
        minio_client.remove_object(src_bucket, file_id)

        return f"{dest_bucket}/{file_id}"
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"File move failed: {str(e)}")

@router.post("/diamonds", status_code=201)
async def create_diamond_cert(
    client_id: str = Form(...),
    category: str = Form(...),
    colour: str = Form(...),
    cut: str = Form(...),
    clarity: str = Form(...),
    photo_file_id: str = Form(None),
    logo_file_id: str = Form(None),
    # current_user: dict = Depends(require_staff)
):
    db = await get_db()

    client = await db.clients.find_one({"uuid": client_id, "is_deleted": False})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Move files from temp → permanent
    photo_url = promote_file_from_temp(photo_file_id) if photo_file_id else None
    logo_url = promote_file_from_temp(logo_file_id) if logo_file_id else None

    now = datetime.utcnow()
    doc = {
        "uuid": str(uuid.uuid4()),
        "type": "diamond",
        "client_id": client_id,
        "category": category,
        "colour": colour,
        "cut": cut,
        "clarity": clarity,
        "photo_url": photo_url,
        "brand_logo_url": logo_url,
        "is_deleted": False,
        "created_by": {
            # "user_id": current_user["id"],
            # "name": current_user["name"],
            # "email": current_user["email"]
        },
        "created_at": now,
        "updated_at": now
    }

    try:
        await db.certifications.insert_one(doc)
    except Exception as e:
        # If DB insert fails, cleanup promoted files
        if photo_url:
            minio_client.remove_object("certificates", photo_file_id)
        if logo_url:
            minio_client.remove_object("certificates", logo_file_id)
        raise HTTPException(status_code=500, detail=f"Certification creation failed: {str(e)}")

    return {"detail": "Certification created"}


@router.get("", summary="List all certifications")
async def list_certifications(
    # current_user: dict = Depends(require_staff),
    cert_type: str = Query(None, description="Filter by type, e.g., 'diamond'"),
    page: int = 1,
    limit: int = 20,
):
    db = await get_db()
    query = {"is_deleted": False}
    if cert_type:
        query["type"] = cert_type

    skip = (page - 1) * limit
    cursor = db.certifications.find(query).skip(skip).limit(limit)
    docs = [serialize_mongo_doc(d) async for d in cursor]

    # Attach presigned URLs
    for d in docs:
        if d.get("photo_url"):
            # photo_url is stored like "certificates/<file_id>"
            bucket, key = d["photo_url"].split("/", 1)
            d["photo_presigned"] = get_presigned_url(bucket, key)
        if d.get("brand_logo_url"):
            bucket, key = d["brand_logo_url"].split("/", 1)
            d["brand_logo_presigned"] = get_presigned_url(bucket, key)

    total = await db.certifications.count_documents(query)
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": docs,
    }


@router.get("/{cert_id}")
async def get_certificate(cert_id: str,
                        #    current_user: dict = Depends(require_staff)
                           ):
    db = await get_db()
    doc = await db.certifications.find_one({"uuid": cert_id, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Certification not found")

    d = serialize_mongo_doc(doc)
    if d.get("photo_url"):
        bucket, key = d["photo_url"].split("/", 1)
        d["photo_presigned"] = get_presigned_url(bucket, key)
    if d.get("brand_logo_url"):
        bucket, key = d["brand_logo_url"].split("/", 1)
        d["brand_logo_presigned"] = get_presigned_url(bucket, key)

    return d