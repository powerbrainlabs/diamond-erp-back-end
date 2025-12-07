from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from bson import ObjectId
from ..core.security import is_token_blacklisted
from ..core.config import settings
from ..db.database import get_db
from ..utils.serializers import dump_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise credentials_exception

    if await is_token_blacklisted(payload.get("jti", "")):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    db = await get_db()
    doc = await db.users.find_one({"_id": ObjectId(user_id), "is_active": True})
    if not doc:
        raise credentials_exception
    return dump_user(doc)

async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

async def require_staff(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] not in ("admin", "staff"):
        raise HTTPException(status_code=403, detail="Staff privileges required")
    return current_user