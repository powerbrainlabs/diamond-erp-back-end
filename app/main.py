from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from .core.config import settings
from .db.database import init_db, get_db
from .api.auth import router as auth_router
from .api.jobs import router as jobs_router
from .api.clients import router as client_router
from .api.manufacturers import router as manufacturers_router
from .api.files import router as files_router
from .api.certification import router as certification_router
from .api.categories import router as category_router
from .api.qc_reports import router as qc_reports_router
from .api.staff import router as staff_router
from .api.action_history import router as action_history_router
from .api.dashboard import router as dashboard_router

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

# Routers
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(client_router)
app.include_router(manufacturers_router)
app.include_router(files_router)
app.include_router(certification_router)
app.include_router(category_router)
app.include_router(qc_reports_router)
app.include_router(staff_router)
app.include_router(action_history_router)
app.include_router(dashboard_router)

@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "status": "ok"}