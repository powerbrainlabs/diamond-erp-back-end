from fastapi import APIRouter, Depends
from datetime import datetime

from ..core.dependencies import require_admin, require_staff
from ..db.database import get_db

router = APIRouter(prefix="/api/management-settings", tags=["Management Settings"])

NATURAL_DIAMOND_KEY = "natural_diamond_defaults"


@router.get("/natural-diamond")
async def get_natural_diamond_defaults(
    current_user: dict = Depends(require_staff),
):
    db = await get_db()
    doc = await db.management_settings.find_one({"key": NATURAL_DIAMOND_KEY})
    if not doc:
        return {"hardness": "10", "ri": "2.417", "sg": "3.52"}
    return {"hardness": doc.get("hardness", "10"), "ri": doc.get("ri", "2.417"), "sg": doc.get("sg", "3.52")}


@router.put("/natural-diamond")
async def update_natural_diamond_defaults(
    payload: dict,
    current_user: dict = Depends(require_admin),
):
    hardness = str(payload.get("hardness", "10")).strip()
    ri = str(payload.get("ri", "2.417")).strip()
    sg = str(payload.get("sg", "3.52")).strip()

    db = await get_db()
    await db.management_settings.update_one(
        {"key": NATURAL_DIAMOND_KEY},
        {"$set": {"key": NATURAL_DIAMOND_KEY, "hardness": hardness, "ri": ri, "sg": sg, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"hardness": hardness, "ri": ri, "sg": sg}
