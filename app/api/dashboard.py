from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from typing import Dict, Any

from ..core.dependencies import require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats(current_user: dict = Depends(require_staff)):
    """
    Get comprehensive dashboard statistics
    Aggregates data from jobs, certificates, QC reports, clients, etc.
    """
    db = await get_db()
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    week_ago = today - timedelta(days=7)
    
    # Jobs Stats
    job_pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "by_status": [{"$group": {"_id": "$status", "count": {"$sum": 1}}}],
            "active": [{"$match": {"status": {"$ne": "completed"}}}, {"$count": "count"}],
            "completed_today": [
                {"$match": {"status": "completed", "updated_at": {"$gte": today}}},
                {"$count": "count"}
            ],
            "completed_yesterday": [
                {"$match": {"status": "completed", "updated_at": {"$gte": yesterday, "$lt": today}}},
                {"$count": "count"}
            ],
            "pending_qa": [
                {"$match": {"work_progress.qa.status": "pending"}},
                {"$count": "count"}
            ],
            "in_photography": [
                {"$match": {"work_progress.photography.status": "in_progress"}},
                {"$count": "count"}
            ],
        }}
    ]
    job_res = await db.jobs.aggregate(job_pipeline).to_list(1)
    job_agg = job_res[0] if job_res else {}
    
    def _get(lst): return lst[0]["count"] if lst else 0
    
    jobs_completed_today = _get(job_agg.get("completed_today", []))
    jobs_completed_yesterday = _get(job_agg.get("completed_yesterday", []))
    jobs_change = 0
    if jobs_completed_yesterday > 0:
        jobs_change = ((jobs_completed_today - jobs_completed_yesterday) / jobs_completed_yesterday) * 100
    
    # Certificates Stats
    cert_pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "created_today": [
                {"$match": {"created_at": {"$gte": today}}},
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
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "created_today": [
                {"$match": {"created_at": {"$gte": today}}},
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
        "jobs": {
            "total": _get(job_agg.get("total", [])),
            "active": _get(job_agg.get("active", [])),
            "completed_today": jobs_completed_today,
            "completed_change": round(jobs_change, 1),
            "by_status": {d["_id"]: d["count"] for d in job_agg.get("by_status", [])},
            "pending_qc": _get(job_agg.get("pending_qa", [])),
            "in_photography": _get(job_agg.get("in_photography", [])),
        },
        "certificates": {
            "total": _get(cert_agg.get("total", [])),
            "created_today": _get(cert_agg.get("created_today", [])),
            "pending_photo_edit": _get(cert_agg.get("pending_photo_edit", [])),
        },
        "qc_reports": {
            "total": _get(qc_agg.get("total", [])),
            "created_today": _get(qc_agg.get("created_today", [])),
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

