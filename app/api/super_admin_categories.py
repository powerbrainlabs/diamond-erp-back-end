from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
import uuid
import copy

from ..core.dependencies import require_super_admin
from ..db.database import get_db
from ..schemas.category_schema import (
    CategorySchemaCreate,
    CategorySchemaUpdate,
    FieldsReplacePayload,
    ReorderPayload,
)
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(
    prefix="/api/super-admin/categories",
    tags=["Super Admin - Category Schemas"],
)


def _ensure_field_ids(fields: list) -> list:
    """Auto-generate field_id for any field missing one."""
    for f in fields:
        if isinstance(f, dict):
            if not f.get("field_id"):
                f["field_id"] = str(uuid.uuid4())
        else:
            if not f.field_id:
                f.field_id = str(uuid.uuid4())
    return fields


def serialize_schema(doc: dict) -> dict:
    """Convert a category_schema MongoDB doc to JSON-safe dict."""
    return serialize_mongo_doc({
        "uuid": doc.get("uuid"),
        "name": doc.get("name"),
        "group": doc.get("group"),
        "description": doc.get("description"),
        "fields": doc.get("fields", []),
        "is_active": doc.get("is_active"),
        "created_by": doc.get("created_by"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    })


# ── Create ────────────────────────────────────────────────────────────
@router.post("", status_code=201)
async def create_category_schema(
    payload: CategorySchemaCreate,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()

    # Duplicate name check
    existing = await db.category_schemas.find_one({
        "name": {"$regex": f"^{payload.name}$", "$options": "i"},
        "is_deleted": False,
    })
    if existing:
        raise HTTPException(status_code=409, detail="A category with this name already exists")

    now = datetime.utcnow()
    fields_dicts = [f.model_dump() for f in payload.fields]
    _ensure_field_ids(fields_dicts)

    doc = {
        "uuid": str(uuid.uuid4()),
        "name": payload.name,
        "group": payload.group,
        "description": payload.description,
        "fields": fields_dicts,
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

    await db.category_schemas.insert_one(doc)
    return serialize_schema(doc)


# ── List ──────────────────────────────────────────────────────────────
@router.get("")
async def list_category_schemas(
    current_user: dict = Depends(require_super_admin),
    group: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    db = await get_db()
    filt: dict = {"is_deleted": False}

    if group:
        filt["group"] = group
    if is_active is not None:
        filt["is_active"] = is_active
    if search:
        filt["name"] = {"$regex": search, "$options": "i"}

    allowed_sorts = {"created_at": "created_at", "name": "name"}
    sort_field = allowed_sorts.get(sort_by, "created_at")
    sort_dir = -1 if order == "desc" else 1

    total = await db.category_schemas.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)

    cursor = (
        db.category_schemas.find(filt)
        .sort([(sort_field, sort_dir)])
        .skip(skip)
        .limit(limit)
    )
    items = [serialize_schema(doc) async for doc in cursor]

    total_pages = (total + limit - 1) // limit if limit else 1
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "data": items,
    }


# ── Get Single ────────────────────────────────────────────────────────
@router.get("/{schema_uuid}")
async def get_category_schema(
    schema_uuid: str,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.category_schemas.find_one({"uuid": schema_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Category schema not found")
    return serialize_schema(doc)


# ── Update Metadata ──────────────────────────────────────────────────
@router.put("/{schema_uuid}")
async def update_category_schema(
    schema_uuid: str,
    payload: CategorySchemaUpdate,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.category_schemas.find_one({"uuid": schema_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Category schema not found")

    updates = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.description is not None:
        updates["description"] = payload.description
    if payload.is_active is not None:
        updates["is_active"] = payload.is_active
    updates["updated_at"] = datetime.utcnow()

    await db.category_schemas.update_one({"_id": doc["_id"]}, {"$set": updates})
    fresh = await db.category_schemas.find_one({"_id": doc["_id"]})
    return serialize_schema(fresh)


# ── Soft Delete ──────────────────────────────────────────────────────
@router.delete("/{schema_uuid}")
async def delete_category_schema(
    schema_uuid: str,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.category_schemas.find_one({"uuid": schema_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Category schema not found")

    await db.category_schemas.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    return {"detail": "Category schema deleted"}


# ── Replace Fields (used by builder UI) ──────────────────────────────
@router.put("/{schema_uuid}/fields")
async def replace_fields(
    schema_uuid: str,
    payload: FieldsReplacePayload,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.category_schemas.find_one({"uuid": schema_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Category schema not found")

    fields_dicts = [f.model_dump() for f in payload.fields]
    _ensure_field_ids(fields_dicts)

    # Assign display_order from list position
    for idx, f in enumerate(fields_dicts):
        f["display_order"] = idx

    await db.category_schemas.update_one(
        {"_id": doc["_id"]},
        {"$set": {"fields": fields_dicts, "updated_at": datetime.utcnow()}},
    )
    fresh = await db.category_schemas.find_one({"_id": doc["_id"]})
    return serialize_schema(fresh)


# ── Reorder Fields ───────────────────────────────────────────────────
@router.patch("/{schema_uuid}/reorder")
async def reorder_fields(
    schema_uuid: str,
    payload: ReorderPayload,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.category_schemas.find_one({"uuid": schema_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Category schema not found")

    fields_by_id = {f["field_id"]: f for f in doc.get("fields", [])}
    reordered = []
    for idx, fid in enumerate(payload.field_order):
        if fid in fields_by_id:
            field = fields_by_id[fid]
            field["display_order"] = idx
            reordered.append(field)

    # Append any fields not mentioned in the order list
    mentioned = set(payload.field_order)
    for f in doc.get("fields", []):
        if f["field_id"] not in mentioned:
            f["display_order"] = len(reordered)
            reordered.append(f)

    await db.category_schemas.update_one(
        {"_id": doc["_id"]},
        {"$set": {"fields": reordered, "updated_at": datetime.utcnow()}},
    )
    fresh = await db.category_schemas.find_one({"_id": doc["_id"]})
    return serialize_schema(fresh)


# ── Duplicate ────────────────────────────────────────────────────────
@router.post("/{schema_uuid}/duplicate", status_code=201)
async def duplicate_category_schema(
    schema_uuid: str,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.category_schemas.find_one({"uuid": schema_uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Category schema not found")

    now = datetime.utcnow()
    new_fields = copy.deepcopy(doc.get("fields", []))
    for f in new_fields:
        f["field_id"] = str(uuid.uuid4())

    new_doc = {
        "uuid": str(uuid.uuid4()),
        "name": f"{doc['name']} (Copy)",
        "group": doc["group"],
        "description": doc.get("description"),
        "fields": new_fields,
        "is_active": False,
        "is_deleted": False,
        "created_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        },
        "created_at": now,
        "updated_at": now,
    }

    await db.category_schemas.insert_one(new_doc)
    return serialize_schema(new_doc)
