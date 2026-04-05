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
    default_fields = {
        "official_name": "GAC",
        "display_name": "GAC",
        "short_name": "GAC",
        "slug": "gac",
        "logo_url": "/gemlogo.svg",
        "primary_email": settings.ADMIN_EMAIL,
        "primary_phone": "+91 98765 43210",
        "website": "https://staging.gac.powerbrainlabs.com",
        "tax_id": "GSTIN-PENDING",
        "address_line_1": "Power Brain Labs",
        "address_line_2": "Gem Certification Division",
        "city": "Kolkata",
        "state": "West Bengal",
        "country": "India",
        "postal_code": "700001",
        "certificate_footer_text": "Certified by GAC - Gem Socket Administration",
        "report_signature_name": "Authorized Signatory",
        "report_signature_title": "GAC Administration",
        "default_timezone": "Asia/Kolkata",
        "default_currency": "INR",
        "status": "active",
    }

    if not org:
        doc = {
            **default_fields,
            "created_at": now,
            "updated_at": now,
        }
        res = await db.organizations.insert_one(doc)
        org = await db.organizations.find_one({"_id": res.inserted_id})
    else:
        updates = {}
        for key, value in default_fields.items():
            if not org.get(key):
                updates[key] = value

        if updates:
            updates["updated_at"] = now
            await db.organizations.update_one({"_id": org["_id"]}, {"$set": updates})
            org = await db.organizations.find_one({"_id": org["_id"]})

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
