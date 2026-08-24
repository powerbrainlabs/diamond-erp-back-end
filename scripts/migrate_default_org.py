"""
Multi-tenant migration: create a "default" organization and backfill
organization_id on all pre-existing documents so nothing breaks after the
single-tenant -> multi-tenant switch.

Idempotent: safe to run multiple times. Only documents missing an
organization_id are touched. The platform super_admin (organization_id=None)
is intentionally left unassigned.

Usage:
    python scripts/migrate_default_org.py
"""
import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db

DEFAULT_ORG_SLUG = "default"

# Collections that carry tenant data and gain an organization_id.
TENANT_COLLECTIONS = [
    "clients",
    "jobs",
    "certifications",
    "category_schemas",
    "certificate_types",
    "attributes",
    "job_photos",
    "qc_reports",
    "manufacturers",
    "management_settings",
]

# Matches docs with no organization_id at all, or an explicit null.
_MISSING_ORG = {"$or": [{"organization_id": {"$exists": False}}, {"organization_id": None}]}


async def _get_or_create_default_org(db) -> str:
    org = await db.organizations.find_one({"slug": DEFAULT_ORG_SLUG})
    if org:
        print(f"[SKIP] Default organization already exists: {org['uuid']}")
        return org["uuid"]

    now = datetime.utcnow()
    org_uuid = str(uuid.uuid4())
    await db.organizations.insert_one({
        "uuid": org_uuid,
        "slug": DEFAULT_ORG_SLUG,
        "official_name": "Default Organization",
        "display_name": "Default Organization",
        "short_name": "Default",
        "logo_url": "",
        "card_logo_url": "",
        "primary_email": "",
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
    })
    print(f"[OK] Created default organization: {org_uuid}")
    return org_uuid


async def migrate():
    db = await get_db()
    org_uuid = await _get_or_create_default_org(db)

    for coll_name in TENANT_COLLECTIONS:
        coll = db[coll_name]
        result = await coll.update_many(_MISSING_ORG, {"$set": {"organization_id": org_uuid}})
        print(f"[OK] {coll_name}: assigned {result.modified_count} document(s) to default org")

    # Users: attach admins/staff to the default org; leave super_admins global.
    user_result = await db.users.update_many(
        {"role": {"$in": ["admin", "user"]}, **_MISSING_ORG},
        {"$set": {"organization_id": org_uuid}},
    )
    print(f"[OK] users: assigned {user_result.modified_count} admin/staff account(s) to default org")

    # Ensure any super_admin without the field has an explicit None (platform-level).
    sa_result = await db.users.update_many(
        {"role": "super_admin", "organization_id": {"$exists": False}},
        {"$set": {"organization_id": None}},
    )
    print(f"[OK] users: normalized {sa_result.modified_count} super_admin account(s) to platform-level")

    print("[DONE] Default-org migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
