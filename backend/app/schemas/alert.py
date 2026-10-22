from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertBase(BaseModel):
    title: str
    message: str
    severity: str
    source: str
    service_id: Optional[int] = None
    incident_id: Optional[int] = None


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseModel):
    title: Optional[str] = None
    message: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None


class AlertResponse(AlertBase):
    id: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
