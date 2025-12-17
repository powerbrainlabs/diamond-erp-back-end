from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId
import uuid

from ..core.dependencies import require_staff, require_admin
from ..db.database import get_db

router = APIRouter(prefix="/api/reports", tags=["QC Reports"])

def serialize_qc_report(doc):
    """Serialize QC report document"""
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
        "uuid": str(doc.get("uuid")),
        "lot_data": doc.get("lot_data", []),
        "clientname": doc.get("clientname"),
        "phno": doc.get("phno"),
        "address": doc.get("address"),
        "country": doc.get("country"),
        "state": doc.get("state"),
        "city": doc.get("city"),
        "summary_note": doc.get("summary_note"),
        "ocr_no": doc.get("ocr_no"),
        "created_by": created_by,
        "created_at": doc.get("created_at").isoformat() if isinstance(doc.get("created_at"), datetime) else doc.get("created_at"),
        "updated_at": doc.get("updated_at").isoformat() if isinstance(doc.get("updated_at"), datetime) else doc.get("updated_at"),
    }

# ✅ Create QC Report
@router.post("/qc", status_code=201)
async def create_qc_report(
    payload: Dict[str, Any],
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    
    # Handle both camelCase (from frontend) and snake_case
    lot_data = payload.get("lotData") or payload.get("lot_data")
    clientname = payload.get("clientname") or payload.get("client_name")
    
    # Validate required fields
    if not lot_data:
        raise HTTPException(status_code=422, detail="lotData is required")
    if not clientname:
        raise HTTPException(status_code=422, detail="clientname is required")
    
    now = datetime.utcnow()
    
    # Generate OCR number (you can customize this logic)
    # For now, using a simple format: OCR-YYYYMMDD-XXXX
    date_str = now.strftime("%Y%m%d")
    existing_today = await db.qc_reports.count_documents({
        "ocr_no": {"$regex": f"OCR-{date_str}"},
        "is_deleted": False
    })
    ocr_no = f"OCR-{date_str}-{str(existing_today + 1).zfill(4)}"
    
    doc = {
        "uuid": str(uuid.uuid4()),
        "lot_data": lot_data,
        "clientname": clientname,
        "phno": payload.get("phno", ""),
        "address": payload.get("address", ""),
        "country": payload.get("country", ""),
        "state": payload.get("state", ""),
        "city": payload.get("city", ""),
        "summary_note": payload.get("summary_note") or payload.get("summaryNote", ""),
        "ocr_no": ocr_no,
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
        "created_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"]
        }
    }
    
    await db.qc_reports.insert_one(doc)
    return {
        "message": "QC Report created successfully",
        "data": serialize_qc_report(doc)
    }

# ✅ List All QC Reports
@router.get("/qc")
async def list_qc_reports(
    current_user: dict = Depends(require_staff),
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    order: str = "desc"
):
    db = await get_db()
    
    filt = {"is_deleted": False}
    if search:
        filt["$or"] = [
            {"clientname": {"$regex": search, "$options": "i"}},
            {"ocr_no": {"$regex": search, "$options": "i"}},
            {"phno": {"$regex": search, "$options": "i"}},
        ]
    
    sort_order = -1 if order == "desc" else 1
    sort_field = sort_by if sort_by in ["created_at", "updated_at", "ocr_no"] else "created_at"
    
    skip = (page - 1) * limit
    
    cursor = db.qc_reports.find(filt).sort([(sort_field, sort_order)]).skip(skip).limit(limit)
    data = [serialize_qc_report(doc) async for doc in cursor]
    
    total = await db.qc_reports.count_documents(filt)
    
    return {
        "data": data,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": (total + limit - 1) // limit,
            "hasNext": page * limit < total,
            "hasPrev": page > 1
        }
    }

# ✅ Get QC Report by ID
@router.get("/qc/{uuid}")
async def get_qc_report(
    uuid: str,
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    doc = await db.qc_reports.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="QC Report not found")
    return serialize_qc_report(doc)

# ✅ Update QC Report
@router.put("/qc/{uuid}")
async def update_qc_report(
    uuid: str,
    payload: Dict[str, Any],
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    doc = await db.qc_reports.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="QC Report not found")
    
    updates = {}
    for field in ["lot_data", "clientname", "phno", "address", "country", "state", "city", "summary_note"]:
        if field in payload:
            updates[field] = payload[field]
    
    updates["updated_at"] = datetime.utcnow()
    await db.qc_reports.update_one({"_id": doc["_id"]}, {"$set": updates})
    
    updated = await db.qc_reports.find_one({"_id": doc["_id"]})
    return serialize_qc_report(updated)

# ✅ Delete QC Report (Soft Delete)
@router.delete("/qc/{uuid}")
async def delete_qc_report(
    uuid: str,
    current_user: dict = Depends(require_admin)
):
    db = await get_db()
    doc = await db.qc_reports.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="QC Report not found")
    
    await db.qc_reports.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}}
    )
    return {"detail": "QC Report deleted"}

