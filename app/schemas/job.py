from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date, datetime

ItemType = Literal["loose_diamond", "diamond", "jewelry", "gemstone"]


class JobItem(BaseModel):
    item_type: str
    weight: Optional[float] = None
    quantity: Optional[int] = None
Status = Literal["pending", "qc", "rfd", "photography", "certification", "completed"]
Priority = Literal["low", "medium", "high", "urgent"]


StageStatus = Literal["pending", "in_progress", "done"]


class JobCreate(BaseModel):
    client_id: str
    item_type: str
    item_description: str
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    expected_delivery_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    received_datetime: Optional[datetime] = None  # Alternative field name
    received_from_name: Optional[str] = None
    notes: Optional[str] = None
    # Optional fields from frontend
    manufacturer_id: Optional[str] = None
    job_type: Optional[str] = None
    item_quantity: Optional[int] = None
    item_weight: Optional[float] = None
    item_size: Optional[str] = None
    items: List[JobItem] = []

class JobResponse(BaseModel):
    uuid: str
    job_number: str
    item_type: str
    status: str
    work_progress: dict
    created_by: dict
    created_at: datetime

class JobUpdate(BaseModel):
    client_name: Optional[str] = Field(default=None, min_length=2)
    client_contact: Optional[str] = Field(default=None, min_length=10, max_length=15)
    item_type: Optional[str] = None
    item_description: Optional[str] = None
    status: Optional[Status] = None
    assigned_to: Optional[str] = None  # user_id
    priority: Optional[Priority] = None
    received_date: Optional[datetime] = None
    expected_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[datetime] = None
    received_from_name: Optional[str] = None
    notes: Optional[str] = None
    received_datetime: Optional[datetime] = None
    manufacturer_id: Optional[str] = None
    job_type: Optional[str] = None
    items: Optional[List[JobItem]] = None

class JobStatusPatch(BaseModel):
    status: Status
    assigned_to: Optional[str] = None
