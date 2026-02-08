from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
import uuid

from ..core.dependencies import require_super_admin
from ..db.database import get_db
from ..schemas.certificate_type import (
    CertificateTypeCreate,
    CertificateTypeUpdate,
    ReorderTypesPayload,
)
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(
    prefix="/api/certificate-types",
    tags=["Certificate Types"],
)


def serialize_type(doc: dict) -> dict:
    return serialize_mongo_doc({
        "uuid": doc.get("uuid"),
        "slug": doc.get("slug"),
        "name": doc.get("name"),
        "description": doc.get("description"),
        "icon": doc.get("icon"),
        "display_order": doc.get("display_order", 0),
        "has_photo": doc.get("has_photo", True),
        "has_logo": doc.get("has_logo", True),
        "has_rear_logo": doc.get("has_rear_logo", True),
        "is_active": doc.get("is_active"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    })


# ── Public: list active types (for dropdowns) ───────────────────────
@router.get("")
async def list_certificate_types():
    db = await get_db()
    cursor = (
        db.certificate_types.find({"is_deleted": False, "is_active": True})
        .sort([("display_order", 1)])
    )
    return {"data": [serialize_type(doc) async for doc in cursor]}


# ── Super Admin: list all types including inactive ──────────────────
@router.get("/all")
async def list_all_certificate_types(
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    cursor = (
        db.certificate_types.find({"is_deleted": False})
        .sort([("display_order", 1)])
    )
    return {"data": [serialize_type(doc) async for doc in cursor]}


# ── Create ──────────────────────────────────────────────────────────
@router.post("", status_code=201)
async def create_certificate_type(
    payload: CertificateTypeCreate,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()

    existing = await db.certificate_types.find_one({
        "slug": payload.slug, "is_deleted": False,
    })
    if existing:
        raise HTTPException(status_code=409, detail="A type with this slug already exists")

    # Determine next display_order
    last = await db.certificate_types.find_one(
        {"is_deleted": False}, sort=[("display_order", -1)]
    )
    next_order = (last["display_order"] + 1) if last else 0

    now = datetime.utcnow()
    doc = {
        "uuid": str(uuid.uuid4()),
        "slug": payload.slug,
        "name": payload.name,
        "description": payload.description,
        "icon": payload.icon or "file-text",
        "display_order": next_order,
        "has_photo": payload.has_photo,
        "has_logo": payload.has_logo,
        "has_rear_logo": payload.has_rear_logo,
        "is_active": True,
        "is_deleted": False,
        "created_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        },
        "created_at": now,
        "updated_at": now,
    }

    await db.certificate_types.insert_one(doc)
    return serialize_type(doc)


# ── Update ──────────────────────────────────────────────────────────
@router.put("/{type_uuid}")
async def update_certificate_type(
    type_uuid: str,
    payload: CertificateTypeUpdate,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.certificate_types.find_one({"uuid": type_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Certificate type not found")

    updates = {}
    for field in ["name", "description", "icon", "display_order",
                   "has_photo", "has_logo", "has_rear_logo", "is_active"]:
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val
    updates["updated_at"] = datetime.utcnow()

    await db.certificate_types.update_one({"_id": doc["_id"]}, {"$set": updates})
    fresh = await db.certificate_types.find_one({"_id": doc["_id"]})
    return serialize_type(fresh)


# ── Soft Delete ─────────────────────────────────────────────────────
@router.delete("/{type_uuid}")
async def delete_certificate_type(
    type_uuid: str,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.certificate_types.find_one({"uuid": type_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Certificate type not found")

    await db.certificate_types.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    return {"detail": "Certificate type deleted"}


# ── Reorder ─────────────────────────────────────────────────────────
@router.patch("/reorder")
async def reorder_certificate_types(
    payload: ReorderTypesPayload,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    for idx, type_uuid in enumerate(payload.type_order):
        await db.certificate_types.update_one(
            {"uuid": type_uuid, "is_deleted": False},
            {"$set": {"display_order": idx, "updated_at": datetime.utcnow()}},
        )
    cursor = (
        db.certificate_types.find({"is_deleted": False})
        .sort([("display_order", 1)])
    )
    return {"data": [serialize_type(doc) async for doc in cursor]}
