from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/metrics", tags=["Metrics"])

class MetricIngest(BaseModel):
    serviceId: str
    name: str
    value: float
    tags: Optional[str] = None
    timestamp: Optional[datetime] = None

@router.post("/")
async def create_metric(payload: MetricIngest):
    metric = await prisma.metric.create(
        data={
            "serviceId": payload.serviceId,
            "name": payload.name,
            "value": payload.value,
            "tags": payload.tags,
            "timestamp": payload.timestamp or datetime.now(timezone.utc),
        }
    )
    return metric

@router.get("/")
async def get_metrics(
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
        where["timestamp"] = {}
        if start_time:
            where["timestamp"]["gte"] = start_time
        if end_time:
            where["timestamp"]["lte"] = end_time
            
    return await prisma.metric.find_many(where=where, skip=skip, take=limit, order={"timestamp": "desc"})
