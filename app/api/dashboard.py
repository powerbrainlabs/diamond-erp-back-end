from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from ..core.dependencies import require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

def _get_period_start(time_period: str) -> datetime:
    now = datetime.utcnow()
    if time_period == "hourly":
        return now - timedelta(hours=1)
    elif time_period == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_period == "weekly":
        return now - timedelta(days=7)
    elif time_period == "monthly":
        return now - timedelta(days=30)
    elif time_period == "yearly":
        return now - timedelta(days=365)
    else:  # overall
        return datetime(2000, 1, 1)

@router.get("/stats")
async def dashboard_stats(time_period: str = "daily", current_user: dict = Depends(require_staff)):
    db = await get_db()
    period_start = _get_period_start(time_period)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # ---- Jobs ----
    jobs_pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "active": [
                {"$match": {"status": {"$ne": "completed"}}},
                {"$count": "count"}
            ],
            "by_status": [
                {"$group": {"_id": "$status", "count": {"$count": {}}}}
            ],
            "created_in_period": [
                {"$match": {"created_at": {"$gte": period_start}}},
                {"$count": "count"}
            ],
            "completed_in_period": [
                {"$match": {"status": "completed", "updated_at": {"$gte": period_start}}},
                {"$count": "count"}
            ],
            "completed_today": [
                {"$match": {"status": "completed", "updated_at": {"$gte": today}}},
                {"$count": "count"}
            ],
            "pending_qc": [
                {"$match": {"job_type": "qc_job", "status": {"$ne": "completed"}}},
                {"$count": "count"}
            ],
            "pending_certification": [
                {"$match": {"job_type": "certification_job", "status": {"$ne": "completed"}}},
                {"$count": "count"}
            ],
        }}
    ]
    jobs_res = await db.jobs.aggregate(jobs_pipeline).to_list(1)
    ja = jobs_res[0] if jobs_res else {}
    def _n(lst): return lst[0]["count"] if lst else 0

    # ---- Certificates ----
    certs_pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "created_in_period": [
                {"$match": {"created_at": {"$gte": period_start}}},
                {"$count": "count"}
            ],
            "created_today": [
                {"$match": {"created_at": {"$gte": today}}},
                {"$count": "count"}
            ],
            "pending_photo_edit": [
                {"$match": {"status": "pending_photo_edit"}},
                {"$count": "count"}
            ],
        }}
    ]
    certs_res = await db.certifications.aggregate(certs_pipeline).to_list(1)
    ca = certs_res[0] if certs_res else {}

    # ---- QC Reports ----
    qc_pipeline = [
        {"$match": {"is_deleted": False}},
        {"$facet": {
            "total": [{"$count": "count"}],
            "created_in_period": [
                {"$match": {"created_at": {"$gte": period_start}}},
                {"$count": "count"}
            ],
            "created_today": [
                {"$match": {"created_at": {"$gte": today}}},
                {"$count": "count"}
            ],
        }}
    ]
    qc_res = await db.qc_reports.aggregate(qc_pipeline).to_list(1)
    qa = qc_res[0] if qc_res else {}

    # ---- Clients & Manufacturers ----
    total_clients = await db.clients.count_documents({"is_deleted": False})
    total_manufacturers = await db.manufacturers.count_documents({"is_deleted": False})

    return {
        "jobs": {
            "active": _n(ja.get("active", [])),
            "by_status": {d["_id"]: d["count"] for d in ja.get("by_status", [])},
            "created_in_period": _n(ja.get("created_in_period", [])),
            "completed_in_period": _n(ja.get("completed_in_period", [])),
            "completed_today": _n(ja.get("completed_today", [])),
            "pending_qc": _n(ja.get("pending_qc", [])),
            "pending_certification": _n(ja.get("pending_certification", [])),
        },
        "certificates": {
            "total": _n(ca.get("total", [])),
            "created_in_period": _n(ca.get("created_in_period", [])),
            "created_today": _n(ca.get("created_today", [])),
            "pending_photo_edit": _n(ca.get("pending_photo_edit", [])),
        },
        "qc_reports": {
            "total": _n(qa.get("total", [])),
            "created_in_period": _n(qa.get("created_in_period", [])),
            "created_today": _n(qa.get("created_today", [])),
        },
        "clients": {
            "total": total_clients,
        },
        "manufacturers": {
            "total": total_manufacturers,
        },
        "time_period": time_period,
    }
