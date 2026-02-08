from pydantic import BaseModel, Field
from typing import Optional, List


class CertificateTypeCreate(BaseModel):
    name: str = Field(min_length=2)
    slug: str = Field(min_length=2, pattern=r"^[a-z0-9_-]+$")
    description: Optional[str] = None
    icon: Optional[str] = "file-text"
    has_photo: bool = True
    has_logo: bool = True
    has_rear_logo: bool = True


class CertificateTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    has_photo: Optional[bool] = None
    has_logo: Optional[bool] = None
    has_rear_logo: Optional[bool] = None
    is_active: Optional[bool] = None


class ReorderTypesPayload(BaseModel):
    type_order: List[str]  # ordered list of type UUIDs
