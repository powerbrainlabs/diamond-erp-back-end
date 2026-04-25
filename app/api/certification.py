from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Depends, Query
from fastapi.responses import Response
from typing import List, Dict, Any, Literal, Optional
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

from pydantic import BaseModel
from ..core.minio_client import minio_client
from ..core.minio_client import CopySource
from ..db.database import get_db
from ..core.dependencies import require_staff
from ..utils.minio_helpers import get_presigned_url
from ..utils.serializers import serialize_mongo_doc
from ..utils.cert_numbering import next_certificate_number
from ..utils.template_renderer import render_description_template

router = APIRouter(prefix="/api/certifications", tags=["Certifications"])


def promote_file_from_temp(file_id: str) -> str:
    # Handle empty or None file_id
    if not file_id or file_id.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="File ID is empty or invalid"
        )

    src_bucket = "cert-temp"
    dest_bucket = "certificates"
    try:
        # Check if file already exists in permanent bucket (already promoted)
        try:
            minio_client.stat_object(dest_bucket, file_id)
            return f"{dest_bucket}/{file_id}"
        except Exception:
            pass

        # Check if file exists in temp bucket
        try:
            minio_client.stat_object(src_bucket, file_id)
        except Exception as stat_error:
            raise HTTPException(
                status_code=404,
                detail=f"File not found in temporary storage: {file_id}. "
                       f"Please re-upload the file. Error: {str(stat_error)}"
            )

        # Copy file from temp to permanent bucket
        source = CopySource(src_bucket, file_id)
        minio_client.copy_object(dest_bucket, file_id, source)

        # Remove from temp bucket after successful copy
        minio_client.remove_object(src_bucket, file_id)

        return f"{dest_bucket}/{file_id}"
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File move failed: {str(e)}")


# 🧱 Single Create
class CertificationCreate(BaseModel):
    type: str
    client_id: str
    job_id: Optional[str] = None
    category_id: Optional[str] = None  # uuid of category_schema (optional for backward compat)
    fields: Dict[str, Any]
    photo_file_id: Optional[str] = None
    logo_file_id: Optional[str] = None
    rear_logo_file_id: Optional[str] = None
    gallery_photo_uuid: Optional[str] = None  # uuid of a job_photos document


