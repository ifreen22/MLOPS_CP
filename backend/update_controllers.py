import os

BASE_DIR = r"C:\Users\Ifreen\Downloads\MLOPS_CP\backend\app\api\v1\controllers"

controllers = {
    "metric_controller.py": """from fastapi import APIRouter, Query
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
""",
    "log_controller.py": """from fastapi import APIRouter, Query
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
""",
    "trace_controller.py": """from fastapi import APIRouter, Query
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
""",
    "incident_controller.py": """from fastapi import APIRouter, Query
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
""",
    "alert_controller.py": """from fastapi import APIRouter, Query
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
""",
    "deployment_controller.py": """from fastapi import APIRouter, Query
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
""",
    "service_controller.py": """from fastapi import APIRouter, Query
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
""",
    "topology_controller.py": """from fastapi import APIRouter, Query
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
    timestamp: Optional[datetime] = None

@router.post("/")
async def create_topology(payload: TopologyIngest):
    namespace = await prisma.namespace.create(
        data={
            "clusterId": payload.clusterId,
            "name": payload.namespaceName,
            "createdAt": payload.timestamp or datetime.now(timezone.utc)
        }
    )
    node = await prisma.node.create(
        data={
            "clusterId": payload.clusterId,
            "name": payload.nodeName,
            "status": payload.status,
            "cpuCores": 4,
            "memoryBytes": 8589934592,
            "createdAt": payload.timestamp or datetime.now(timezone.utc)
        }
    )
    pod = await prisma.pod.create(
        data={
            "namespaceId": namespace.id,
            "nodeId": node.id,
            "name": payload.podName,
            "status": payload.status,
            "createdAt": payload.timestamp or datetime.now(timezone.utc)
        }
    )
    return {"namespace": namespace, "node": node, "pod": pod}

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

    return {"nodes": nodes, "namespaces": namespaces, "pods": pods}
"""
}

for filename, content in controllers.items():
    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Controllers updated successfully.")
