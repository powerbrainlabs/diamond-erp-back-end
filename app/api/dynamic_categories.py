"""
Dynamic Categories API
----------------------
This API provides dynamic category management based on certificate types and schemas.
- Admins and staff can view certificate types and their schemas
- Admins can add/edit/delete attributes (color, clarity, etc.)
- Super admins can create certificate types (in Certificate Engine)
- Staff can only view categories
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime
import uuid as uuid_lib

from ..core.dependencies import require_super_admin, require_admin, require_staff
from ..db.database import get_db
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/api/dynamic-categories", tags=["Dynamic Categories"])


def serialize_attribute(doc: dict) -> dict:
    """Convert attribute MongoDB doc to JSON-safe dict."""
    return serialize_mongo_doc({
        "id": doc.get("uuid"),
        "uuid": doc.get("uuid"),
        "group": doc.get("group"),
        "type": doc.get("type"),
        "name": doc.get("name"),
        "hardness": doc.get("hardness"),
        "ri": doc.get("ri"),
        "sg": doc.get("sg"),
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
        "created_by": doc.get("created_by"),
    })


# ── Get all active certificate types (for tabs) ─────────────────────
@router.get("/types")
async def list_certificate_types(
    current_user: dict = Depends(require_staff),
):
    """List all active certificate types for category management tabs."""
    db = await get_db()
    cursor = db.certificate_types.find({
        "is_active": True,
        "is_deleted": False
    }).sort([("display_order", 1), ("name", 1)])
    
    types = []
    async for doc in cursor:
        types.append({
            "uuid": doc.get("uuid"),
            "name": doc.get("name"),
            "slug": doc.get("slug"),
            "display_order": doc.get("display_order", 0),
        })
    
    return {"data": types}


# ── Get schema fields for a certificate type (for sub-tabs) ─────────
@router.get("/types/{type_slug}/fields")
async def get_type_fields(
    type_slug: str,
    current_user: dict = Depends(require_staff),
):
    """Get manageable fields (dropdown, radio, creatable_select) for a certificate type."""
    db = await get_db()
    
    # Verify type exists
    cert_type = await db.certificate_types.find_one({
        "slug": type_slug,
        "is_active": True,
        "is_deleted": False
    })
    if not cert_type:
        raise HTTPException(status_code=404, detail=f"Certificate type '{type_slug}' not found")
    
    # Get active schema for this type
    schema = await db.category_schemas.find_one({
        "group": type_slug,
        "is_active": True,
        "is_deleted": False
    })
    
    if not schema:
        return {"data": [], "schema_uuid": None}
    
    # Filter fields that are "manageable" (have option lists)
    manageable_types = {"dropdown", "radio", "creatable_select"}
    fields = []
    for field in schema.get("fields", []):
        if field.get("field_type") in manageable_types:
            fields.append({
                "field_id": field.get("field_id"),
                "field_name": field.get("field_name"),
                "label": field.get("label"),
                "field_type": field.get("field_type"),
                "display_order": field.get("display_order", 0),
            })
    
    # Sort by display_order
    fields.sort(key=lambda x: x.get("display_order", 0))
    
    return {
        "data": fields,
        "schema_uuid": schema.get("uuid"),
        "schema_name": schema.get("name"),
    }


# ── List attributes for a group/type ─────────────────────────────────
@router.get("/attributes/{group}/{field_type}")
async def list_attributes(
    group: str,
    field_type: str,
    search: Optional[str] = None,
    current_user: dict = Depends(require_staff),
):
    """List all attributes for a given group and field type."""
    db = await get_db()
    
    filt = {"group": group, "type": field_type, "is_deleted": False}
    if search:
        filt["name"] = {"$regex": search, "$options": "i"}
    
    cursor = db.attributes.find(filt).sort([("created_at", -1)])
    data = [serialize_attribute(doc) async for doc in cursor]
    
    return {"data": data, "count": len(data)}


# ── Create attribute (Admin or Super Admin) ──────────────────────────
@router.post("/attributes/{group}/{field_type}", status_code=201)
async def create_attribute(
    group: str,
    field_type: str,
    payload: dict,
    current_user: dict = Depends(require_admin),
):
    """Create a new attribute. Admin or Super Admin."""
    db = await get_db()
    
    # Validate group exists as a certificate type
    cert_type = await db.certificate_types.find_one({
        "slug": group,
        "is_deleted": False
    })
    if not cert_type:
        raise HTTPException(status_code=400, detail=f"Invalid certificate type: {group}")
    
    # Required field
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="Field 'name' is required")
    
    # Check duplicates
    existing = await db.attributes.find_one({
        "group": group,
        "type": field_type,
        "name": {"$regex": f"^{name}$", "$options": "i"},
        "is_deleted": False
    })
    if existing:
        raise HTTPException(status_code=409, detail="An attribute with this name already exists")
    
    now = datetime.utcnow()
    doc = {
        "uuid": str(uuid_lib.uuid4()),
        "group": group,
        "type": field_type,
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
    
    # Extra fields for gemstone type
    for field in ["hardness", "ri", "sg"]:
        if field in payload:
            doc[field] = payload[field]
    
    await db.attributes.insert_one(doc)
    return serialize_attribute(doc)


# ── Update attribute (Admin or Super Admin) ──────────────────────────
@router.put("/attributes/{uuid}")
async def update_attribute(
    uuid: str,
    payload: dict,
    current_user: dict = Depends(require_admin),
):
    """Update an attribute. Admin or Super Admin."""
    db = await get_db()
    
    doc = await db.attributes.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Attribute not found")
    
    name = payload.get("name")
    if not name:
        raise HTTPException(status_code=422, detail="Field 'name' is required")
    
    # Check duplicates (excluding current)
    existing = await db.attributes.find_one({
        "group": doc["group"],
        "type": doc["type"],
        "name": {"$regex": f"^{name}$", "$options": "i"},
        "uuid": {"$ne": uuid},
        "is_deleted": False
    })
    if existing:
        raise HTTPException(status_code=409, detail="An attribute with this name already exists")
    
    update_data = {
        "name": name,
        "updated_at": datetime.utcnow()
    }
    
    # Extra fields for gemstone type
    for field in ["hardness", "ri", "sg"]:
        if field in payload:
            update_data[field] = payload[field]
    
    await db.attributes.update_one({"uuid": uuid}, {"$set": update_data})
    
    updated = await db.attributes.find_one({"uuid": uuid})
    return serialize_attribute(updated)


# ── Delete attribute (Admin or Super Admin) ──────────────────────────
@router.delete("/attributes/{uuid}")
async def delete_attribute(
    uuid: str,
    current_user: dict = Depends(require_admin),
):
    """Soft delete an attribute. Admin or Super Admin."""
    db = await get_db()
    
    doc = await db.attributes.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Attribute not found")
    
    await db.attributes.update_one(
        {"uuid": uuid},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Deleted successfully"}
