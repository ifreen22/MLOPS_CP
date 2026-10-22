from fastapi import APIRouter
from app.core.db import prisma
from app.schemas.extended import DashboardKPIs
from datetime import datetime, timezone

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/kpis", response_model=DashboardKPIs)
async def get_kpis():
    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    incidents = await prisma.incident.count(where={"status": "OPEN"})
    alerts = await prisma.alert.count(where={"status": "OPEN"})
    deployments = await prisma.deployment.count(where={"createdAt": {"gte": today}})
    latest_telemetry = await prisma.hosttelemetry.find_first(order={"timestamp": "desc"})
    health = 100.0 - latest_telemetry.cpuUsage if latest_telemetry else 0.0
    return DashboardKPIs(
        total_incidents=incidents,
        active_alerts=alerts,
        system_health=round(max(0.0, min(health, 100.0)), 1),
        deployments_today=deployments,
    )


@router.get("/")
async def get_dashboard():
    kpis = await get_kpis()
    situations = await prisma.situation.find_many(
        where={"status": "OPEN"},
        take=10,
        order={"updatedAt": "desc"},
    )
    return {
        "kpis": {
            "activeSituations": {
                "value": kpis.total_incidents,
                "change": "Live",
                "label": "Open incidents",
            },
            "mttr": {"value": "N/A", "change": "No resolved incidents", "label": "MTTR", "trend": []},
            "alertCompression": {
                "value": str(kpis.active_alerts),
                "ratio": "N/A",
                "target": "N/A",
                "label": "Open alerts",
            },
            "failureRiskServices": {
                "value": kpis.deployments_today,
                "label": "Deployments today",
                "riskThreshold": "N/A",
                "topService": "N/A",
                "topServiceRisk": 0,
                "heatmap": [],
            },
        },
        "situations": situations,
        "heatmap": [],
        "recentChanges": [],
    }
