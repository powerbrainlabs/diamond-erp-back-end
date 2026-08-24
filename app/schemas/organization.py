from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal

OrgStatus = Literal["active", "suspended"]


class OrgAdminSpec(BaseModel):
    """First admin account provisioned alongside a new organization."""
    name: str = Field(min_length=2)
    email: EmailStr
    password: Optional[str] = None  # auto-generated when blank


class OrganizationBase(BaseModel):
    official_name: str = Field(min_length=1)
    display_name: Optional[str] = ""
    short_name: Optional[str] = ""
    logo_url: Optional[str] = ""
    card_logo_url: Optional[str] = ""
    primary_email: Optional[str] = ""
    primary_phone: Optional[str] = ""
    website: Optional[str] = ""
    tax_id: Optional[str] = ""
    address_line_1: Optional[str] = ""
    address_line_2: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    country: Optional[str] = "India"
    postal_code: Optional[str] = ""
    certificate_footer_text: Optional[str] = ""
    report_signature_name: Optional[str] = ""
    report_signature_title: Optional[str] = ""
    default_timezone: Optional[str] = "Asia/Kolkata"
    default_currency: Optional[str] = "INR"
    status: OrgStatus = "active"


class OrganizationCreate(OrganizationBase):
    admin: OrgAdminSpec


class OrganizationUpdate(BaseModel):
    official_name: Optional[str] = None
    display_name: Optional[str] = None
    short_name: Optional[str] = None
    logo_url: Optional[str] = None
    card_logo_url: Optional[str] = None
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
    default_timezone: Optional[str] = None
    default_currency: Optional[str] = None
    status: Optional[OrgStatus] = None


# Fields that make up the persisted organization document (excludes admin).
ORGANIZATION_FIELDS = tuple(OrganizationBase.model_fields.keys())
