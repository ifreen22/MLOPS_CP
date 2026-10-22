from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    repo_url: Optional[str] = None
    cluster_id: Optional[int] = None


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repo_url: Optional[str] = None
    cluster_id: Optional[int] = None


class ServiceResponse(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
