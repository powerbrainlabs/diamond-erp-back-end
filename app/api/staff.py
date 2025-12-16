from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId

from ..core.dependencies import require_admin
from ..core.security import hash_password, verify_password
from ..db.database import get_db
from ..utils.serializers import dump_user

router = APIRouter(prefix="/api/staff", tags=["Staff"])

class StaffCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=2)
    role: Literal["staff", "admin"] = "staff"

class StaffUpdate(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=2)
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[Literal["staff", "admin"]] = None
    is_active: Optional[bool] = None

@router.post("", status_code=201)
async def create_staff(
    payload: StaffCreate,
    current_user: dict = Depends(require_admin)
):
    """Create a new staff member (admin only)"""
    db = await get_db()
    
    # Check if email already exists
    existing = await db.users.find_one({"email": payload.email})
    if existing:
        raise HTTPException(status_code=409, detail="Email already exists")
    
    now = datetime.utcnow()
    doc = {
        "email": payload.email,
        "password": hash_password(payload.password),
        "name": payload.name,
        "role": payload.role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    
    res = await db.users.insert_one(doc)
    created = await db.users.find_one({"_id": res.inserted_id})
    return dump_user(created)

@router.get("")
async def list_staff(
    current_user: dict = Depends(require_admin),
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    """List all staff members and admins (admin only)"""
    db = await get_db()
    
    query = {"role": {"$in": ["staff", "admin"]}}
    
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    
    skip = (page - 1) * limit
    
    # Get total count
    total = await db.users.count_documents(query)
    
    # Build sort
    sort_direction = 1 if order == "asc" else -1
    sort_field = sort_by if sort_by in ["name", "email", "created_at", "is_active"] else "created_at"
    
    # Fetch staff
    cursor = db.users.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
    staff_list = await cursor.to_list(length=limit)
    
    return {
        "data": [dump_user(s) for s in staff_list],
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit,
        "has_next": skip + limit < total,
        "has_prev": page > 1,
    }

@router.get("/{staff_id}")
async def get_staff(
    staff_id: str,
    current_user: dict = Depends(require_admin)
):
    """Get a single staff member or admin by ID (admin only)"""
    db = await get_db()
    
    try:
        doc = await db.users.find_one({"_id": ObjectId(staff_id), "role": {"$in": ["staff", "admin"]}})
    except:
        raise HTTPException(status_code=400, detail="Invalid staff ID")
    
    if not doc:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    return dump_user(doc)

@router.put("/{staff_id}")
async def update_staff(
    staff_id: str,
    payload: StaffUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update a staff member or admin (admin only)"""
    db = await get_db()
    
    try:
        doc = await db.users.find_one({"_id": ObjectId(staff_id), "role": {"$in": ["staff", "admin"]}})
    except:
        raise HTTPException(status_code=400, detail="Invalid staff ID")
    
    if not doc:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Check if email is being changed and if it already exists
    if payload.email and payload.email != doc["email"]:
        existing = await db.users.find_one({"email": payload.email})
        if existing:
            raise HTTPException(status_code=409, detail="Email already exists")
    
    update_data = {"updated_at": datetime.utcnow()}
    
    if payload.email:
        update_data["email"] = payload.email
    if payload.name:
        update_data["name"] = payload.name
    if payload.password:
        update_data["password"] = hash_password(payload.password)
    if payload.role:
        update_data["role"] = payload.role
    if payload.is_active is not None:
        update_data["is_active"] = payload.is_active
    
    await db.users.update_one(
        {"_id": ObjectId(staff_id)},
        {"$set": update_data}
    )
    
    updated = await db.users.find_one({"_id": ObjectId(staff_id)})
    return dump_user(updated)

@router.delete("/{staff_id}")
async def delete_staff(
    staff_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete (deactivate) a staff member or admin (admin only)"""
    db = await get_db()
    
    try:
        doc = await db.users.find_one({"_id": ObjectId(staff_id), "role": {"$in": ["staff", "admin"]}})
    except:
        raise HTTPException(status_code=400, detail="Invalid staff ID")
    
    if not doc:
        raise HTTPException(status_code=404, detail="Staff member not found")
    
    # Soft delete - set is_active to False
    await db.users.update_one(
        {"_id": ObjectId(staff_id)},
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    
    return {"message": "Staff member deactivated successfully"}

