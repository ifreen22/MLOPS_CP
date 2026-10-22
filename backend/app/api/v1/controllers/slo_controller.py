from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.db import prisma

router = APIRouter(prefix="/slos", tags=["Service Level Objectives"])

MetricName = Literal["cpu_usage", "memory_usage", "disk_usage"]
METRIC_FIELDS = {
    "cpu_usage": "cpuUsage",
    "memory_usage": "memoryPercent",
    "disk_usage": "diskPercent",
}


class SloCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    metric: MetricName
    threshold: float = Field(ge=0, le=100)
    targetPercent: float = Field(gt=0, le=100)
    windowHours: int = Field(ge=1, le=720)


@router.get("/")
async def list_slos():
    objectives = await prisma.servicelevelobjective.find_many(
        order={"createdAt": "desc"}
    )
    if not objectives:
        return []

    now = datetime.now(timezone.utc)
    earliest = min(
        now - timedelta(hours=objective.windowHours) for objective in objectives
    )
    records = await prisma.hosttelemetry.find_many(
        where={"timestamp": {"gte": earliest}},
        take=10000,
        order={"timestamp": "desc"},
    )

    results = []
    for objective in objectives:
        cutoff = now - timedelta(hours=objective.windowHours)
        values = [
            float(getattr(record, METRIC_FIELDS[objective.metric]))
            for record in records
            if record.timestamp >= cutoff
        ]
        sample_count = len(values)
        compliance = (
            sum(value <= objective.threshold for value in values) / sample_count * 100
            if sample_count
            else None
        )
        error_budget = 100 - objective.targetPercent
        if compliance is None:
            budget_remaining = None
        elif error_budget == 0:
            budget_remaining = 100.0 if compliance == 100 else 0.0
        else:
            budget_remaining = max(
                0.0, min(100.0, 100 - (100 - compliance) / error_budget * 100)
            )

        results.append(
            {
                "id": objective.id,
                "name": objective.name,
                "description": objective.description,
                "metric": objective.metric,
                "threshold": objective.threshold,
                "targetPercent": objective.targetPercent,
                "windowHours": objective.windowHours,
                "sampleCount": sample_count,
                "compliancePercent": round(compliance, 3) if compliance is not None else None,
                "errorBudgetRemainingPercent": (
                    round(budget_remaining, 3)
                    if budget_remaining is not None
                    else None
                ),
                "status": (
                    "no_data"
                    if compliance is None
                    else "met"
                    if compliance >= objective.targetPercent
                    else "breached"
                ),
            }
        )
    return results


@router.post("/", status_code=201)
async def create_slo(payload: SloCreate):
    return await prisma.servicelevelobjective.create(data=payload.model_dump())


@router.delete("/{slo_id}", status_code=204)
async def delete_slo(slo_id: str):
    objective = await prisma.servicelevelobjective.find_unique(where={"id": slo_id})
    if objective is None:
        raise HTTPException(status_code=404, detail="SLO not found.")
    await prisma.servicelevelobjective.delete(where={"id": slo_id})
    return Response(status_code=204)
