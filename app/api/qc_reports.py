from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
import uuid

from ..schemas.qc_report import QCReportCreate, QCReportUpdate
from ..core.dependencies import require_staff
from ..db.database import get_db
from ..utils.serializers import dump_qc_report

router = APIRouter(prefix="/api/reports/qc", tags=["QC Reports"])

# ✅ Create QC Report
@router.post("", status_code=201)
async def create_qc_report(payload: QCReportCreate, current_user: dict = Depends(require_staff)):
    db = await get_db()
    
    # Validate job exists
    job = await db.jobs.find_one({"uuid": payload.job_id, "is_deleted": False})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Auto-generate OCR number (QC Report Number)
    # Format: OCR-YYYYMMDD-XXXX
    from datetime import datetime
    today = datetime.utcnow()
    date_prefix = today.strftime("%Y%m%d")
    
    # Find the last report number for today
    last_report = await db.qc_reports.find_one(
        {"ocr_no": {"$regex": f"^OCR-{date_prefix}-"}},
        sort=[("created_at", -1)]
    )
    
    if last_report and last_report.get("ocr_no"):
        # Extract the sequence number and increment
        last_seq = int(last_report["ocr_no"].split("-")[-1])
        new_seq = last_seq + 1
    else:
        new_seq = 1
    
    ocr_no = f"OCR-{date_prefix}-{new_seq:04d}"
    
    now = datetime.utcnow()
    
    # Convert lotData to dict format
    lot_data_dict = [lot.dict(by_alias=True) for lot in payload.lotData] if payload.lotData else []
    
    doc = {
        "uuid": str(uuid.uuid4()),
        "job_id": payload.job_id,
        "ocr_no": ocr_no,
        "clientname": payload.clientname,
        "phno": payload.phno,
        "address": payload.address,
        "country": payload.country,
        "state": payload.state,
        "city": payload.city,
        "lotData": lot_data_dict,
        "summary_note": payload.summary_note,
        "tested_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        },
        "status": "draft",
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    }
    
    await db.qc_reports.insert_one(doc)
    return dump_qc_report(doc)

# ✅ List QC Reports
@router.get("")
async def list_qc_reports(
    current_user: dict = Depends(require_staff),
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    db = await get_db()
    filt = {"is_deleted": False}
    
    if job_id:
        filt["job_id"] = job_id
    if status:
        filt["status"] = status
    
    total = await db.qc_reports.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)
    cursor = db.qc_reports.find(filt).sort([("created_at", -1)]).skip(skip).limit(limit)
    items = [dump_qc_report(doc) async for doc in cursor]
    
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

# ✅ Get Single QC Report
@router.get("/{uuid}")
async def get_qc_report(uuid: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.qc_reports.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="QC Report not found")
    return dump_qc_report(doc)

# ✅ Update QC Report
@router.put("/{uuid}")
async def update_qc_report(uuid: str, payload: QCReportUpdate, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.qc_reports.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="QC Report not found")
    
    updates = {}
    for field in ["clientname", "phno", "address", "summary_note", "status"]:
        val = getattr(payload, field, None)
        if val is not None:
            updates[field] = val
    
    # Handle lotData separately
    if payload.lotData is not None:
        updates["lotData"] = [lot.dict(by_alias=True) for lot in payload.lotData]
    
    updates["updated_at"] = datetime.utcnow()
    await db.qc_reports.update_one({"_id": doc["_id"]}, {"$set": updates})
    fresh = await db.qc_reports.find_one({"_id": doc["_id"]})
    return dump_qc_report(fresh)

# ✅ Delete QC Report
@router.delete("/{uuid}")
async def delete_qc_report(uuid: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.qc_reports.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="QC Report not found")
    
    await db.qc_reports.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    return {"detail": "QC Report deleted"}


# ✅ Stats: Overview
@router.get("/stats")
async def qc_report_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": "$status", "count": {"$count": {}}}}
    ]
    res = await db.qc_reports.aggregate(pipeline).to_list(None)
    stats = {d["_id"]: d["count"] for d in res}
    total = sum(stats.values())
    return {
        "total": total,
        "by_status": stats
    }

# ✅ Stats
@router.get("/stats/daily")
async def qc_stats_daily(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$count": {}}}},
        {"$sort": {"_id": 1}},
    ]
    res = await db.qc_reports.aggregate(pipeline).to_list(None)
    return {"daily": res}
