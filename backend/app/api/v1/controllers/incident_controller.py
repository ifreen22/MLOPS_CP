from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/incidents", tags=["Incidents"])

class IncidentIngest(BaseModel):
    organizationId: str
    serviceId: str
    assigneeId: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str = "OPEN"
    severity: str
    createdAt: Optional[datetime] = None

@router.post("/")
async def create_incident(payload: IncidentIngest):
    incident = await prisma.incident.create(
        data={
            "organizationId": payload.organizationId,
            "serviceId": payload.serviceId,
            "assigneeId": payload.assigneeId,
            "title": payload.title,
            "description": payload.description,
            "status": payload.status,
            "severity": payload.severity,
            "createdAt": payload.createdAt or datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
    )
    return incident

@router.get("/")
async def get_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    serviceId: Optional[str] = None
):
    where: dict[str, Any] = {}
    if serviceId:
        where["serviceId"] = serviceId
    if start_time or end_time:
        where["createdAt"] = {}
        if start_time:
            where["createdAt"]["gte"] = start_time
        if end_time:
            where["createdAt"]["lte"] = end_time

    return await prisma.incident.find_many(where=where, skip=skip, take=limit, order={"createdAt": "desc"})
