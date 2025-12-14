from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
import uuid
from bson import ObjectId

from ..core.dependencies import require_admin, require_staff
from ..db.database import get_db
from ..schemas.manufacturer import ManufacturerCreate, ManufacturerUpdate
from ..utils.serializers import dump_manufacturer

router = APIRouter(prefix="/api/manufacturers", tags=["Manufacturers"])

ALLOWED_SORTS = {"created_at": "created_at", "name": "name"}

# ✅ Create Manufacturer
@router.post("", status_code=201)
async def create_manufacturer(payload: ManufacturerCreate, current_user: dict = Depends(require_staff)):
    db = await get_db()

    # Check duplicate (email or phone)
    if payload.email:
        existing = await db.manufacturers.find_one({"email": payload.email, "is_deleted": False})
        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")
    if payload.phone:
        existing = await db.manufacturers.find_one({"phone": payload.phone, "is_deleted": False})
        if existing:
            raise HTTPException(status_code=409, detail="Phone already exists")

    now = datetime.utcnow()
    doc = {
        "uuid": str(uuid.uuid4()),
        "name": payload.name,
        "contact_person": payload.contact_person,
        "email": payload.email,
        "phone": payload.phone,
        "address": payload.address,
        "gst_number": payload.gst_number,
        "notes": payload.notes,
        "is_deleted": False,
        "created_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        },
        "created_at": now,
        "updated_at": now,
    }

    await db.manufacturers.insert_one(doc)
    return dump_manufacturer(doc)


# ✅ List Manufacturers
@router.get("")
async def list_manufacturers(
    current_user: dict = Depends(require_staff),
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    db = await get_db()
    filt = {"is_deleted": False}

    if search:
        filt["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]

    sort_field = ALLOWED_SORTS.get(sort_by, "created_at")
    sort_dir = -1 if order == "desc" else 1

    total = await db.manufacturers.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)
    cursor = db.manufacturers.find(filt).sort([(sort_field, sort_dir)]).skip(skip).limit(limit)
    items = [dump_manufacturer(doc) async for doc in cursor]

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


# ✅ Get Single Manufacturer
@router.get("/{uuid}")
async def get_manufacturer(uuid: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.manufacturers.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    return dump_manufacturer(doc)


# ✅ Update Manufacturer
@router.put("/{uuid}")
async def update_manufacturer(uuid: str, payload: ManufacturerUpdate, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.manufacturers.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    updates = {}
    for field in ["name", "contact_person", "email", "phone", "address", "gst_number", "notes"]:
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val

    updates["updated_at"] = datetime.utcnow()
    await db.manufacturers.update_one({"_id": doc["_id"]}, {"$set": updates})
    fresh = await db.manufacturers.find_one({"_id": doc["_id"]})
    return dump_manufacturer(fresh)


# ✅ Soft Delete Manufacturer
@router.delete("/{uuid}")
async def delete_manufacturer(uuid: str, current_user: dict = Depends(require_admin)):
    db = await get_db()
    doc = await db.manufacturers.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    await db.manufacturers.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    return {"detail": "Manufacturer deleted"}


# ✅ Manufacturer Stats
@router.get("/stats")
async def manufacturer_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": None, "total_manufacturers": {"$sum": 1}}},
    ]
    res = await db.manufacturers.aggregate(pipeline).to_list(1)
    total = res[0]["total_manufacturers"] if res and res[0] else 0
    return {"total_manufacturers": total}

