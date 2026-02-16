from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class QCReportRow(BaseModel):
    clarity: Optional[str] = None
    color: Optional[str] = None
    sieveSize: Optional[str] = None
    weight: Optional[str] = None
    percent: Optional[str] = Field(None, alias="%")
    result: Optional[str] = None

class QCReportLot(BaseModel):
    lot: Optional[str] = None
    passPercent: Optional[str] = None
    rows: List[QCReportRow] = []
    totalWeight: Optional[str] = None
    totalPercent: Optional[str] = None

class QCReportCreate(BaseModel):
    job_id: str
    clientname: str
    phno: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    lotData: List[QCReportLot] = []
    summary_note: Optional[str] = None

class QCReportUpdate(BaseModel):
    clientname: Optional[str] = None
    phno: Optional[str] = None
    address: Optional[str] = None
    lotData: Optional[List[QCReportLot]] = None
    summary_note: Optional[str] = None
    status: Optional[str] = None
