from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DeploymentBase(BaseModel):
    version: str
    status: str
    environment: str
    service_id: int


class DeploymentCreate(DeploymentBase):
    pass


class DeploymentUpdate(BaseModel):
    status: Optional[str] = None
    environment: Optional[str] = None


class DeploymentResponse(DeploymentBase):
    id: int
    deployed_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
