from fastapi import APIRouter, Query
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(prefix="/topology", tags=["Topology"])

class TopologyIngest(BaseModel):
    clusterId: str
    namespaceName: str
    nodeName: str
    podName: str
    status: str
    cpuCores: Optional[int] = None
    memoryBytes: Optional[int] = None
    timestamp: Optional[datetime] = None

@router.post("")
@router.post("/")
async def create_topology(payload: TopologyIngest):
    timestamp = payload.timestamp or datetime.now(timezone.utc)
    namespace = await prisma.namespace.find_first(
        where={"clusterId": payload.clusterId, "name": payload.namespaceName}
    )
    if namespace is None:
        namespace = await prisma.namespace.create(
            data={
                "clusterId": payload.clusterId,
                "name": payload.namespaceName,
                "createdAt": timestamp,
            }
        )

    node = await prisma.node.find_first(
        where={"clusterId": payload.clusterId, "name": payload.nodeName}
    )
    if node is None:
        node = await prisma.node.create(
            data={
                "clusterId": payload.clusterId,
                "name": payload.nodeName,
                "status": payload.status,
                "cpuCores": payload.cpuCores,
                "memoryBytes": payload.memoryBytes,
                "createdAt": timestamp,
            }
        )
    elif payload.cpuCores is not None or payload.memoryBytes is not None:
        node_data = {"status": payload.status}
        if payload.cpuCores is not None:
            node_data["cpuCores"] = payload.cpuCores
        if payload.memoryBytes is not None:
            node_data["memoryBytes"] = payload.memoryBytes
        node = await prisma.node.update(
            where={"id": node.id},
            data=node_data,
        )

    pod = await prisma.pod.find_first(
        where={
            "namespaceId": namespace.id,
            "nodeId": node.id,
            "name": payload.podName,
        }
    )
    if pod is None:
        pod = await prisma.pod.create(
            data={
                "namespaceId": namespace.id,
                "nodeId": node.id,
                "name": payload.podName,
                "status": payload.status,
                "createdAt": timestamp,
            }
        )
    else:
        pod = await prisma.pod.update(
            where={"id": pod.id},
            data={"status": payload.status},
        )
    return {"namespace": namespace, "node": node, "pod": pod}

@router.get("")
@router.get("/")
async def get_topology(
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

    nodes = await prisma.node.find_many(where=where, skip=skip, take=limit)
    namespaces = await prisma.namespace.find_many(where=where, skip=skip, take=limit)
    pods = await prisma.pod.find_many(skip=skip, take=limit)
    services = await prisma.service.find_many(where=where, include={"pods": True}, skip=skip, take=limit)

    return {"nodes": nodes, "namespaces": namespaces, "pods": pods, "services": services}
