from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional

Role = Literal["admin", "staff"]

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
