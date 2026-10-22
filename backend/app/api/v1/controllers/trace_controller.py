from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/traces", tags=["Traces"])

class TraceIngest(BaseModel):
    serviceId: str
    traceId: str
    spanId: str
    parentSpanId: Optional[str] = None
    name: str
    durationMs: int
    status: str
    timestamp: Optional[datetime] = None

@router.post("/")
async def create_trace(payload: TraceIngest):
    trace = await prisma.trace.create(
        data={
            "serviceId": payload.serviceId,
            "traceId": payload.traceId,
            "spanId": payload.spanId,
            "parentSpanId": payload.parentSpanId,
            "name": payload.name,
            "durationMs": payload.durationMs,
            "status": payload.status,
            "timestamp": payload.timestamp or datetime.now(timezone.utc),
        }
    )
    return trace

@router.get("/")
async def get_traces(
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

    return await prisma.trace.find_many(where=where, skip=skip, take=limit, order={"timestamp": "desc"})
