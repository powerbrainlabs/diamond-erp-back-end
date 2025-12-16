from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from pydantic import EmailStr
from jose import JWTError, jwt
from bson import ObjectId

from ..schemas.auth import RegisterRequest, TokenResponse, MeUpdate, ChangePasswordRequest, RefreshRequest
from ..core.dependencies import get_current_user, require_admin
from ..core.security import hash_password, verify_password, create_access_token, create_refresh_token, blacklist_token
from ..core.config import settings
from ..db.database import get_db
from ..utils.serializers import dump_user
from ..utils.action_logger import auto_log_action
from fastapi import Request

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/register")
async def register_user(payload: RegisterRequest,
                        #  _: dict = Depends(require_admin)
                         ):
    db = await get_db()
    if await db.users.find_one({"email": payload.email}):
        raise HTTPException(status_code=409, detail="Email already exists")
    now = datetime.utcnow()
    doc = {
        "email": payload.email,
        "password": hash_password(payload.password),
        "name": payload.name,
        "role": payload.role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    res = await db.users.insert_one(doc)
    created = await db.users.find_one({"_id": res.inserted_id})
    return dump_user(created)

@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), request: Request = None):
    from email_validator import validate_email, EmailNotValidError

    db = await get_db()
    try:
        normalized = validate_email(form.username, check_deliverability=False).normalized
    except EmailNotValidError:
        raise HTTPException(status_code=400, detail="Invalid email format")

    user = await db.users.find_one({"email": normalized})
    if not user or not verify_password(form.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access = create_access_token(str(user["_id"]), user["email"], user["role"])
    refresh = create_refresh_token(str(user["_id"]), user["email"], user["role"])
    
    # Note: Login is a public endpoint, so auto_log_action can't be used here
    # We'll log it manually for now, or you can add it to a middleware
    from ..utils.action_logger import log_action
    await log_action(
        user_id=str(user["_id"]),
        action_type="login",
        resource_type="auth",
        details=f"User logged in: {user.get('name', normalized)}",
        ip_address=request.client.host if request and request.client else None,
    )
    
    return TokenResponse(
        access_token=access["token"],
        refresh_token=refresh["token"],
        expires_in=int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
        user=dump_user(user),
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(payload: RefreshRequest):
    try:
        data = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    if data.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")
    access = create_access_token(data["sub"], data["email"], data["role"])
    refresh = create_refresh_token(data["sub"], data["email"], data["role"])

    db = await get_db()
    user = await db.users.find_one({"_id": ObjectId(data["sub"])})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return TokenResponse(
        access_token=access["token"],
        refresh_token=refresh["token"],
        expires_in=int(timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES).total_seconds()),
        user=dump_user(user),
    )

@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

@router.put("/me")
async def update_me(payload: MeUpdate, current_user: dict = Depends(get_current_user)):
    db = await get_db()
    updates = {}
    if payload.name:
        updates["name"] = payload.name
    if not updates:
        return current_user
    updates["updated_at"] = datetime.utcnow()
    await db.users.update_one({"_id": ObjectId(current_user["id"])}, {"$set": updates})
    doc = await db.users.find_one({"_id": ObjectId(current_user["id"])})
    return dump_user(doc)

@router.post("/change-password")
async def change_password(payload: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    db = await get_db()
    doc = await db.users.find_one({"_id": ObjectId(current_user["id"])})
    if not verify_password(payload.current_password, doc["password"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    await db.users.update_one({"_id": doc["_id"]}, {"$set": {"password": hash_password(payload.new_password), "updated_at": datetime.utcnow()}})
    return {"detail": "Password updated"}

@router.post("/logout/refresh")
async def logout_refresh(payload: RefreshRequest):
    try:
        data = jwt.decode(payload.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid refresh token")
    if data.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Invalid token type")
    await blacklist_token(data["jti"], exp=datetime.utcfromtimestamp(data["exp"]))
    return {"detail": "Logged out"}
