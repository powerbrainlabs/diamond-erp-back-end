from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional
from datetime import datetime
import uuid


class ClientBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None

    @field_validator("email", mode="before")
    @classmethod
    def empty_email_to_none(cls, v):
        if isinstance(v, str) and v.strip() == "":
            return None
        return v
    phone: Optional[str] = Field(None, pattern=r"^[\+]?[0-9\s\-]{7,15}$")
    address: Optional[str] = None
    gst_number: Optional[str] = None
    notes: Optional[str] = None
    brand_logo_url: Optional[str] = None
    rear_logo_url: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientBase):
    name: Optional[str] = None


class ClientResponse(ClientBase):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_deleted: bool
    created_by: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
