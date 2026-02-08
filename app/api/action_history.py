from fastapi import APIRouter, Depends, Query
from typing import Optional
from ..core.dependencies import require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/action-history", tags=["Action History"])

@router.get("")
async def list_action_history(
    page: int = Query(1),
    limit: int = Query(10),
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    # In a real app, we'd have an 'actions' collection. 
    # For now, let's return an empty list or some mock data to avoid 404s.
    
    filt = {}
    total = await db.actions.count_documents(filt) if hasattr(db, "actions") else 0
    
    # Mock data if no collection exists yet
    if total == 0:
        return {
            "total": 0,
            "page": page,
            "limit": limit,
            "data": []
        }
        
    skip = (page - 1) * limit
    cursor = db.actions.find(filt).sort([("created_at", -1)]).skip(skip).limit(limit)
    items = [doc async for doc in cursor]
    # serialize items...
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "data": items
    }

@router.get("/stats")
async def action_history_stats(current_user: dict = Depends(require_staff)):
    return {"total_actions": 0}
