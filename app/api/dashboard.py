from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from typing import Dict, Any, Literal, Optional

from ..core.dependencies import require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


def get_time_range(time_period: str):
    """Calculate start and end dates based on time period"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if time_period == "hourly":
        start = now - timedelta(hours=1)
        end = now
    elif time_period == "daily":
        start = today
        end = now
    elif time_period == "weekly":
        start = today - timedelta(days=7)
        end = now
    elif time_period == "monthly":
        start = today - timedelta(days=30)
        end = now
    elif time_period == "yearly":
        start = today - timedelta(days=365)
        end = now
    else:  # overall
        start = datetime(2020, 1, 1)  # Very old date to get all data
        end = now
    
    return start, end


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(require_staff),
    time_period: Literal["hourly", "daily", "weekly", "monthly", "yearly", "overall"] = Query("daily", description="Time period for statistics")
):
    """
    Get comprehensive dashboard statistics
    Aggregates data from jobs, certificates, QC reports, clients, etc.
    Supports time period filtering: hourly, daily, weekly, monthly, yearly, overall
    """
    db = await get_db()
    start_date, end_date = get_time_range(time_period)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Jobs Stats
    job_pipeline = [
        {"$match": {"is_deleted": False, "created_at": {"$gte": start_date, "$lte": end_date}}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "by_status": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
            "active": [{"$match": {"status": {"$ne": "completed"}}}, {"$count": "count"}],
            "completed_in_period": [
                {"$match": {"status": "completed", "updated_at": {"$gte": start_date, "$lte": end_date}}},
                {"$count": "count"}
            ],
            "completed_today": [
                {"$match": {"status": "completed", "updated_at": {"$gte": today}}},
                {"$count": "count"}
            ],
            "completed_yesterday": [
                {"$match": {"status": "completed", "updated_at": {"$gte": yesterday, "$lt": today}}},
                {"$count": "count"}
            ],
            "pending_qc": [
                {"$match": {"job_type": "qc_job", "work_progress.qc.status": "pending"}},
                {"$count": "count"}
            ],
            "pending_certification": [
                {"$match": {"job_type": "certification_job", "work_progress.certification.status": "pending"}},
                {"$count": "count"}
            ],
            "in_progress_qc": [
                {"$match": {"job_type": "qc_job", "work_progress.qc.status": "in_progress"}},
                {"$count": "count"}
            ],
            "in_progress_certification": [
                {"$match": {"job_type": "certification_job", "work_progress.certification.status": "in_progress"}},
                {"$count": "count"}
            ],
            "created_in_period": [
                {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
                {"$count": "count"}
            ],
        }}
    ]
    job_res = await db.jobs.aggregate(job_pipeline).to_list(1)
    job_agg = job_res[0] if job_res else {}
    
    def _get(lst): return lst[0]["count"] if lst else 0
    
    jobs_completed_today = _get(job_agg.get("completed_today", []))
    jobs_completed_yesterday = _get(job_agg.get("completed_yesterday", []))
    jobs_completed_in_period = _get(job_agg.get("completed_in_period", []))
    jobs_created_in_period = _get(job_agg.get("created_in_period", []))
    
    jobs_change = 0
    if jobs_completed_yesterday > 0:
        jobs_change = ((jobs_completed_today - jobs_completed_yesterday) / jobs_completed_yesterday) * 100
    
    # Certificates Stats
    cert_pipeline = [
        {"$match": {"is_deleted": False, "created_at": {"$gte": start_date, "$lte": end_date}}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "created_today": [
                {"$match": {"created_at": {"$gte": today}}},
                {"$count": "count"}
            ],
            "created_in_period": [
                {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
                {"$count": "count"}
            ],
            "pending_photo_edit": [
                {"$match": {"photo_edit_completed": False, "photo_url": {"$ne": None}}},
                {"$count": "count"}
            ],
        }}
    ]
    cert_res = await db.certifications.aggregate(cert_pipeline).to_list(1)
    cert_agg = cert_res[0] if cert_res else {}
    
    # QC Reports Stats
    qc_pipeline = [
        {"$match": {"is_deleted": False, "created_at": {"$gte": start_date, "$lte": end_date}}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "created_today": [
                {"$match": {"created_at": {"$gte": today}}},
                {"$count": "count"}
            ],
            "created_in_period": [
                {"$match": {"created_at": {"$gte": start_date, "$lte": end_date}}},
                {"$count": "count"}
            ],
        }}
    ]
    qc_res = await db.qc_reports.aggregate(qc_pipeline).to_list(1)
    qc_agg = qc_res[0] if qc_res else {}
    
    # Clients Stats
    total_clients = await db.clients.count_documents({"is_deleted": False})
    
    # Manufacturers Stats
    total_manufacturers = await db.manufacturers.count_documents({"is_deleted": False})
    
    # Recent Activity (last 24 hours)
    recent_actions = await db.action_history.count_documents({
        "created_at": {"$gte": week_ago}
    })
    
    return {
        "time_period": time_period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "jobs": {
            "total": _get(job_agg.get("total", [])),
            "active": _get(job_agg.get("active", [])),
            "completed_today": jobs_completed_today,
            "completed_in_period": jobs_completed_in_period,
            "created_in_period": jobs_created_in_period,
            "completed_change": round(jobs_change, 1),
            "by_status": {d["_id"]: d["count"] for d in job_agg.get("by_status", [])},
            "pending_qc": _get(job_agg.get("pending_qc", [])),
            "pending_certification": _get(job_agg.get("pending_certification", [])),
            "in_progress_qc": _get(job_agg.get("in_progress_qc", [])),
            "in_progress_certification": _get(job_agg.get("in_progress_certification", [])),
        },
        "certificates": {
            "total": _get(cert_agg.get("total", [])),
            "created_today": _get(cert_agg.get("created_today", [])),
            "created_in_period": _get(cert_agg.get("created_in_period", [])),
            "pending_photo_edit": _get(cert_agg.get("pending_photo_edit", [])),
        },
        "qc_reports": {
            "total": _get(qc_agg.get("total", [])),
            "created_today": _get(qc_agg.get("created_today", [])),
            "created_in_period": _get(qc_agg.get("created_in_period", [])),
        },
        "clients": {
            "total": total_clients,
        },
        "manufacturers": {
            "total": total_manufacturers,
        },
        "activity": {
            "recent_actions": recent_actions,
        },
    }

