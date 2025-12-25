from fastapi import APIRouter, Depends, Query
from typing import Optional, List, Dict, Any
from ..core.dependencies import require_staff
from ..db.database import get_db
from ..utils.serializers import serialize_mongo_doc

router = APIRouter(prefix="/api/search", tags=["Search"])

@router.get("")
async def global_search(
    query: str = Query(..., min_length=2),
    current_user: dict = Depends(require_staff)
):
    db = await get_db()
    results = []

    # 1. Search Jobs
    job_filt = {
        "is_deleted": False,
        "$or": [
            {"job_number": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
            {"client_name": {"$regex": query, "$options": "i"}},
        ]
    }
    jobs = await db.jobs.find(job_filt).limit(5).to_list(None)
    for j in jobs:
        results.append({
            "type": "job",
            "id": j["uuid"],
            "title": j["job_number"],
            "subtitle": j.get("client_name", "N/A"),
            "description": j.get("description", ""),
            "url": f"/jobs?search={j['job_number']}"
        })

    # 2. Search Certifications
    cert_filt = {
        "is_deleted": False,
        "$or": [
            {"uuid": {"$regex": query, "$options": "i"}},
            {"type": {"$regex": query, "$options": "i"}},
            {"fields.certificate_no": {"$regex": query, "$options": "i"}},
            {"fields.certificate_number": {"$regex": query, "$options": "i"}},
        ]
    }
    certs = await db.certifications.find(cert_filt).limit(5).to_list(None)
    for c in certs:
        cert_no = c.get("fields", {}).get("certificate_no") or c.get("fields", {}).get("certificate_number") or c["uuid"][:8]
        results.append({
            "type": "certificate",
            "id": c["uuid"],
            "title": f"Cert: {cert_no}",
            "subtitle": c.get("type", "Certificate").capitalize(),
            "description": f"Type: {c.get('type')}",
            "url": f"/certificate/{c['uuid']}"
        })

    # 3. Search Clients
    client_filt = {
        "is_deleted": False,
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}},
            {"phone": {"$regex": query, "$options": "i"}},
        ]
    }
    clients = await db.clients.find(client_filt).limit(5).to_list(None)
    for c in clients:
        results.append({
            "type": "client",
            "id": c["uuid"],
            "title": c["name"],
            "subtitle": "Client",
            "description": f"{c.get('email', '')} | {c.get('phone', '')}",
            "url": f"/contacts?tab=clients&search={c['name']}"
        })

    # 4. Search Manufacturers
    manu_filt = {
        "is_deleted": False,
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"email": {"$regex": query, "$options": "i"}},
            {"phone": {"$regex": query, "$options": "i"}},
        ]
    }
    manus = await db.manufacturers.find(manu_filt).limit(5).to_list(None)
    for m in manus:
        results.append({
            "type": "manufacturer",
            "id": m["uuid"],
            "title": m["name"],
            "subtitle": "Manufacturer",
            "description": f"{m.get('email', '')} | {m.get('phone', '')}",
            "url": f"/contacts?tab=manufacturers&search={m['name']}"
        })

    return results
