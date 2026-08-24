from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db.database import get_db
from ..core.dependencies import require_super_admin, get_current_user

router = APIRouter(prefix="/api/orgs", tags=["Organization Templates"])


class HeaderTemplatePayload(BaseModel):
    html: Optional[str] = None
    css: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None


async def _get_org_or_404(db, organization_id: str) -> dict:
    org = await db.organizations.find_one({"uuid": organization_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.get("/{organization_id}/header-template")
async def get_header_template(
    organization_id: str,
    current_user: dict = Depends(get_current_user),
):
    db = await get_db()
    org = await _get_org_or_404(db, organization_id)
    # Non-super-admins may only read their own organization's template.
    if current_user.get("role") != "super_admin" and current_user.get("organization_id") != organization_id:
        raise HTTPException(status_code=403, detail="Not permitted for this organization")
    return org.get("header_template") or {}


@router.put("/{organization_id}/header-template")
async def save_header_template(
    organization_id: str,
    payload: HeaderTemplatePayload,
    _: dict = Depends(require_super_admin),
):
    db = await get_db()
    await _get_org_or_404(db, organization_id)
    template = payload.model_dump(exclude_none=True)
    await db.organizations.update_one(
        {"uuid": organization_id},
        {"$set": {"header_template": template, "updated_at": datetime.utcnow()}},
    )
    return template
