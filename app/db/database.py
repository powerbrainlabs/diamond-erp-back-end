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

    # Jobs indexes
    await db.jobs.create_index([("job_number", ASCENDING)], unique=True)
    await db.jobs.create_index([("status", ASCENDING)])
    await db.jobs.create_index([("client_name", TEXT), ("item_description", TEXT)], name="client_item_text")
    await db.jobs.create_index([("created_at", DESCENDING)])
    await db.jobs.create_index([("assigned_to.user_id", ASCENDING)])
    await db.jobs.create_index([("created_by.user_id", ASCENDING)])

    # Tokens blacklist
    await db.tokens_blacklist.create_index([("jti", ASCENDING)], unique=True)

    # Category schemas indexes
    await db.category_schemas.create_index([("uuid", ASCENDING)], unique=True)
    await db.category_schemas.create_index([("group", ASCENDING)])
    await db.category_schemas.create_index([("is_deleted", ASCENDING), ("is_active", ASCENDING)])

    # Certificate types indexes
    await db.certificate_types.create_index([("uuid", ASCENDING)], unique=True)
    await db.certificate_types.create_index([("slug", ASCENDING)], unique=True)
    await db.certificate_types.create_index([("is_deleted", ASCENDING), ("is_active", ASCENDING)])

    return db
