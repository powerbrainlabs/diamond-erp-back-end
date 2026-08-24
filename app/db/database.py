from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT
from ..core.config import settings

_client: Optional[AsyncIOMotorClient] = None

def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _client

async def get_db():
    return get_client()[settings.DATABASE_NAME]

async def init_db():
    db = await get_db()

    # Users indexes
    await db.users.create_index([("email", ASCENDING)], unique=True)
    await db.users.create_index([("role", ASCENDING)])
    await db.users.create_index([("organization_id", ASCENDING)])

    # Organizations indexes
    await db.organizations.create_index([("uuid", ASCENDING)], unique=True)
    await db.organizations.create_index([("status", ASCENDING)])

    # Jobs indexes
    await db.jobs.create_index([("job_number", ASCENDING)], unique=True)
    await db.jobs.create_index([("status", ASCENDING)])
    await db.jobs.create_index([("client_name", TEXT), ("item_description", TEXT)], name="client_item_text")
    await db.jobs.create_index([("created_at", DESCENDING)])
    await db.jobs.create_index([("assigned_to.user_id", ASCENDING)])
    await db.jobs.create_index([("created_by.user_id", ASCENDING)])
    await db.jobs.create_index([("organization_id", ASCENDING)])

    # Tokens blacklist
    await db.tokens_blacklist.create_index([("jti", ASCENDING)], unique=True)

    # Category schemas indexes
    await db.category_schemas.create_index([("uuid", ASCENDING)], unique=True)
    await db.category_schemas.create_index([("group", ASCENDING)])
    await db.category_schemas.create_index([("is_deleted", ASCENDING), ("is_active", ASCENDING)])

    # Certificate types indexes
    await db.certificate_types.create_index([("uuid", ASCENDING)], unique=True)
    # Slug is unique per organization (multi-tenant). Drop the legacy global-unique
    # slug index if it exists, then create the compound unique index.
    try:
        await db.certificate_types.drop_index("slug_1")
    except Exception:
        pass
    await db.certificate_types.create_index(
        [("organization_id", ASCENDING), ("slug", ASCENDING)],
        unique=True,
        name="org_slug_unique",
    )
    await db.certificate_types.create_index([("is_deleted", ASCENDING), ("is_active", ASCENDING)])

    # Certifications indexes
    await db.certifications.create_index([("uuid", ASCENDING)], unique=True)
    # Certificate numbers are unique per organization (multi-tenant). Drop the
    # legacy global-unique index if present, then create the compound index.
    try:
        await db.certifications.drop_index("certificate_number_1")
    except Exception:
        pass
    await db.certifications.create_index(
        [("organization_id", ASCENDING), ("certificate_number", ASCENDING)],
        unique=True,
        partialFilterExpression={"certificate_number": {"$type": "string"}},
        name="org_certificate_number_unique",
    )
    await db.certifications.create_index([("client_id", ASCENDING)])
    await db.certifications.create_index([("category_id", ASCENDING)])
    await db.certifications.create_index([("created_at", DESCENDING)])
    await db.certifications.create_index([("is_deleted", ASCENDING)])
    await db.certifications.create_index([("organization_id", ASCENDING)])

    # Tenant-scoping indexes on shared collections
    await db.category_schemas.create_index([("organization_id", ASCENDING)])
    await db.certificate_types.create_index([("organization_id", ASCENDING)])
    await db.attributes.create_index([("organization_id", ASCENDING)])
    await db.clients.create_index([("organization_id", ASCENDING)])

    # Certificate counters - no index needed (_id is already unique by default)

    # Attributes (for certificate field dropdowns)
    await db.attributes.create_index([("uuid", ASCENDING)], unique=True)
    await db.attributes.create_index([("group", ASCENDING), ("type", ASCENDING)])
    await db.attributes.create_index([("is_deleted", ASCENDING)])

    return db
