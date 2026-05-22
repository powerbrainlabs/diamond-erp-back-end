from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..core.dependencies import require_super_admin
from ..db.database import get_db

router = APIRouter(prefix="/api/orgs", tags=["OrgHeaderTemplate"])


class HeaderTemplatePayload(BaseModel):
    html: str = ""
    css: str = ""
    layout_config: Optional[Dict[str, Any]] = None


def _normalize_org_id(org_id: str):
    try:
        return ObjectId(org_id)
    except Exception:
        return org_id


@router.get("/{org_id}/header-template")
async def get_header_template(
    org_id: str,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()
    doc = await db.org_header_templates.find_one({"org_id": org_id})
    if not doc:
        return {"org_id": org_id, "html": "", "css": "", "layout_config": None}
    return {
        "org_id": org_id,
        "html": doc.get("html", ""),
        "css": doc.get("css", ""),
        "layout_config": doc.get("layout_config"),
        "updated_at": doc.get("updated_at", "").isoformat() if doc.get("updated_at") else None,
    }


@router.put("/{org_id}/header-template")
async def save_header_template(
    org_id: str,
    payload: HeaderTemplatePayload,
    current_user: dict = Depends(require_super_admin),
):
    db = await get_db()

    # Verify org exists
    org = await db.organizations.find_one({"_id": _normalize_org_id(org_id)})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    now = datetime.utcnow()
    await db.org_header_templates.update_one(
        {"org_id": org_id},
        {
            "$set": {
                "org_id": org_id,
                "html": payload.html,
                "css": payload.css,
                "layout_config": payload.layout_config,
                "updated_at": now,
            }
        },
        upsert=True,
    )
    return {"ok": True, "org_id": org_id, "updated_at": now.isoformat()}
