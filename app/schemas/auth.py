from pydantic import BaseModel, EmailStr, Field
from typing import Dict, List, Literal, Optional

Role = Literal["super_admin", "admin", "user"]

ROLE_HIERARCHY: Dict[str, int] = {
    "super_admin": 3,
    "admin": 2,
    "user": 1,
}

ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "super_admin": [
        "manage_categories", "manage_schemas", "manage_users",
        "manage_jobs", "manage_certs", "manage_clients",
        "view_action_history", "system_settings", "view_all",
    ],
    "admin": [
        "manage_users", "manage_jobs", "manage_certs",
        "manage_clients", "view_action_history", "view_all",
    ],
    "user": [
        "manage_certs", "manage_jobs", "view_own",
    ],
}

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=2)
    role: Role

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

class MeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

class RefreshRequest(BaseModel):
    refresh_token: str
