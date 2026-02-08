from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from .core.config import settings
from .db.database import init_db, get_db
from .core.minio_client import ensure_buckets
from .api.auth import router as auth_router
from .api.jobs import router as jobs_router
from .api.clients import router as client_router
from .api.files import router as files_router
from .api.certification import router as certification_router
from .api.categories import router as category_router
from .api.qc_reports import router as qc_reports_router
from .api.dashboard import router as dashboard_router
from .api.action_history import router as action_history_router
from .api.super_admin_categories import router as super_admin_categories_router
from .api.certificate_types import router as certificate_types_router

from .core.security import hash_password

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    db = await init_db()

    # Migration: rename legacy "staff" role to "user"
    await db.users.update_many({"role": "staff"}, {"$set": {"role": "user"}})

    # Seed super admin
    sa = await db.users.find_one({"email": settings.SUPER_ADMIN_EMAIL})
    if not sa:
        now = datetime.utcnow()
        await db.users.insert_one({
            "email": settings.SUPER_ADMIN_EMAIL,
            "password": hash_password(settings.SUPER_ADMIN_PASSWORD),
            "name": settings.SUPER_ADMIN_NAME,
            "role": "super_admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

    # Seed admin
    admin = await db.users.find_one({"email": settings.ADMIN_EMAIL})
    if not admin:
        now = datetime.utcnow()
        await db.users.insert_one({
            "email": settings.ADMIN_EMAIL,
            "password": hash_password(settings.ADMIN_PASSWORD),
            "name": settings.ADMIN_NAME,
            "role": "admin",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        })

    # Seed default certificate types if none exist
    from .utils.seed_schemas import seed_default_certificate_types
    await seed_default_certificate_types(db)

    # Seed default category schemas if none exist
    from .utils.seed_schemas import seed_default_category_schemas
    await seed_default_category_schemas(db)

    # Ensure MinIO buckets exist
    ensure_buckets()

# Routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(client_router)
app.include_router(files_router)
app.include_router(certification_router)
app.include_router(category_router)
app.include_router(qc_reports_router)
app.include_router(dashboard_router)
app.include_router(action_history_router)
app.include_router(super_admin_categories_router)
app.include_router(certificate_types_router)

@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "status": "ok"}