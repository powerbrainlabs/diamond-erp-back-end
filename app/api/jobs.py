from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId
import uuid

from ..schemas.job import JobCreate, JobUpdate, JobStatusPatch
from ..core.dependencies import require_admin, require_staff
from ..db.database import get_db
from ..utils.job_number import next_job_number
from ..utils.serializers import dump_job
from ..utils.action_logger import auto_log_action
from fastapi import Depends

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

ALLOWED_SORTS = {
    "created_at": "created_at",
    "expected_delivery_date": "expected_delivery_date",
    "job_number": "job_number"
}

# ✅ Create Job
@router.post("", status_code=201)
async def create_job(
    payload: JobCreate, 
    current_user: dict = Depends(require_staff),
    _: None = Depends(auto_log_action),  # Automatic logging - no logic needed!
):
    db = await get_db()

    # Validate client
    client = await db.clients.find_one({"uuid": payload.client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Validate manufacturer if provided
    if payload.manufacturer_id:
        manufacturer = await db.manufacturers.find_one({"uuid": payload.manufacturer_id, "is_deleted": False})
        if not manufacturer:
            raise HTTPException(status_code=404, detail="Manufacturer not found")

    now = datetime.utcnow()
    job_no = await next_job_number()
    
    # Use received_datetime if provided, otherwise use received_date, otherwise use now
    received_dt = payload.received_datetime or payload.received_date or now

    doc = {
        "uuid": str(uuid.uuid4()),
        "job_number": job_no,
        "client_id": payload.client_id,
        "manufacturer_id": payload.manufacturer_id,
        "item_type": payload.item_type,
        "item_description": payload.item_description,
        "item_quantity": payload.item_quantity,
        "item_weight": payload.item_weight,
        "item_size": payload.item_size,
        "priority": payload.priority,
        "status": "pending",
        "work_progress": {
            "qa": {"status": "pending", "started_at": None, "done_at": None, "done_by": None},
            "rfd": {"status": "pending", "started_at": None, "done_at": None, "done_by": None},
            "photography": {"status": "pending", "started_at": None, "done_at": None, "done_by": None},
        },
        "received_date": received_dt,  # Keep for backward compatibility
        "received_datetime": payload.received_datetime or received_dt,
        "received_from_name": payload.received_from_name,
        "expected_delivery_date": payload.expected_delivery_date,
        "actual_delivery_date": None,
        "notes": payload.notes,
        "created_by": {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        },
        "is_deleted": False,
        "created_at": now,
        "updated_at": now,
    }

    await db.jobs.insert_one(doc)
    result = dump_job(doc)
    
    # No logging code needed - auto_log_action handles it automatically!
    
    return result

# ✅ List Jobs (with pagination, sorting, and filters)
@router.get("")
async def list_jobs(
    current_user: dict = Depends(require_staff),
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    db = await get_db()
    filt = {"is_deleted": False}
    if status:
        filt["status"] = status

    sort_field = ALLOWED_SORTS.get(sort_by, "created_at")
    sort_dir = -1 if order == "desc" else 1

    total = await db.jobs.count_documents(filt)
    skip = (max(page, 1) - 1) * max(min(limit, 200), 1)
    cursor = db.jobs.find(filt).sort([(sort_field, sort_dir)]).skip(skip).limit(limit)
    items = [dump_job(doc) async for doc in cursor]

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

# ✅ Get Single Job by UUID
@router.get("get-job-details/{uuid}")
async def get_job(uuid: str, current_user: dict = Depends(require_staff)):
    db = await get_db()
    doc = await db.jobs.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not Found")
    return dump_job(doc)

# ✅ Update Job Info
@router.put("/{uuid}")
async def update_job(
    uuid: str, 
    payload: JobUpdate, 
    current_user: dict = Depends(require_staff),
    _: None = Depends(auto_log_action),  # Automatic logging
):
    db = await get_db()
    doc = await db.jobs.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not Found")

    # Validate manufacturer if provided
    if payload.manufacturer_id is not None:
        if payload.manufacturer_id:
            manufacturer = await db.manufacturers.find_one({"uuid": payload.manufacturer_id, "is_deleted": False})
            if not manufacturer:
                raise HTTPException(status_code=404, detail="Manufacturer not found")

    updates = {}
    for field in [
        "manufacturer_id", "item_type", "item_description", "item_quantity", 
        "item_weight", "item_size", "priority", 
        "expected_delivery_date", "received_datetime", "notes", "received_from_name"
    ]:
        val = getattr(payload, field)
        if val is not None:
            updates[field] = val

    # Handle received_date for backward compatibility
    if payload.received_date is not None:
        updates["received_date"] = payload.received_date
        if "received_datetime" not in updates:
            updates["received_datetime"] = payload.received_date

    updates["updated_at"] = datetime.utcnow()
    await db.jobs.update_one({"_id": doc["_id"]}, {"$set": updates})
    fresh = await db.jobs.find_one({"_id": doc["_id"]})
    result = dump_job(fresh)
    
    # No logging code needed - auto_log_action handles it automatically!
    
    return result

# ✅ Update Stage Progress (QA, RFD, Photography)
@router.patch("/{uuid}/progress/{stage}")
async def update_stage_progress(
    uuid: str,
    stage: Literal["qa", "rfd", "photography"],
    status: Literal["pending", "in_progress", "done"],
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    doc = await db.jobs.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not Found")

    now = datetime.utcnow()
    updates = {}
    stage_field = f"work_progress.{stage}"

    if status == "in_progress":
        updates[f"{stage_field}.status"] = "in_progress"
        updates[f"{stage_field}.started_at"] = now
    elif status == "done":
        updates[f"{stage_field}.status"] = "done"
        updates[f"{stage_field}.done_at"] = now
        updates[f"{stage_field}.done_by"] = {
            "user_id": current_user["id"],
            "name": current_user["name"],
            "email": current_user["email"],
        }
    else:
        updates[f"{stage_field}.status"] = "pending"
        updates[f"{stage_field}.started_at"] = None
        updates[f"{stage_field}.done_at"] = None
        updates[f"{stage_field}.done_by"] = None

    updates["updated_at"] = now
    await db.jobs.update_one({"_id": doc["_id"]}, {"$set": updates})

    # Auto-update main status
    job = await db.jobs.find_one({"_id": doc["_id"]})
    all_stages = job["work_progress"]

    if all(s["status"] == "pending" for s in all_stages.values()):
        main_status = "pending"
    elif all(s["status"] == "done" for s in all_stages.values()):
        main_status = "completed"
        job["actual_delivery_date"] = now
    else:
        main_status = "in_progress"

    await db.jobs.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": main_status, "actual_delivery_date": job.get("actual_delivery_date")}},
    )

    fresh = await db.jobs.find_one({"_id": doc["_id"]})
    return dump_job(fresh)

# ✅ Manually Update Overall Job Status
@router.patch("/{uuid}/status")
async def update_job_status(
    uuid: str,
    payload: JobStatusPatch,
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    doc = await db.jobs.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not Found")

    await db.jobs.update_one(
        {"_id": doc["_id"]},
        {"$set": {"status": payload.status, "updated_at": datetime.utcnow()}}
    )
    fresh = await db.jobs.find_one({"_id": doc["_id"]})
    return dump_job(fresh)

# ✅ Soft Delete
@router.delete("/{uuid}")
async def delete_job(
    uuid: str, 
    current_user: dict = Depends(require_admin),
    _: None = Depends(auto_log_action),  # Automatic logging
):
    db = await get_db()
    doc = await db.jobs.find_one({"uuid": uuid, "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not Found")
    await db.jobs.update_one(
        {"_id": doc["_id"]},
        {"$set": {"is_deleted": True, "updated_at": datetime.utcnow()}},
    )
    
    # No logging code needed - auto_log_action handles it automatically!
    
    return {"detail": "Job deleted"}

# ✅ Stats: Overview
@router.get("/stats")
async def job_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "by_status": [{"$group": {"_id": "$status", "count": {"$count": {}}}}],
            "active_jobs": [{"$match": {"status": {"$ne": "completed"}}}, {"$count": "count"}],
            "completed_today": [
                {"$match": {"status": "completed"}},
                {"$match": {"updated_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}}},
                {"$count": "count"}
            ],
        }}
    ]
    res = await db.jobs.aggregate(pipeline).to_list(1)
    agg = res[0] if res else {}
    def _get(lst): return lst[0]["count"] if lst else 0
    return {
        "total_jobs": _get(agg.get("total", [])),
        "by_status": {d["_id"]: d["count"] for d in agg.get("by_status", [])},
        "active_jobs": _get(agg.get("active_jobs", [])),
        "completed_today": _get(agg.get("completed_today", [])),
    }

# ✅ Stats: Daily Job Count
@router.get("/stats/daily")
async def job_stats_daily(current_user: dict = Depends(require_staff)):
    db = await get_db()
    pipeline = [
        {"$match": {"is_deleted": False}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}}, "count": {"$count": {}}}},
        {"$sort": {"_id": 1}},
    ]
    res = await db.jobs.aggregate(pipeline).to_list(None)
    return {"daily": res}