@router.post("", status_code=201)
async def create_certification(
    payload: CertificationCreate,
    #   current_user: dict = Depends(require_staff)
):
    db = await get_db()

    print(f"📝 Creating certification with payload: type={payload.type}, client_id={payload.client_id}")
    print(f"📸 File IDs - photo: {payload.photo_file_id}, logo: {payload.logo_file_id}, rear_logo: {payload.rear_logo_file_id}")

    client = await db.clients.find_one({"uuid": payload.client_id, "is_deleted": False})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Validate fields against category schema if provided
    if payload.category_id:
        schema = await db.category_schemas.find_one({
            "uuid": payload.category_id, "is_deleted": False, "is_active": True,
        })
        if not schema:
            raise HTTPException(status_code=400, detail="Invalid category schema")
        for field_def in schema.get("fields", []):
            if field_def.get("is_required") and not payload.fields.get(field_def["field_name"]):
                raise HTTPException(
                    status_code=422,
                    detail=f"Required field '{field_def['label']}' is missing",
                )

    # Promote files with better error handling
    photo_url = None
    logo_url = None
    rear_logo_url = None

    try:
        if payload.gallery_photo_uuid:
            # Use a photo from the job-photos gallery — copy to certificates bucket
            gallery_doc = await db.job_photos.find_one({"uuid": payload.gallery_photo_uuid, "is_deleted": False})
            if not gallery_doc:
                raise HTTPException(status_code=404, detail="Gallery photo not found")
            src_file_id = gallery_doc["file_id"]
            dest_file_id = f"{uuid.uuid4()}_{src_file_id}"
            source = CopySource("job-photos", src_file_id)
            minio_client.copy_object("certificates", dest_file_id, source)
            photo_url = f"certificates/{dest_file_id}"
            print(f"✅ Gallery photo copied to: {photo_url}")
        elif payload.photo_file_id:
            print(f"🔄 Promoting photo file: {payload.photo_file_id}")
            photo_url = promote_file_from_temp(payload.photo_file_id)
            print(f"✅ Photo promoted to: {photo_url}")
    except Exception as e:
        print(f"❌ Photo promotion failed: {str(e)}")
        raise

    def _copy_client_logo(client_url: str) -> str:
        """Copy a logo from client-logos bucket to certificates bucket."""
        src_file_id = client_url.split("/", 1)[-1]
        dest_file_id = f"{uuid.uuid4()}_{src_file_id}"
        source = CopySource("client-logos", src_file_id)
        minio_client.copy_object("certificates", dest_file_id, source)
        return f"certificates/{dest_file_id}"

    try:
        if payload.logo_file_id:
            print(f"🔄 Promoting logo file: {payload.logo_file_id}")
            logo_url = promote_file_from_temp(payload.logo_file_id)
            print(f"✅ Logo promoted to: {logo_url}")
        elif client.get("brand_logo_url"):
            logo_url = _copy_client_logo(client["brand_logo_url"])
            print(f"✅ Client brand logo copied to: {logo_url}")
    except Exception as e:
        print(f"❌ Logo promotion failed: {str(e)}")
        raise

    try:
        if payload.rear_logo_file_id:
            print(f"🔄 Promoting rear logo file: {payload.rear_logo_file_id}")
            rear_logo_url = promote_file_from_temp(payload.rear_logo_file_id)
            print(f"✅ Rear logo promoted to: {rear_logo_url}")
        elif client.get("rear_logo_url"):
            rear_logo_url = _copy_client_logo(client["rear_logo_url"])
            print(f"✅ Client rear logo copied to: {rear_logo_url}")
    except Exception as e:
        print(f"❌ Rear logo promotion failed: {str(e)}")
        raise

    # Generate certificate number (format: G{YYMMDD}{XXXX})
    certificate_number = await next_certificate_number()

    now = datetime.utcnow()
    doc = {
        "uuid": str(uuid.uuid4()),
        "certificate_number": certificate_number,
        "type": payload.type,
        "client_id": payload.client_id,
        "job_id": payload.job_id or "",
        "category_id": payload.category_id,
        "fields": payload.fields,
        "photo_url": photo_url,
        "brand_logo_url": logo_url,
        "rear_brand_logo_url": rear_logo_url,
        "is_deleted": False,
        "is_published": False,
        "published_at": None,
        "is_rejected": False,
        "rejected_at": None,
        "created_at": now,
        "updated_at": now,
    }

    await db.certifications.insert_one(doc)

    # Track which gallery photo was used in this certificate
    if payload.gallery_photo_uuid:
        await db.job_photos.update_one(
            {"uuid": payload.gallery_photo_uuid},
            {"$addToSet": {"used_in_certificates": doc["uuid"]}},
        )

    return {
        "detail": "Certification created",
        "uuid": doc["uuid"],
        "certificate_number": doc["certificate_number"]
    }


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
            rear_logo_url = promote_file_from_temp(cert.get("rear_logo_file_id")) if cert.get("rear_logo_file_id") else None
            if photo_url: promoted_files.append(("certificates", photo_url.split("/", 1)[1]))
            if logo_url: promoted_files.append(("certificates", logo_url.split("/", 1)[1]))
            if rear_logo_url: promoted_files.append(("certificates", rear_logo_url.split("/", 1)[1]))

            # Generate certificate number for each certificate
            certificate_number = await next_certificate_number()

            inserted_docs.append({
                "uuid": str(uuid.uuid4()),
                "certificate_number": certificate_number,
                "type": cert["type"],
                "client_id": cert["client_id"],
                "fields": cert.get("fields", {}),
                "photo_url": photo_url,
                "brand_logo_url": logo_url,
                "rear_brand_logo_url": rear_logo_url,
                "is_deleted": False,
                "is_published": False,
                "published_at": None,
                "is_rejected": False,
                "rejected_at": None,
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
    Inject presigned URLs for photo & logo if present.
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

    # Rear Logo
    if doc.get("rear_brand_logo_url"):
        try:
            bucket, file_id = doc["rear_brand_logo_url"].split("/", 1)
            doc["rear_brand_logo_signed_url"] = get_presigned_url(bucket, file_id)
        except:
            doc["rear_brand_logo_signed_url"] = None

    return doc


class CertificationUpdate(BaseModel):
    client_id: Optional[str] = None
    job_id: Optional[str] = None
    fields: Optional[Dict[str, Any]] = None
    photo_file_id: Optional[str] = None
    logo_file_id: Optional[str] = None
    rear_logo_file_id: Optional[str] = None
    gallery_photo_uuid: Optional[str] = None
    remove_photo: bool = False
    remove_logo: bool = False
    remove_rear_logo: bool = False


@router.put("/{cert_uuid}")
async def update_certification(cert_uuid: str, payload: CertificationUpdate):
    db = await get_db()
    doc = await db.certifications.find_one({"uuid": cert_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Certificate not found")

    updates: Dict[str, Any] = {"updated_at": datetime.utcnow()}

    if payload.client_id is not None:
        client = await db.clients.find_one({"uuid": payload.client_id, "is_deleted": False})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        updates["client_id"] = payload.client_id

    if payload.job_id is not None:
        updates["job_id"] = payload.job_id

    if payload.fields is not None:
        updates["fields"] = payload.fields

    # Photo
    if payload.remove_photo:
        updates["photo_url"] = None
    elif payload.gallery_photo_uuid:
        gallery_doc = await db.job_photos.find_one({"uuid": payload.gallery_photo_uuid, "is_deleted": False})
        if not gallery_doc:
            raise HTTPException(status_code=404, detail="Gallery photo not found")
        src_file_id = gallery_doc["file_id"]
        dest_file_id = f"{uuid.uuid4()}_{src_file_id}"
        source = CopySource("job-photos", src_file_id)
        minio_client.copy_object("certificates", dest_file_id, source)
        updates["photo_url"] = f"certificates/{dest_file_id}"
    elif payload.photo_file_id:
        updates["photo_url"] = promote_file_from_temp(payload.photo_file_id)

    # Logo
    if payload.remove_logo:
        updates["brand_logo_url"] = None
    elif payload.logo_file_id:
        updates["brand_logo_url"] = promote_file_from_temp(payload.logo_file_id)

    # Rear Logo
    if payload.remove_rear_logo:
        updates["rear_brand_logo_url"] = None
    elif payload.rear_logo_file_id:
        updates["rear_brand_logo_url"] = promote_file_from_temp(payload.rear_logo_file_id)

    await db.certifications.update_one({"uuid": cert_uuid}, {"$set": updates})
    return {"detail": "Certificate updated"}


class BulkPublishPayload(BaseModel):
    uuids: List[str]


@router.patch("/{cert_uuid}/reject")
async def reject_certification(cert_uuid: str):
    db = await get_db()
    doc = await db.certifications.find_one({"uuid": cert_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Certificate not found")
    if not doc.get("is_published"):
        raise HTTPException(status_code=400, detail="Only published certificates can be rejected")
    if doc.get("is_rejected"):
        return {"detail": "Certificate already rejected"}

    now = datetime.utcnow()
    await db.certifications.update_one(
        {"uuid": cert_uuid, "is_deleted": False},
        {
            "$set": {
                "is_rejected": True,
                "rejected_at": now,
                "updated_at": now,
            }
        },
    )
    return {"detail": "Certificate rejected successfully"}


@router.patch("/publish")
async def bulk_publish_certifications(payload: BulkPublishPayload):
    """
    Bulk publish certificates by UUID list.
    Sets is_published=True and published_at=now on matching non-rejected certs.
    """
    if not payload.uuids:
        raise HTTPException(status_code=400, detail="No UUIDs provided")
    db = await get_db()
    now = datetime.utcnow()
    rejected_count = await db.certifications.count_documents(
        {"uuid": {"$in": payload.uuids}, "is_deleted": False, "is_rejected": True}
    )
    result = await db.certifications.update_many(
        {"uuid": {"$in": payload.uuids}, "is_deleted": False, "is_rejected": {"$ne": True}},
        {"$set": {"is_published": True, "published_at": now, "updated_at": now}},
    )
    detail = f"{result.modified_count} certificate(s) published"
    if rejected_count:
        detail += f"; {rejected_count} rejected certificate(s) skipped"
    return {
        "detail": detail,
        "published_count": result.modified_count,
        "skipped_rejected_count": rejected_count,
    }


@router.get("")
async def list_certifications(
    search: Optional[str] = None,
    type: Optional[str] = None,
    published: Optional[str] = None,
    rejected_filter: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    """
    Fetch paginated certifications with filters,
    now with presigned URLs included.
    published param: "true" = only published, "false" = only drafts, "all" = everything
    """
    db = await get_db()
    filt = {"is_deleted": False}

    # Filter by published state
    if published == "true":
        filt["is_published"] = True
    elif published == "false":
        filt["is_published"] = {"$ne": True}

    if rejected_filter == "only":
        filt["is_rejected"] = True
    elif rejected_filter == "exclude":
        filt["is_rejected"] = {"$ne": True}

    # Filter by certificate type
    if type:
        filt["type"] = type

    # Search on certificate_number, type, fields, and client name
    if search:
        matching_clients = await db.clients.find(
            {"name": {"$regex": search, "$options": "i"}, "is_deleted": False},
            {"uuid": 1}
        ).to_list(length=200)
        matching_client_ids = [c["uuid"] for c in matching_clients]
        search_conditions = [
            {"certificate_number": {"$regex": search, "$options": "i"}},
            {"fields": {"$regex": search, "$options": "i"}},
            {"type": {"$regex": search, "$options": "i"}},
        ]
        if matching_client_ids:
            search_conditions.append({"client_id": {"$in": matching_client_ids}})
        filt["$or"] = search_conditions

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

        # Join with category schema (for field definitions and labels)
        if doc.get("category_id"):
            schema = await db.category_schemas.find_one({
                "uuid": doc["category_id"],
                "is_deleted": False
            })
            if schema:
                doc["schema"] = {
                    "uuid": schema["uuid"],
                    "name": schema["name"],
                    "group": schema["group"],
                    "fields": schema.get("fields", [])
                }

                # Render description from template if available
                description_template = schema.get("description_template")
                if description_template and doc.get("fields"):
                    doc["generated_description"] = render_description_template(
                        description_template,
                        doc.get("fields", {})
                    )

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

# ✅ Form Schema: returns category schema fields for dynamic form rendering
# Dynamically populates dropdown options from the attributes collection
@router.get("/form-schema/{category_uuid}")
async def get_form_schema(category_uuid: str):
    db = await get_db()
    schema = await db.category_schemas.find_one({
        "uuid": category_uuid,
        "is_deleted": False,
        "is_active": True,
    })
    if not schema:
        raise HTTPException(status_code=404, detail="Category schema not found")
    
    # Get the group (certificate type slug) for this schema
    group = schema.get("group")
    
    # Dynamically populate options for dropdown and creatable_select fields
    enriched_fields = []
    for field in schema.get("fields", []):
        enriched_field = dict(field)
        
        # For dropdown, radio, and creatable_select fields, load options from attributes
        if field.get("field_type") in {"dropdown", "radio", "creatable_select"}:
            field_type_key = field.get("field_name")
            # Fetch attributes for this group/field type
            cursor = db.attributes.find({
                "group": group,
                "type": field_type_key,
                "is_deleted": False
            }).sort([("name", 1)])

            attrs = [doc async for doc in cursor]
            options = [doc.get("name") for doc in attrs]

            # If we found attributes, use them; otherwise keep the schema's default options
            if options:
                enriched_field["options"] = options
                # Include extra properties (hardness, ri, sg) if any attribute has them
                extra_props = ["hardness", "ri", "sg"]
                metadata = {
                    a["name"]: {k: a[k] for k in extra_props if a.get(k) is not None}
                    for a in attrs
                    if any(a.get(k) is not None for k in extra_props)
                }
                if metadata:
                    enriched_field["attribute_metadata"] = metadata
        
        enriched_fields.append(enriched_field)
    
    schema["fields"] = enriched_fields
    return serialize_mongo_doc(schema)


# ✅ Active category schemas list (for certificate form dropdown)
@router.get("/available-schemas")
async def list_available_schemas(group: Optional[str] = None):
    db = await get_db()
    filt = {"is_deleted": False, "is_active": True}
    if group:
        filt["group"] = group
    cursor = db.category_schemas.find(filt).sort([("name", 1)])
    items = []
    async for doc in cursor:
        items.append(serialize_mongo_doc({
            "uuid": doc["uuid"],
            "name": doc["name"],
            "group": doc["group"],
            "field_count": len(doc.get("fields", [])),
        }))
    return {"data": items}


# ✅ Stats: Overview
@router.get("/stats")
async def certification_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": "$type", "count": {"$count": {}}}}
    ]
    res = await db.certifications.aggregate(pipeline).to_list(None)
    stats = {d["_id"]: d["count"] for d in res}
    total = sum(stats.values())
    return {
        "total": total,
        "by_type": stats
    }

# ✅ Stats: Daily
@router.get("/stats/daily")
async def certification_stats_daily(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$count": {}}}},
        {"$sort": {"_id": 1}},
    ]
    res = await db.certifications.aggregate(pipeline).to_list(None)
    return {"daily": res}


# ✅ Get Single Certificate by UUID
@router.get("/{uuid}")
async def get_certification(uuid: str):
    """
    Get a single certificate by UUID with schema and presigned URLs.
    Public endpoint for certificate viewing.
    """
    db = await get_db()
    doc = await db.certifications.find_one({
        "uuid": uuid,
        "is_deleted": False
    })

    if not doc:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # Join with client
    client = await db.clients.find_one({
        "uuid": doc["client_id"],
        "is_deleted": False
    })
    doc["client"] = {
        "id": client["uuid"],
        "name": client["name"]
    } if client else None

    # Join with category schema (for field definitions and labels)
    if doc.get("category_id"):
        schema = await db.category_schemas.find_one({
            "uuid": doc["category_id"],
            "is_deleted": False
        })
        if schema:
            doc["schema"] = {
                "uuid": schema["uuid"],
                "name": schema["name"],
                "group": schema["group"],
                "fields": schema.get("fields", [])
            }

            # Render description from template if available
            description_template = schema.get("description_template")
            if description_template and doc.get("fields"):
                doc["generated_description"] = render_description_template(
                    description_template,
                    doc.get("fields", {})
                )

    serialized = serialize_mongo_doc(doc)
    serialized = attach_presigned_urls(serialized)

    return serialized


# ✅ Delete Certificate
@router.delete("/{uuid}")
async def delete_certification(uuid: str):
    """
    Soft delete a certification by marking it as deleted.
    """
    db = await get_db()
    doc = await db.certifications.find_one({
        "uuid": uuid,
        "is_deleted": False
    })

    if not doc:
        raise HTTPException(status_code=404, detail="Certificate not found")

    # Soft delete by marking as_deleted
    await db.certifications.update_one(
        {"uuid": uuid},
        {
            "$set": {
                "is_deleted": True,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {"detail": "Certificate deleted successfully"}


class DownloadPdfPayload(BaseModel):
    uuids: List[str]


@router.post("/download-pdf")
async def download_certificates_pdf(payload: DownloadPdfPayload):
    if not payload.uuids:
        raise HTTPException(status_code=400, detail="No certificates selected")

    from ..utils.cert_pdf_generator import generate_certificates_pdf_async

    db = await get_db()
    raw_docs = await db.certifications.find(
        {"uuid": {"$in": payload.uuids}, "is_deleted": False}
    ).to_list(length=len(payload.uuids))

    if not raw_docs:
        raise HTTPException(status_code=404, detail="No matching certificates found")

    order_map = {uuid: index for index, uuid in enumerate(payload.uuids)}
    docs_by_uuid = {}
    schema_uuids = set()

    for raw_doc in raw_docs:
        doc = attach_presigned_urls(serialize_mongo_doc(raw_doc))
        schema_uuid = doc.get("schema_uuid") or doc.get("category_uuid") or doc.get("category_id")
        if schema_uuid:
            schema_uuids.add(schema_uuid)
        if doc.get("qr_code_url"):
            try:
                bucket, file_id = doc["qr_code_url"].split("/", 1)
                doc["qr_code_signed_url"] = get_presigned_url(bucket, file_id)
            except Exception:
                pass
        docs_by_uuid[doc["uuid"]] = doc

    schemas = await db.category_schemas.find(
        {"uuid": {"$in": list(schema_uuids)}}
    ).to_list(length=len(schema_uuids) or None)
    schema_map = {schema["uuid"]: serialize_mongo_doc(schema) for schema in schemas}

    certs = []
    for cert_uuid in payload.uuids:
        doc = docs_by_uuid.get(cert_uuid)
        if not doc:
            continue
        schema_uuid = doc.get("schema_uuid") or doc.get("category_uuid") or doc.get("category_id")
        schema = schema_map.get(schema_uuid)
        if schema:
            doc["schema"] = schema
            description_template = schema.get("description_template")
            if description_template and doc.get("fields"):
                doc["generated_description"] = render_description_template(
                    description_template, doc["fields"]
                )
        certs.append(doc)

    if not certs:
        raise HTTPException(status_code=404, detail="No matching certificates found")

    try:
        pdf_bytes = await generate_certificates_pdf_async(certs)
    except Exception:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate PDF")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="certificates_{len(certs)}.pdf"'},
    )
