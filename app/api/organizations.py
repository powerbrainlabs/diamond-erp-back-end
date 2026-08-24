import io
import uuid
import secrets
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..db.database import get_db
from ..core.dependencies import require_super_admin, get_current_user
from ..core.security import hash_password
from ..core.minio_client import minio_client
from ..utils.minio_helpers import get_presigned_url
from ..utils.serializers import dump_organization
from ..schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    ORGANIZATION_FIELDS,
)
from .files import compress_image

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])

ORG_LOGO_BUCKET = "org-logos"


def _generate_temp_password() -> str:
    return secrets.token_urlsafe(9)


@router.post("", status_code=201)
async def create_organization(
    payload: OrganizationCreate,
    _: dict = Depends(require_super_admin),
):
    db = await get_db()

    admin_email = str(payload.admin.email).strip().lower()
    if await db.users.find_one({"email": admin_email}):
        raise HTTPException(status_code=409, detail="Admin email already exists")

    now = datetime.utcnow()
    org_uuid = str(uuid.uuid4())

    org_doc = {"uuid": org_uuid, "created_at": now, "updated_at": now}
    for field in ORGANIZATION_FIELDS:
        org_doc[field] = getattr(payload, field)

    await db.organizations.insert_one(org_doc)

    # Provision the first admin for this organization.
    temp_password = payload.admin.password or _generate_temp_password()
    auto_generated = not bool(payload.admin.password)
    await db.users.insert_one({
        "email": admin_email,
        "password": hash_password(temp_password),
        "name": payload.admin.name,
        "role": "admin",
        "organization_id": org_uuid,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    })

    result = dump_organization(await db.organizations.find_one({"uuid": org_uuid}))
    if auto_generated:
        result["temp_password"] = temp_password
    return result


@router.get("")
async def list_organizations(_: dict = Depends(require_super_admin)):
    db = await get_db()
    docs = await db.organizations.find({}).sort("created_at", -1).to_list(length=1000)
    return [dump_organization(doc) for doc in docs]


@router.get("/me")
async def get_my_organization(current_user: dict = Depends(get_current_user)):
    org_id = current_user.get("organization_id")
    if not org_id:
        raise HTTPException(status_code=404, detail="No organization associated with this account")
    db = await get_db()
    org = await db.organizations.find_one({"uuid": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return dump_organization(org)


@router.put("/{organization_id}")
async def update_organization(
    organization_id: str,
    payload: OrganizationUpdate,
    _: dict = Depends(require_super_admin),
):
    db = await get_db()
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        org = await db.organizations.find_one({"uuid": organization_id})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return dump_organization(org)

    updates["updated_at"] = datetime.utcnow()
    result = await db.organizations.update_one({"uuid": organization_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Organization not found")
    return dump_organization(await db.organizations.find_one({"uuid": organization_id}))


@router.post("/upload-logo")
async def upload_organization_logo(
    file: UploadFile = File(...),
    _: dict = Depends(require_super_admin),
):
    filename = file.filename or "logo"
    lower = filename.lower()
    file_bytes = await file.read()

    if lower.endswith(".svg") or (file.content_type or "") == "image/svg+xml":
        content_type = "image/svg+xml"
    else:
        file_bytes, content_type = compress_image(file_bytes, filename)

    object_name = f"{uuid.uuid4()}_{filename}"
    try:
        minio_client.put_object(
            bucket_name=ORG_LOGO_BUCKET,
            object_name=object_name,
            data=io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Logo upload failed: {exc}")

    return {"logo_url": get_presigned_url(ORG_LOGO_BUCKET, object_name)}
