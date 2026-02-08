from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from ..core.dependencies import require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
async def dashboard_stats(time_period: str = "daily", current_user: dict = Depends(require_staff)):
    db = await get_db()
    
    # Simple summary for the dashboard cards
    # This could aggregate data from Multiple collections
    
    # 1. Total Jobs
    total_jobs = await db.jobs.count_documents({"is_deleted": False})
    
    # 2. Active Jobs
    active_jobs = await db.jobs.count_documents({"is_deleted": False, "status": {"$ne": "completed"}})
    
    # 3. Today's Certifications
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_certs = await db.certifications.count_documents({"is_deleted": False, "created_at": {"$gte": today}})
    
    # 4. Pending QC Reports
    pending_qc = await db.qc_reports.count_documents({"is_deleted": False, "status": "draft"})
    
    return {
        "summary": {
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "today_certifications": today_certs,
            "pending_qc_reports": pending_qc
        },
        "time_period": time_period
    }
