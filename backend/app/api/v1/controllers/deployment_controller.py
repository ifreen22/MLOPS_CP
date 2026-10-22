from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/deployments", tags=["Deployments"])

class DeploymentIngest(BaseModel):
    serviceId: str
    version: str
    status: str = "PENDING"
    deployedAt: Optional[datetime] = None
    createdAt: Optional[datetime] = None

@router.post("/")
async def create_deployment(payload: DeploymentIngest):
    deployment = await prisma.deployment.create(
        data={
            "serviceId": payload.serviceId,
            "version": payload.version,
            "status": payload.status,
            "deployedAt": payload.deployedAt,
            "createdAt": payload.createdAt or datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
    )
    return deployment

@router.get("/")
async def get_deployments(
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

    return await prisma.deployment.find_many(where=where, skip=skip, take=limit, order={"createdAt": "desc"})
