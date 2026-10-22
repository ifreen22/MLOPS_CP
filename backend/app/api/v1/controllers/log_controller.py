from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/logs", tags=["Logs"])

class LogIngest(BaseModel):
    serviceId: str
    level: str
    message: str
    metadata: Optional[str] = None
    timestamp: Optional[datetime] = None

@router.post("/")
async def create_log(payload: LogIngest):
    log = await prisma.log.create(
        data={
            "serviceId": payload.serviceId,
            "level": payload.level,
            "message": payload.message,
            "metadata": payload.metadata,
            "timestamp": payload.timestamp or datetime.now(timezone.utc),
        }
    )
    return log

@router.get("/")
async def get_logs(
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

    return await prisma.log.find_many(where=where, skip=skip, take=limit, order={"timestamp": "desc"})
