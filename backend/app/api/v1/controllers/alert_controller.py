from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/alerts", tags=["Alerts"])

class AlertIngest(BaseModel):
    organizationId: str
    serviceId: str
    incidentId: Optional[str] = None
    title: str
    description: Optional[str] = None
    severity: str
    status: str = "OPEN"
    firedAt: Optional[datetime] = None

@router.post("/")
async def create_alert(payload: AlertIngest):
    alert = await prisma.alert.create(
        data={
            "organizationId": payload.organizationId,
            "serviceId": payload.serviceId,
            "incidentId": payload.incidentId,
            "title": payload.title,
            "description": payload.description,
            "severity": payload.severity,
            "status": payload.status,
            "firedAt": payload.firedAt or datetime.now(timezone.utc),
        }
    )
    return alert

@router.get("/")
async def get_alerts(
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
        where["firedAt"] = {}
        if start_time:
            where["firedAt"]["gte"] = start_time
        if end_time:
            where["firedAt"]["lte"] = end_time

    return await prisma.alert.find_many(where=where, skip=skip, take=limit, order={"firedAt": "desc"})
