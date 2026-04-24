from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
import uuid
from bson import ObjectId
from pydantic import BaseModel

from ..core.dependencies import require_admin, require_staff
from ..db.database import get_db
from ..schemas.client import ClientCreate, ClientUpdate
from ..utils.serializers import dump_client
from ..core.minio_client import minio_client, CopySource

router = APIRouter(prefix="/api/clients", tags=["Clients"])

ALLOWED_SORTS = {"created_at": "created_at", "name": "name"}

# ✅ Create Client
@router.post("", status_code=201)
async def create_client(payload: ClientCreate, current_user: dict = Depends(require_staff)):
    db = await get_db()

    # Check duplicate (email or phone)
    if payload.email:
        existing = await db.clients.find_one({"email": payload.email, "is_deleted": False})
        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")
    if payload.phone:
        existing = await db.clients.find_one({"phone": payload.phone, "is_deleted": False})
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

    await db.clients.insert_one(doc)
    return dump_client(doc)


# ✅ List Clients
@router.get("")
async def list_clients(
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

    total = await db.clients.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)
    cursor = db.clients.find(filt).sort([(sort_field, sort_dir)]).skip(skip).limit(limit)
    items = [dump_client(doc) async for doc in cursor]

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


# ✅ Client Stats (MUST be before /{uuid} to avoid route conflict)
@router.get("/stats")
async def client_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": None, "total_clients": {"$count": {}}}},
    ]
    res = await db.clients.aggregate(pipeline).to_list(1)
    total = res[0]["total_clients"] if res else 0
    return {"total_clients": total}


# ✅ Get Single Client
@router.get("/{uuid}")
async def get_client(uuid: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.clients.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Client not found")
    return dump_client(doc)


# ✅ Update Client
@router.put("/{uuid}")
async def update_client(uuid: str, payload: ClientUpdate, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.clients.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = {}
    for field in ["name", "contact_person", "email", "phone", "address", "gst_number", "notes"]:
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val

    updates["updated_at"] = datetime.utcnow()
    await db.clients.update_one({"_id": doc["_id"]}, {"$set": updates})
    fresh = await db.clients.find_one({"_id": doc["_id"]})
    return dump_client(fresh)


# ✅ Update Client Logos
class ClientLogosUpdate(BaseModel):
    brand_logo_file_id: Optional[str] = None
    rear_logo_file_id: Optional[str] = None


def _promote_logo(file_id: str, old_url: Optional[str] = None) -> str:
    """Promote a logo from cert-temp to client-logos bucket, delete old one."""
    src = "cert-temp"
    dest = "client-logos"
    try:
        minio_client.stat_object(src, file_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Logo file not found in temp storage: {file_id}")
    source = CopySource(src, file_id)
    minio_client.copy_object(dest, file_id, source)
    minio_client.remove_object(src, file_id)
    if old_url:
        old_file_id = old_url.split("/", 1)[-1]
        try:
            minio_client.remove_object(dest, old_file_id)
        except Exception:
            pass
    return f"{dest}/{file_id}"


@router.put("/{uuid}/logos")
async def update_client_logos(uuid: str, payload: ClientLogosUpdate, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.clients.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Client not found")

    updates = {}
    if payload.brand_logo_file_id:
        updates["brand_logo_url"] = _promote_logo(payload.brand_logo_file_id, doc.get("brand_logo_url"))
    if payload.rear_logo_file_id:
        updates["rear_logo_url"] = _promote_logo(payload.rear_logo_file_id, doc.get("rear_logo_url"))

    if updates:
        updates["updated_at"] = datetime.utcnow()
        await db.clients.update_one({"_id": doc["_id"]}, {"$set": updates})

    fresh = await db.clients.find_one({"_id": doc["_id"]})
    return dump_client(fresh)


# ✅ Soft Delete Client
@router.delete("/{uuid}")
async def delete_client(uuid: str, current_user: dict = Depends(require_admin)):
    db = await get_db()
    doc = await db.clients.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Client not found")
    await db.clients.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    return {"detail": "Client deleted"}
