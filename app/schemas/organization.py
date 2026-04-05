from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field


OrganizationStatus = Literal["active", "suspended"]


class OrganizationAdminCreate(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)


class OrganizationCreate(BaseModel):
    official_name: str = Field(min_length=2)
    display_name: Optional[str] = None
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_email: Optional[EmailStr] = None
    primary_phone: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    certificate_footer_text: Optional[str] = None
    report_signature_name: Optional[str] = None
    report_signature_title: Optional[str] = None
    default_timezone: str = "Asia/Kolkata"
    default_currency: str = "INR"
    status: OrganizationStatus = "active"
    admin: OrganizationAdminCreate


class OrganizationUpdate(BaseModel):
    official_name: Optional[str] = Field(default=None, min_length=2)
    display_name: Optional[str] = None
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_email: Optional[EmailStr] = None
    primary_phone: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    certificate_footer_text: Optional[str] = None
    report_signature_name: Optional[str] = None
    report_signature_title: Optional[str] = None
    default_timezone: Optional[str] = None
    default_currency: Optional[str] = None
    status: Optional[OrganizationStatus] = None


class OrganizationOut(BaseModel):
    id: str
    official_name: str
    display_name: str
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    primary_email: Optional[str] = None
    primary_phone: Optional[str] = None
    website: Optional[str] = None
    tax_id: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    certificate_footer_text: Optional[str] = None
    report_signature_name: Optional[str] = None
    report_signature_title: Optional[str] = None
    default_timezone: str
    default_currency: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime
