"""
Utility for logging user actions to action_history collection
"""
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from bson import ObjectId
from fastapi import Request, Depends, BackgroundTasks
from ..db.database import get_db
from ..core.dependencies import get_current_user

async def log_action(
    user_id: str,
    action_type: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
):
    """
    Log a user action to the action_history collection
    
    Args:
        user_id: ID of the user performing the action
        action_type: Type of action (create, update, delete, view, login, logout, etc.)
        resource_type: Type of resource (job, client, certificate, qc_report, etc.)
        resource_id: ID of the resource (optional)
        details: Human-readable description of the action
        metadata: Additional data about the action (optional)
        ip_address: IP address of the user (optional)
    """
    try:
        db = await get_db()
        
        # Convert user_id to ObjectId if it's a string
        if isinstance(user_id, str):
            try:
                user_id = ObjectId(user_id)
            except:
                return  # Invalid user_id, skip logging
        
        action_doc = {
            "user_id": user_id,
            "action_type": action_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or f"{action_type} {resource_type}",
            "metadata": metadata or {},
            "ip_address": ip_address,
            "created_at": datetime.utcnow(),
        }
        
        await db.action_history.insert_one(action_doc)
    except Exception as e:
        # Don't fail the request if logging fails
        print(f"Failed to log action: {e}")

class ActionLogger:
    """
    Dependency-injected action logger that automatically captures user context
    """
    def __init__(self, current_user: dict, request: Optional[Request] = None):
        self.user_id = current_user.get("id")
        self.user_name = current_user.get("name", "Unknown")
        self.ip_address = request.client.host if request and request.client else None
    
    async def log(
        self,
        action_type: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log an action with automatic user context"""
        await log_action(
            user_id=self.user_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            metadata=metadata,
            ip_address=self.ip_address,
        )

async def auto_log_action(
    request: Request,
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """
    Automatic action logging dependency - no logic needed in routes!
    Automatically captures: endpoint, method, path params, query params, user info, IP
    
    Usage:
        from ..utils.action_logger import auto_log_action
        from ..core.dependencies import require_staff
        
        @router.post("/jobs")
        async def create_job(
            payload: JobCreate,
            current_user: dict = Depends(require_staff),
            _: None = Depends(auto_log_action),  # Just add this line - that's it!
        ):
            # Your normal route logic - no logging code needed!
            return result
    """
    # Extract endpoint info
    method = request.method
    path = request.url.path
    endpoint = f"{method} {path}"
    
    # Get path parameters (from URL path like /jobs/{uuid})
    path_params = dict(request.path_params) if hasattr(request, "path_params") else {}
    resource_id = None
    if path_params:
        # Try to get UUID or ID from path params
        resource_id = (
            path_params.get("uuid") 
            or path_params.get("id") 
            or path_params.get("staff_id") 
            or path_params.get("cert_uuid")
            or path_params.get("client_id")
        )
    
    # Get query parameters
    query_params = dict(request.query_params)
    
    # Determine action type and resource type from path
    action_type = "unknown"
    resource_type = "unknown"
    
    # Parse path to determine resource type
    path_parts = [p for p in path.strip("/").split("/") if p]
    if path_parts:
        # Remove API prefix if present
        if path_parts[0] == "api":
            path_parts = path_parts[1:]
        
        # Get resource type (usually the first part after /api)
        if path_parts:
            resource_type = path_parts[0].rstrip("s")  # Remove plural (jobs -> job)
            # If we have a UUID/id in path and not in path_params, use it
            if len(path_parts) > 1 and not resource_id:
                potential_id = path_parts[-1]
                if len(potential_id) > 10:  # Likely a UUID
                    resource_id = potential_id
    
    # Map HTTP methods to action types
    if method == "POST":
        action_type = "create"
    elif method in ["PUT", "PATCH"]:
        action_type = "update"
    elif method == "DELETE":
        action_type = "delete"
    elif method == "GET":
        action_type = "view"
    
    # Create details
    details = f"{method} {path}"
    if query_params:
        details += f" with query params"
    
    # Log in background (non-blocking) - runs after response is sent
    if background_tasks:
        background_tasks.add_task(
            log_action,
            user_id=current_user.get("id"),
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            metadata={
                "endpoint": endpoint,
                "method": method,
                "path": path,
                "path_params": path_params,
                "query_params": query_params,
                "user_name": current_user.get("name"),
                "user_email": current_user.get("email"),
            },
            ip_address=request.client.host if request.client else None,
        )
    
    # Return None so it doesn't affect route function
    return None
