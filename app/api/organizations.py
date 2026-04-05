from datetime import datetime
import io
import re
import uuid

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile

from ..core.dependencies import require_admin, require_super_admin
from ..core.security import hash_password
from ..core.minio_client import minio_client
from ..db.database import get_db
from ..schemas.organization import OrganizationCreate, OrganizationUpdate
from ..utils.organizations import normalize_org_id, serialize_organization
from ..utils.serializers import dump_user
from ..utils.seed_schemas import seed_default_attributes, seed_default_certificate_types, seed_default_category_schemas
from .files import compress_image

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "organization"


@router.post("/upload-logo")
async def upload_organization_logo(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_super_admin),
):
    allowed_types = {
        "image/svg+xml": ".svg",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
    }
    content_type = (file.content_type or "").lower()
    filename = file.filename or "organization-logo"
    filename_lower = filename.lower()

    if content_type not in allowed_types and not filename_lower.endswith((".svg", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only SVG, PNG, JPG, and JPEG logo files are allowed")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded logo file is empty")

    object_name = f"organization-logos/{uuid.uuid4()}_{re.sub(r'[^a-zA-Z0-9._-]+', '_', filename)}"

    if content_type == "image/svg+xml" or filename_lower.endswith(".svg"):
        upload_bytes = raw_bytes
        upload_content_type = "image/svg+xml"
    else:
        upload_bytes, upload_content_type = compress_image(raw_bytes, filename)

    minio_client.put_object(
        bucket_name="certificates",
        object_name=object_name,
        data=io.BytesIO(upload_bytes),
        length=len(upload_bytes),
        content_type=upload_content_type,
    )

    return {
        "logo_url": f"/api/files/proxy/certificates/{object_name}",
        "content_type": upload_content_type,
        "filename": filename,
    }


@router.get("")
async def list_organizations(current_user: dict = Depends(require_super_admin)):
    db = await get_db()
    docs = await db.organizations.find({}).sort("created_at", -1).to_list(length=500)
    return [serialize_organization(doc) for doc in docs]


@router.post("", status_code=201)
async def create_organization(payload: OrganizationCreate, current_user: dict = Depends(require_super_admin)):
    db = await get_db()
    slug = slugify(payload.display_name or payload.official_name)

    if await db.users.find_one({"email": payload.admin.email}):
        raise HTTPException(status_code=409, detail="Admin email already exists")

    existing_slug = await db.organizations.find_one({"slug": slug})
    if existing_slug:
        slug = f"{slug}-{int(datetime.utcnow().timestamp())}"

    now = datetime.utcnow()
    org_doc = {
        "official_name": payload.official_name.strip(),
        "display_name": (payload.display_name or payload.official_name).strip(),
        "short_name": (payload.short_name or payload.display_name or payload.official_name).strip(),
        "slug": slug,
        "logo_url": payload.logo_url or "",
        "primary_email": payload.primary_email,
        "primary_phone": payload.primary_phone or "",
        "website": payload.website or "",
        "tax_id": payload.tax_id or "",
        "address_line_1": payload.address_line_1 or "",
        "address_line_2": payload.address_line_2 or "",
        "city": payload.city or "",
        "state": payload.state or "",
        "country": payload.country or "",
        "postal_code": payload.postal_code or "",
        "certificate_footer_text": payload.certificate_footer_text or "",
        "report_signature_name": payload.report_signature_name or "",
        "report_signature_title": payload.report_signature_title or "",
        "default_timezone": payload.default_timezone,
        "default_currency": payload.default_currency,
        "status": payload.status,
        "created_at": now,
        "updated_at": now,
    }

    res = await db.organizations.insert_one(org_doc)
    organization_id = res.inserted_id

    admin_doc = {
        "email": payload.admin.email,
        "password": hash_password(payload.admin.password),
        "name": payload.admin.name,
        "role": "admin",
        "features": [],
        "organization_id": organization_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    admin_res = await db.users.insert_one(admin_doc)

    await seed_default_attributes(db, organization_id)
    await seed_default_certificate_types(db, organization_id)
    await seed_default_category_schemas(db, organization_id)

    org = await db.organizations.find_one({"_id": organization_id})
    admin = await db.users.find_one({"_id": admin_res.inserted_id})
    admin["organization"] = org

    return {
        "organization": serialize_organization(org),
        "admin": dump_user(admin),
    }


@router.get("/me")
async def get_my_organization(current_user: dict = Depends(require_admin)):
    if current_user["role"] == "super_admin":
        raise HTTPException(status_code=400, detail="Super admin is not bound to a single organization")

    db = await get_db()
    org = await db.organizations.find_one({"_id": normalize_org_id(current_user["organization_id"])})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return serialize_organization(org)


@router.put("/{organization_id}")
async def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = datetime.utcnow()
    result = await db.organizations.update_one(
        {"_id": normalize_org_id(organization_id)},
        {"$set": updates},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Organization not found")

    org = await db.organizations.find_one({"_id": normalize_org_id(organization_id)})
    return serialize_organization(org)
