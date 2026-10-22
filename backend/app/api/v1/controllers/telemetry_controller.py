from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.core.db import prisma

router = APIRouter(tags=["Telemetry"])


# --- SCHEMAS ---
class MetricIngest(BaseModel):
    serviceId: str
    name: str
    value: float
    tags: Optional[str] = None
    timestamp: Optional[datetime] = None


class LogIngest(BaseModel):
    serviceId: str
    level: str
    message: str
    metadata: Optional[str] = None
    timestamp: Optional[datetime] = None


class TraceIngest(BaseModel):
    serviceId: str
    traceId: str
    spanId: str
    name: str
    durationMs: int
    status: str


# --- INGESTION ENDPOINTS (POST) ---
@router.post("/metrics")
async def ingest_metric(payload: MetricIngest):
    metric = await prisma.metric.create(
        data={
            "serviceId": payload.serviceId,
            "name": payload.name,
            "value": payload.value,
            "tags": payload.tags,
            "timestamp": payload.timestamp or datetime.utcnow(),
        }
    )
    return {"status": "success", "id": metric.id}


@router.post("/logs")
async def ingest_log(payload: LogIngest):
    log = await prisma.log.create(
        data={
            "serviceId": payload.serviceId,
            "level": payload.level,
            "message": payload.message,
            "metadata": payload.metadata,
            "timestamp": payload.timestamp or datetime.utcnow(),
        }
    )
    return {"status": "success", "id": log.id}


@router.post("/traces")
async def ingest_trace(payload: TraceIngest):
    trace = await prisma.trace.create(
        data={
            "serviceId": payload.serviceId,
            "traceId": payload.traceId,
            "spanId": payload.spanId,
            "name": payload.name,
            "durationMs": payload.durationMs,
            "status": payload.status,
            "timestamp": datetime.utcnow(),
        }
    )
    return {"status": "success", "id": trace.id}


# --- CONSUMPTION ENDPOINTS (GET) ---
@router.get("/metrics")
async def get_metrics(
    serviceId: Optional[str] = None,
    name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    where = {}
    if serviceId:
        where["serviceId"] = serviceId
    if name:
        where["name"] = name
    if start_time or end_time:
        where["timestamp"] = {}
        if start_time:
            where["timestamp"]["gte"] = start_time
        if end_time:
            where["timestamp"]["lte"] = end_time

    return await prisma.metric.find_many(
        where=where, skip=skip, take=limit, order={"timestamp": "desc"}
    )


@router.get("/logs")
async def get_logs(
    serviceId: Optional[str] = None,
    level: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    where = {}
    if serviceId:
        where["serviceId"] = serviceId
    if level:
        where["level"] = level
    if start_time or end_time:
        where["timestamp"] = {}
        if start_time:
            where["timestamp"]["gte"] = start_time
        if end_time:
            where["timestamp"]["lte"] = end_time

    return await prisma.log.find_many(
        where=where, skip=skip, take=limit, order={"timestamp": "desc"}
    )


@router.get("/traces")
async def get_traces(
    serviceId: Optional[str] = None,
    traceId: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    where = {}
    if serviceId:
        where["serviceId"] = serviceId
    if traceId:
        where["traceId"] = traceId
    if start_time or end_time:
        where["timestamp"] = {}
        if start_time:
            where["timestamp"]["gte"] = start_time
        if end_time:
            where["timestamp"]["lte"] = end_time

    return await prisma.trace.find_many(
        where=where, skip=skip, take=limit, order={"timestamp": "desc"}
    )


@router.get("/alerts")
async def get_alerts(
    serviceId: Optional[str] = None,
    severity: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    where = {}
    if serviceId:
        where["serviceId"] = serviceId
    if severity:
        where["severity"] = severity
    if start_time or end_time:
        where["firedAt"] = {}
        if start_time:
            where["firedAt"]["gte"] = start_time
        if end_time:
            where["firedAt"]["lte"] = end_time

    alerts = await prisma.alert.find_many(
        where=where,
        skip=skip,
        take=limit,
        order={"firedAt": "desc"},
        include={"service": True},
    )
    severity_map = {
        "critical": "sev1",
        "sev1": "sev1",
        "high": "sev2",
        "sev2": "sev2",
        "medium": "sev3",
        "warning": "sev3",
        "sev3": "sev3",
    }
    return [
        {
            "id": alert.id,
            "timestamp": alert.firedAt.isoformat(),
            "severity": severity_map.get(str(alert.severity).lower(), "info"),
            "engine": "database",
            "service": alert.service.name if alert.service else alert.serviceId,
            "message": alert.description or alert.title,
            "clusterTarget": alert.incidentId,
        }
        for alert in alerts
    ]


@router.get("/changes")
async def get_change_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    events = await prisma.k8sevent.find_many(
        skip=skip,
        take=limit,
        order={"timestamp": "desc"},
    )
    return [
        {
            "id": event.id,
            "timestamp": event.timestamp.isoformat(),
            "service": event.involvedObject,
            "type": "deployment" if "deploy" in event.reason.lower() else "config" if "config" in event.reason.lower() else "infra",
            "versionDelta": f"{event.reason}: {event.message}",
            "author": f"Kubernetes · {event.namespace}",
        }
        for event in events
    ]


@router.get("/incidents")
async def get_incidents(
    serviceId: Optional[str] = None,
    status: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
):
    where = {}
    if serviceId:
        where["serviceId"] = serviceId
    if status:
        where["status"] = status
    if start_time or end_time:
        where["createdAt"] = {}
        if start_time:
            where["createdAt"]["gte"] = start_time
        if end_time:
            where["createdAt"]["lte"] = end_time

    return await prisma.incident.find_many(
        where=where,
        skip=skip,
        take=limit,
        order={"createdAt": "desc"},
        include={"alerts": True, "service": True},
    )


@router.get("/topology")
async def get_topology(clusterId: Optional[str] = None):
    where = {}
    if clusterId:
        where["clusterId"] = clusterId
    services = await prisma.service.find_many(where=where, include={"pods": True})
    nodes = await prisma.node.find_many(where=where)

    return {"nodes": nodes, "services": services}

# --- LIVE SYSTEM TELEMETRY ENDPOINTS ---
from app.telemetry.collectors import get_collector
import traceback
from fastapi import HTTPException

def safe_collect(method_name):
    collector = get_collector()
    if hasattr(collector, method_name):
        try:
            return getattr(collector, method_name)()
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail='Not supported on this OS')

@router.get("/cpu")
async def get_cpu_live():
    return safe_collect('get_cpu')

@router.get("/memory")
async def get_memory_live():
    return safe_collect('get_memory')

@router.get("/storage")
async def get_storage_live():
    return safe_collect('get_disk')

@router.get("/network")
async def get_network_live():
    return safe_collect('get_network')

@router.get("/processes")
async def get_processes_live():
    return safe_collect('get_processes')

@router.get("/services")
async def get_services_live():
    return safe_collect('get_services')

@router.get("/gpu")
async def get_gpu_live():
    return safe_collect('get_gpu')

@router.get("/battery")
async def get_battery_live():
    return safe_collect('get_battery')
