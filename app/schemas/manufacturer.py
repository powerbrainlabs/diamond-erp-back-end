from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid


class ManufacturerBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^[0-9]{10}$")
    address: Optional[str] = None
    gst_number: Optional[str] = None
    notes: Optional[str] = None


class ManufacturerCreate(ManufacturerBase):
    pass


class ManufacturerUpdate(ManufacturerBase):
    name: Optional[str] = None


class ManufacturerResponse(ManufacturerBase):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_deleted: bool
    created_by: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

