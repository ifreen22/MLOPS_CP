from pydantic import BaseModel, Field, field_validator
from typing import Optional, Any, Literal
import re
from datetime import datetime


# Users
class UserBase(BaseModel):
    organizationId: str
    email: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: str = "VIEWER"


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=72)
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    role: Literal["ADMIN", "OPERATOR", "VIEWER"] = "VIEWER"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("A valid email address is required.")
        return normalized


class UserUpdate(BaseModel):
    email: Optional[str] = Field(default=None, min_length=3, max_length=254)
    firstName: Optional[str] = Field(default=None, max_length=100)
    lastName: Optional[str] = Field(default=None, max_length=100)
    role: Optional[Literal["ADMIN", "OPERATOR", "VIEWER"]] = None
    password: Optional[str] = Field(default=None, min_length=12, max_length=72)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
            raise ValueError("A valid email address is required.")
        return normalized


class UserResponse(UserBase):
    id: str
    isActive: bool = True
    createdAt: datetime
    updatedAt: datetime

    model_config = {"from_attributes": True}


# Organizations
class OrganizationBase(BaseModel):
    name: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: str
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


# Logs
class LogBase(BaseModel):
    serviceId: str
    level: str
    message: str
    metadata: Optional[Any] = None


class LogCreate(LogBase):
    pass


class LogResponse(LogBase):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True


# Metrics
class MetricBase(BaseModel):
    serviceId: str
    name: str
    value: float
    tags: Optional[Any] = None


class MetricCreate(MetricBase):
    pass


class MetricResponse(MetricBase):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True


# Traces
class TraceBase(BaseModel):
    serviceId: str
    traceId: str
    spanId: str
    parentSpanId: Optional[str] = None
    name: str
    durationMs: int
    status: str


class TraceCreate(TraceBase):
    pass


class TraceResponse(TraceBase):
    id: str
    timestamp: datetime

    class Config:
        from_attributes = True


# Playbooks
class PlaybookBase(BaseModel):
    organizationId: str
    name: str
    description: Optional[str] = None
    steps: Any


class PlaybookCreate(PlaybookBase):
    pass


class PlaybookResponse(PlaybookBase):
    id: str
    createdAt: datetime
    updatedAt: datetime

    class Config:
        from_attributes = True


# RiskScores
class RiskScoreBase(BaseModel):
    deploymentId: str
    score: float
    factors: Any


class RiskScoreCreate(RiskScoreBase):
    pass


class RiskScoreResponse(RiskScoreBase):
    id: str
    createdAt: datetime

    class Config:
        from_attributes = True


# Dashboard
class DashboardKPIs(BaseModel):
    total_incidents: int
    active_alerts: int
    system_health: float
    deployments_today: int
