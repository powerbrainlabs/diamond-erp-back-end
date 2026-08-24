from typing import Optional
from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from bson import ObjectId
from ..core.security import is_token_blacklisted
from ..core.config import settings
from ..db.database import get_db
from ..utils.serializers import dump_user, dump_organization

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def with_organization(user: dict) -> dict:
    """Attach the full organization object to a serialized user dict.

    The frontend (brand.js / organizationBranding.js) reads user.organization.
    Super admins are platform-level and have no organization.
    """
    org_id = user.get("organization_id")
    if not org_id:
        user["organization"] = None
        return user
    db = await get_db()
    org = await db.organizations.find_one({"uuid": org_id})
    user["organization"] = dump_organization(org) if org else None
    return user

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
    return await with_organization(dump_user(doc))

async def require_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Super admin privileges required")
    return current_user

async def require_admin_or_above(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user["role"] not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user

# Aliases for backward compatibility with existing routes
require_admin = require_admin_or_above

async def require_authenticated(current_user: dict = Depends(get_current_user)) -> dict:
    """Any logged-in user (super_admin, admin, or user) can access."""
    return current_user

# Alias: existing routes use require_staff
require_staff = require_authenticated


async def get_org_scope(
    organization_id: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
) -> Optional[str]:
    """Resolve the effective organization scope for a tenant-scoped request.

    - admin / user: always locked to their own organization_id.
    - super_admin (platform, no org): returns None (all orgs) unless an explicit
      `?organization_id=` is provided to act within one tenant.

    Routers use the returned scope to build Mongo filters:
        flt = {} if scope is None else {"organization_id": scope}
    and to stamp organization_id on created documents.
    """
    role = current_user.get("role")
    user_org = current_user.get("organization_id")
    if role == "super_admin":
        return organization_id  # None => unscoped (all orgs)
    return user_org


def org_filter(scope: Optional[str]) -> dict:
    """Build a Mongo filter fragment for the given org scope."""
    return {} if scope is None else {"organization_id": scope}