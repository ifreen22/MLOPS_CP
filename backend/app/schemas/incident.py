from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    service_id: Optional[int] = None


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    service_id: Optional[int] = None


class IncidentResponse(IncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
