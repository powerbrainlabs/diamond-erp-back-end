from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime, timedelta
from bson import ObjectId

from ..core.dependencies import require_admin, get_current_user, require_staff
from ..db.database import get_db
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/api/action-history", tags=["Action History"])

@router.get("")
async def list_action_history(
    current_user: dict = Depends(require_staff),
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    search: Optional[str] = None,
    time_range: Optional[Literal["hourly", "daily", "monthly", "yearly"]] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = "created_at",
    order: Literal["asc", "desc"] = "desc",
):
    """
    List action history
    - Admin can see all users' history
    - Staff can only see their own history
    """
    db = await get_db()
    
    query = {}
    
    # Staff can only see their own history
    if current_user.get("role") != "admin":
        try:
            query["user_id"] = ObjectId(current_user.get("id"))
        except:
            raise HTTPException(status_code=400, detail="Invalid user ID")
    # Admin can filter by user_id
    elif user_id:
        try:
            query["user_id"] = ObjectId(user_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid user ID")
    
    # Time range filter
    if time_range:
        now = datetime.utcnow()
        if time_range == "hourly":
            start_time = now - timedelta(hours=1)
        elif time_range == "daily":
            start_time = now - timedelta(days=1)
        elif time_range == "monthly":
            start_time = now - timedelta(days=30)
        elif time_range == "yearly":
            start_time = now - timedelta(days=365)
        query["created_at"] = {"$gte": start_time}
    
    if action_type:
        query["action_type"] = action_type
    
    if resource_type:
        query["resource_type"] = resource_type
    
    if search:
        query["$or"] = [
            {"details": {"$regex": search, "$options": "i"}},
            {"resource_id": {"$regex": search, "$options": "i"}},
        ]
    
    skip = (page - 1) * limit
    
    # Get total count
    total = await db.action_history.count_documents(query)
    
    # Build sort
    sort_direction = 1 if order == "asc" else -1
    sort_field = sort_by if sort_by in ["created_at", "action_type", "resource_type"] else "created_at"
    
    # Fetch history
    cursor = db.action_history.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
    history_list = await cursor.to_list(length=limit)
    
    # Get user names for display
    user_ids = [h.get("user_id") for h in history_list if h.get("user_id")]
    users = {}
    if user_ids:
        user_cursor = db.users.find({"_id": {"$in": user_ids}})
        user_list = await user_cursor.to_list(length=len(user_ids))
        users = {str(u["_id"]): u.get("name", "Unknown") for u in user_list}
    
    # Format results - serialize all ObjectIds and datetimes
    results = []
    for h in history_list:
        # Convert _id to id and serialize all ObjectIds/datetimes
        result = serialize_mongo_doc(dict(h))
        # Rename _id to id if it exists
        if "_id" in result:
            result["id"] = str(result.pop("_id"))
        # Add user_name
        user_id_str = str(h.get("user_id")) if h.get("user_id") else None
        result["user_name"] = users.get(user_id_str, "Unknown")
        results.append(result)
    
    return {
        "data": results,
        "total": total,
        "page": page,
        "total_pages": (total + limit - 1) // limit,
        "has_next": skip + limit < total,
        "has_prev": page > 1,
    }

@router.get("/stats")
async def get_action_history_stats(
    current_user: dict = Depends(require_admin),
):
    """Get action history statistics (admin only)"""
    db = await get_db()
    
    # Total actions
    total_actions = await db.action_history.count_documents({})
    
    # Actions by type
    pipeline = [
        {"$group": {"_id": "$action_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    actions_by_type = await db.action_history.aggregate(pipeline).to_list(length=100)
    
    # Actions by resource type
    pipeline = [
        {"$group": {"_id": "$resource_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    actions_by_resource = await db.action_history.aggregate(pipeline).to_list(length=100)
    
    # Recent activity (last 24 hours)
    from datetime import timedelta
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_actions = await db.action_history.count_documents({"created_at": {"$gte": yesterday}})
    
    return {
        "total_actions": total_actions,
        "recent_actions": recent_actions,
        "actions_by_type": {item["_id"]: item["count"] for item in actions_by_type},
        "actions_by_resource": {item["_id"]: item["count"] for item in actions_by_resource},
    }


@router.get("/test12")
async def get_action_history_stats():
    """Get action history statistics (admin only)"""
    return {"message": "Hello World"}
