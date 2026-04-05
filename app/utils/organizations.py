from datetime import datetime
from typing import Iterable

from bson import ObjectId


DEFAULT_COLLECTIONS: Iterable[str] = (
    "users",
    "jobs",
    "clients",
    "manufacturers",
    "certifications",
    "qc_reports",
    "photos",
    "files",
    "action_history",
)


def serialize_organization(doc: dict | None) -> dict | None:
    if not doc:
        return None

    payload = dict(doc)
    payload["id"] = str(payload.pop("_id"))
    payload["display_name"] = payload.get("display_name") or payload.get("official_name")
    return payload


async def ensure_default_organization(db, settings) -> dict:
    now = datetime.utcnow()
    org = await db.organizations.find_one({"slug": "gac"})

    if not org:
        doc = {
            "official_name": "GAC",
            "display_name": "GAC",
            "short_name": "GAC",
            "slug": "gac",
            "logo_url": "",
            "primary_email": settings.ADMIN_EMAIL,
            "primary_phone": "",
            "website": "",
            "tax_id": "",
            "address_line_1": "",
            "address_line_2": "",
            "city": "",
            "state": "",
            "country": "India",
            "postal_code": "",
            "certificate_footer_text": "",
            "report_signature_name": "",
            "report_signature_title": "",
            "default_timezone": "Asia/Kolkata",
            "default_currency": "INR",
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }
        res = await db.organizations.insert_one(doc)
        org = await db.organizations.find_one({"_id": res.inserted_id})

    default_org_id = org["_id"]

    for collection_name in DEFAULT_COLLECTIONS:
        collection = getattr(db, collection_name, None)
        if collection is None:
            continue
        await collection.update_many(
            {"organization_id": {"$exists": False}},
            {"$set": {"organization_id": default_org_id}},
        )

    return org


async def get_user_organization(db, user: dict) -> dict | None:
    organization_id = user.get("organization_id")
    if not organization_id:
        return None

    if isinstance(organization_id, str):
        organization_id = ObjectId(organization_id)

    return await db.organizations.find_one({"_id": organization_id})


def normalize_org_id(value):
    return value if isinstance(value, ObjectId) else ObjectId(str(value))
