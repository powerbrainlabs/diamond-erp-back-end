from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId
import uuid

from ..core.dependencies import require_admin, require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/categories", tags=["Categories"])

# Allowed groups and types
DIAMOND_TYPES = {"category", "color", "clarity", "cut", "conclusion", "metal_type"}
GEMSTONE_TYPES = {"gemstone", "gemstone_category", "gemstone_shape", "gemstone_comments", "microscopic_observation"}
ALLOWED_GROUPS = {"diamond", "gemstone"}

# ✅ Create Attribute
@router.post("/{group}/{type}", status_code=201)
async def create_attribute(
    group: Literal["diamond", "gemstone"],
    type: str,
    payload: dict,
    current_user: dict = Depends(require_staff)
):
    db = await get_db()

    # Validate group & type
    if group not in ALLOWED_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid group")
    if group == "diamond" and type not in DIAMOND_TYPES:
        raise HTTPException(status_code=400, detail="Invalid diamond type")
    if group == "gemstone" and type not in GEMSTONE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid gemstone type")

    # Required field
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="Field 'name' is required")

    # Check duplicates
    existing = await db.attributes.find_one({
        "group": group,
        "type": type,
        "name": {"$regex": f"^{name}$", "$options": "i"},
        "is_deleted": False
    })
    if existing:
        raise HTTPException(status_code=409, detail="Name already exists")

    now = datetime.utcnow()
    doc = {
        "uuid": str(uuid.uuid4()),
        "group": group,
        "type": type,
        "name": name,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
        "created_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"]
        }
    }

    # Gemstone extras
    if group == "gemstone" and type == "gemstone":
        for field in ["hardness", "ri", "sg"]:
            if field in payload:
                doc[field] = payload[field]

    await db.attributes.insert_one(doc)
    return serialize_attribute(doc)


# ✅ List Attributes by group & type
@router.get("/list/{group}/{type}")
async def list_attributes(
    group: Literal["diamond", "gemstone"],
    type: str,
    search: Optional[str] = None,
    current_user: dict = Depends(require_staff),
):
    db = await get_db()

    # Validate group/type
    if group not in ALLOWED_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid group")
    if group == "diamond" and type not in DIAMOND_TYPES:
        raise HTTPException(status_code=400, detail="Invalid diamond type")
    if group == "gemstone" and type not in GEMSTONE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid gemstone type")

    filt = {"group": group, "type": type, "is_deleted": False}
    if search:
        filt["name"] = {"$regex": search, "$options": "i"}

    cursor = db.attributes.find(filt).sort([("created_at", -1)])
    data = [serialize_attribute(doc) async for doc in cursor]

    return {"data": data, "count": len(data)}


# ✅ Get Single Attribute
@router.get("/{uuid}")
async def get_attribute(uuid: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.attributes.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Attribute not found")
    return serialize_attribute(doc)


# ✅ Update Attribute
@router.put("/{uuid}")
async def update_attribute(uuid: str, payload: dict, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.attributes.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Attribute not found")

    updates = {}
    if "name" in payload:
        updates["name"] = payload["name"]
    for field in ["hardness", "ri", "sg"]:
        if field in payload:
            updates[field] = payload[field]

    updates["updated_at"] = datetime.utcnow()
    await db.attributes.update_one({"_id": doc["_id"]}, {"$set": updates})
    updated = await db.attributes.find_one({"_id": doc["_id"]})
    return serialize_attribute(updated)


# ✅ Soft Delete
@router.delete("/{uuid}")
async def delete_attribute(uuid: str, current_user: dict = Depends(require_admin)):
    db = await get_db()
    doc = await db.attributes.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Attribute not found")

    await db.attributes.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )
    return {"detail": "Attribute deleted"}


# ✅ Stats (optional)
@router.get("/stats/overview")
async def attribute_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": {"group": "$group", "type": "$type"}, "count": {"$count": {}}}},
    ]
    data = await db.attributes.aggregate(pipeline).to_list(None)
    stats = {}
    for d in data:
        g = d["_id"]["group"]
        t = d["_id"]["type"]
        stats.setdefault(g, {})[t] = d["count"]
    return {"stats": stats}


# Example structure:
CATEGORY_GROUPS = {
    "diamond": [
        "category",
        "color",
        "clarity",
        "cut",
        "conclusion",
        "metal_type",
    ],
    "gemstone": [
        "gemstone",
        "gemstone_category",
        "gemstone_shape",
        "gemstone_comments",
        "microscopic_observation",
    ],
}


@router.get("/by-type/{stone_type}")
async def get_categories_by_type(stone_type: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    print(stone_type)

    stone_type = stone_type.lower()
    if stone_type not in CATEGORY_GROUPS:
        raise HTTPException(status_code=400, detail="Invalid category type")

    result = {}

    for group in CATEGORY_GROUPS[stone_type]:
        docs = await db.attributes.find(
            {"group": stone_type, "type": group, "is_deleted": False}
        ).to_list(None)
        result[group] = [
            serialize_attribute(doc) for doc in docs
        ]

    return {
        "type": stone_type,
        "groups": result,
    }


# Utility Serializer
def serialize_attribute(doc):
    if not doc:
        return None
    
    # Serialize created_by to handle ObjectId in user_id
    created_by = doc.get("created_by", {})
    if created_by and isinstance(created_by, dict):
        created_by = created_by.copy()
        if isinstance(created_by.get("user_id"), ObjectId):
            created_by["user_id"] = str(created_by["user_id"])
    
    return {
        "id": str(doc.get("uuid")),
        "group": doc.get("group"),
        "type": doc.get("type"),
        "name": doc.get("name"),
        "hardness": doc.get("hardness"),
        "ri": doc.get("ri"),
        "sg": doc.get("sg"),
        "created_by": created_by,
        "created_at": doc.get("created_at").isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
        "updated_at": doc.get("updated_at").isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
    }
