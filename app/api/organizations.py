from datetime import datetime
import re

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..core.dependencies import require_admin, require_super_admin
from ..core.security import hash_password
from ..db.database import get_db
from ..schemas.organization import OrganizationCreate, OrganizationUpdate
from ..utils.organizations import normalize_org_id, serialize_organization
from ..utils.serializers import dump_user

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "organization"


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
