from fastapi import APIRouter, Depends, Query
from typing import Optional
from ..core.dependencies import require_staff, organization_filter
from ..db.database import get_db
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/api/action-history", tags=["Action History"])

@router.get("")
async def list_action_history(
    page: int = Query(1),
    limit: int = Query(10),
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    scope = organization_filter(current_user)
    filt = {"organization_id": scope.get("organization_id")}
    total = await db.action_history.count_documents(filt)

    if total == 0:
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "data": []
        }
        
    skip = (page - 1) * limit
    cursor = db.action_history.find(filt).sort([("created_at", -1)]).skip(skip).limit(limit)
    items = [serialize_mongo_doc(doc) async for doc in cursor]
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": items
    }

@router.get("/stats")
async def action_history_stats(current_user: dict = Depends(require_staff)):
    db = await get_db()
    scope = organization_filter(current_user)
    total = await db.action_history.count_documents({"organization_id": scope.get("organization_id")})
    return {"total_actions": total}
