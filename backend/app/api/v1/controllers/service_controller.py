import re
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/services", tags=["Services"])

class ServiceIngest(BaseModel):
    organizationId: str
    clusterId: str
    name: str
    description: Optional[str] = None
    createdAt: Optional[datetime] = None

class ServiceTierUpdate(BaseModel):
    tier: str

@router.post("")
@router.post("/")
async def create_service(payload: ServiceIngest):
    service = await prisma.service.create(
        data={
            "organizationId": payload.organizationId,
            "clusterId": payload.clusterId,
            "name": payload.name,
            "description": payload.description,
            "createdAt": payload.createdAt or datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc)
        }
    )
    return service

@router.get("")
@router.get("/")
async def get_services(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    clusterId: Optional[str] = None
):
    where: dict[str, Any] = {}
    if clusterId:
        where["clusterId"] = clusterId
    if start_time or end_time:
        where["createdAt"] = {}
        if start_time:
            where["createdAt"]["gte"] = start_time
        if end_time:
            where["createdAt"]["lte"] = end_time

    return await prisma.service.find_many(where=where, skip=skip, take=limit, order={"createdAt": "desc"})

@router.patch("/{service_id}/tier")
async def update_service_tier(service_id: str, payload: ServiceTierUpdate):
    service = await prisma.service.find_unique(where={"id": service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    old_desc = service.description or ""
    if "[Tier:" in old_desc:
        new_desc = re.sub(r"\[Tier:[^\]]+\]", f"[Tier: {payload.tier}]", old_desc)
    else:
        new_desc = f"{old_desc} [Tier: {payload.tier}]".strip()
        
    return await prisma.service.update(
        where={"id": service_id},
        data={"description": new_desc, "updatedAt": datetime.now(timezone.utc)}
    )
