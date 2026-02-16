from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from pydantic import BaseModel
from ..db.database import get_db
from ..core.dependencies import require_admin
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/api/manufacturers", tags=["Manufacturers"])


class ManufacturerCreate(BaseModel):
    name: str
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class ManufacturerUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


# ✅ Create Manufacturer
@router.post("", status_code=201)
async def create_manufacturer(
    payload: ManufacturerCreate,
    current_user: dict = Depends(require_admin)
):
    db = await get_db()

    doc = {
        "uuid": str(uuid.uuid4()),
        "name": payload.name,
        "contact_person": payload.contact_person,
        "email": payload.email,
        "phone": payload.phone,
        "address": payload.address,
        "notes": payload.notes,
        "is_deleted": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    await db.manufacturers.insert_one(doc)
    return serialize_mongo_doc(doc)


# ✅ List Manufacturers
@router.get("")
async def list_manufacturers(
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "name",
    order: str = "asc",
):
    """
    Fetch paginated manufacturers with optional search.
    """
    db = await get_db()
    filt = {"is_deleted": False}

    if search:
        filt["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
        ]

    sort_dir = -1 if order == "desc" else 1

    total = await db.manufacturers.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)

    cursor = (
        db.manufacturers.find(filt)
        .sort([(sort_by, sort_dir)])
        .skip(skip)
        .limit(limit)
    )

    items = [serialize_mongo_doc(doc) async for doc in cursor]

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


# ✅ Get Stats (MUST be before /{uuid} to avoid route conflict)
@router.get("/stats")
async def manufacturer_stats():
    db = await get_db()
    total = await db.manufacturers.count_documents({"is_deleted": False})
    return {"total": total}


# ✅ Get Single Manufacturer
@router.get("/{uuid}")
async def get_manufacturer(uuid: str):
    db = await get_db()
    doc = await db.manufacturers.find_one({
        "uuid": uuid,
        "is_deleted": False
    })

    if not doc:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    return serialize_mongo_doc(doc)


# ✅ Update Manufacturer
@router.put("/{uuid}")
async def update_manufacturer(
    uuid: str,
    payload: ManufacturerUpdate,
    current_user: dict = Depends(require_admin)
):
    db = await get_db()
    doc = await db.manufacturers.find_one({
        "uuid": uuid,
        "is_deleted": False
    })

    if not doc:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    updates = {}
    for field in ["name", "contact_person", "email", "phone", "address", "notes"]:
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val

    updates["updated_at"] = datetime.utcnow()
    await db.manufacturers.update_one({"uuid": uuid}, {"$set": updates})

    fresh = await db.manufacturers.find_one({"uuid": uuid})
    return serialize_mongo_doc(fresh)


# ✅ Delete Manufacturer
@router.delete("/{uuid}")
async def delete_manufacturer(
    uuid: str,
    current_user: dict = Depends(require_admin)
):
    db = await get_db()
    doc = await db.manufacturers.find_one({
        "uuid": uuid,
        "is_deleted": False
    })

    if not doc:
        raise HTTPException(status_code=404, detail="Manufacturer not found")

    await db.manufacturers.update_one(
        {"uuid": uuid},
        {
            "$set": {
                "is_deleted": True,
                "updated_at": datetime.utcnow()
            }
        }
    )

    return {"detail": "Manufacturer deleted successfully"}
