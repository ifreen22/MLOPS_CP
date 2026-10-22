import json
import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.auth import get_current_user, require_agent_token, require_agent_or_user, require_role
from app.core.db import prisma

router = APIRouter(prefix="/system", tags=["System Telemetry"])
logger = logging.getLogger(__name__)


@router.get("", dependencies=[Depends(require_agent_or_user)])
@router.get("/", dependencies=[Depends(require_agent_or_user)])
async def get_system_root():
    """
    Root system telemetry status endpoint.
    Accessible to both authenticated users and the Windows telemetry agent.
    """
    global last_telemetry
    return {
        "status": "online",
        "agentConnected": last_telemetry is not None,
        "lastTelemetry": last_telemetry,
    }

class ActionRequest(BaseModel):
    actionType: str = Field(pattern="^TERMINATE_PROCESS$")
    target: int = Field(gt=4)


class SystemSettingsUpdate(BaseModel):
    isMonitoring: Optional[bool] = None
    autoRecovery: Optional[bool] = None
    pollingInterval: Optional[int] = Field(default=None, ge=1, le=60)


class ActionCompletion(BaseModel):
    status: Literal["SUCCESS", "FAILED"]
    result: str = Field(default="", max_length=2000)


# In-memory store for the very latest telemetry
last_telemetry = None


def get_eligible_process(target_pid: int):
    if last_telemetry is None:
        raise HTTPException(status_code=409, detail="Host telemetry is not available.")

    timestamp = last_telemetry.get("timestamp")
    try:
        sampled_at = datetime.fromisoformat(timestamp)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=409,
            detail="Host telemetry has no valid sample timestamp.",
        ) from error

    if sampled_at.tzinfo is None:
        raise HTTPException(
            status_code=409,
            detail="Host telemetry timestamp must include a timezone.",
        )
    age_seconds = (datetime.now(timezone.utc) - sampled_at).total_seconds()
    if age_seconds > 30 or age_seconds < -60:
        raise HTTPException(
            status_code=409,
            detail="Host telemetry is stale; wait for a fresh agent sample.",
        )

    process = next(
        (
            item
            for item in last_telemetry.get("processes", [])
            if item.get("pid") == target_pid
        ),
        None,
    )
    if process is None:
        raise HTTPException(
            status_code=404,
            detail="The process is no longer present in telemetry.",
        )
    try:
        cpu_percent = float(process.get("cpu_percent", 0) or 0)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=409,
            detail="Process CPU telemetry is invalid; action was not queued.",
        ) from error
    if not math.isfinite(cpu_percent) or cpu_percent < 20:
        raise HTTPException(
            status_code=409,
            detail="The process is no longer using enough CPU to qualify for this action.",
        )

    process_name = str(process.get("name", "")).strip()
    if not process_name:
        raise HTTPException(
            status_code=409,
            detail="The process name is missing from telemetry.",
        )
    if process_name.lower() in {
        "system",
        "registry",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "services.exe",
        "lsass.exe",
        "winlogon.exe",
    }:
        raise HTTPException(
            status_code=409,
            detail="Termination of this protected process is not allowed.",
        )
    try:
        create_time = float(process["create_time"])
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=409,
            detail="Process identity is missing from telemetry; action was not queued.",
        ) from error
    if not math.isfinite(create_time) or create_time <= 0:
        raise HTTPException(
            status_code=409,
            detail="Process identity is invalid; action was not queued.",
        )

    return process, create_time


async def queue_termination_action(target_pid: int, process: dict, create_time: float, user):
    details = {
        "pid": target_pid,
        "processName": process["name"],
        "processCreateTime": create_time,
    }
    async with prisma.tx() as transaction:
        action = await transaction.actionqueue.create(
            data={
                "actionType": "TERMINATE_PROCESS",
                "target": str(target_pid),
                "status": "PENDING",
                "organizationId": user.organizationId,
                "requestedByUserId": user.id,
                "requestedByEmail": user.email,
                "processName": str(process["name"]),
                "processCreateTime": create_time,
            }
        )
        await transaction.auditlog.create(
            data={
                "organizationId": user.organizationId,
                "userId": user.id,
                "action": "PROCESS_TERMINATION_QUEUED",
                "resource": "ActionQueue",
                "resourceId": action.id,
                "details": json.dumps(details),
            }
        )
    return action


@router.get("/live", dependencies=[Depends(require_agent_or_user)])
async def get_live_system():
    global last_telemetry
    is_docker = os.path.exists('/.dockerenv')
    
    # Return status and latest telemetry
    return {
        "is_docker": is_docker,
        "data": last_telemetry
    }

@router.post("/telemetry", dependencies=[Depends(require_agent_token)])
async def post_telemetry(data: dict):
    global last_telemetry
    last_telemetry = data

    # Save to db
    cpu = data.get("cpu", {})
    ram = data.get("ram", {})
    disk = data.get("disk", {})
    net = data.get("network", {})

    cpu_usage = cpu.get("usage_percent", 0)
    memory_total = ram.get("total", 0)
    memory_used = ram.get("used", 0)
    memory_percent = ram.get("percent", 0)
    disk_total = disk.get("total", 0)
    disk_used = disk.get("used", 0)
    disk_percent = disk.get("percent", 0)
    net_sent = net.get("bytes_sent", 0)
    net_recv = net.get("bytes_recv", 0)
    battery_percent = data.get("battery_percent")
    temperature = data.get("temperature")

    try:
        record = await prisma.hosttelemetry.create(
            data={
                "cpuUsage": float(cpu_usage),
                "memoryTotal": int(memory_total),
                "memoryUsed": int(memory_used),
                "memoryPercent": float(memory_percent),
                "diskTotal": int(disk_total),
                "diskUsed": int(disk_used),
                "diskPercent": float(disk_percent),
                "netSent": int(net_sent),
                "netRecv": int(net_recv),
                "batteryPercent": float(battery_percent) if battery_percent is not None else None,
                "temperature": float(temperature) if temperature is not None else None,
            }
        )

        processes = data.get("processes", [])
        if processes:
            proc_data = []
            for p in processes:
                proc_data.append({
                    "telemetryId": record.id,
                    "pid": int(p.get("pid", 0)),
                    "name": str(p.get("name", "")),
                    "cpuPercent": float(p.get("cpu_percent", 0) or 0.0),
                    "memoryPercent": float(p.get("memory_percent", 0) or 0.0),
                    "exePath": str(p.get("exe", "") or "")
                })
            await prisma.hostprocess.create_many(data=proc_data)
            
    except Exception as e:
        logger.exception("Failed to save host telemetry")
        raise HTTPException(status_code=500, detail="Failed to persist host telemetry") from e
        
    return {"status": "ok"}

@router.get("/history")
async def get_system_history(
    limit: int = 100, current_user=Depends(get_current_user)
):
    history = await prisma.hosttelemetry.find_many(
        take=limit,
        order={"timestamp": "desc"}
    )
    return history

@router.get("/processes")
async def get_system_processes(
    limit: int = 50, current_user=Depends(get_current_user)
):
    processes = await prisma.hostprocess.find_many(
        take=limit,
        order={"timestamp": "desc"}
    )
    return processes

@router.get("/settings", dependencies=[Depends(require_agent_or_user)])
async def get_settings():
    settings = await prisma.systemsettings.find_first()
    if not settings:
        settings = await prisma.systemsettings.create(
            data={"isMonitoring": False, "autoRecovery": False, "pollingInterval": 2}
        )
    return settings


@router.get("/agent/settings", dependencies=[Depends(require_agent_token)])
async def get_agent_settings():
    settings = await prisma.systemsettings.find_first()
    if not settings:
        settings = await prisma.systemsettings.create(
            data={"isMonitoring": False, "autoRecovery": False, "pollingInterval": 2}
        )
    return settings


@router.post("/settings")
async def update_settings(
    payload: SystemSettingsUpdate,
    current_user=Depends(require_role(["ADMIN", "OPERATOR"])),
):
    changes = payload.model_dump(exclude_none=True)
    if changes.get("autoRecovery") is True and current_user.role != "ADMIN":
        raise HTTPException(
            status_code=403,
            detail="Only an administrator can enable Auto Recovery.",
        )

    settings = await prisma.systemsettings.find_first()
    if not settings:
        settings = await prisma.systemsettings.create(
            data={"isMonitoring": False, "autoRecovery": False, "pollingInterval": 2}
        )

    effective_changes = {
        key: value
        for key, value in changes.items()
        if value != getattr(settings, key)
    }
    if not effective_changes:
        return settings

    async with prisma.tx() as transaction:
        updated = await transaction.systemsettings.update(
            where={"id": settings.id},
            data=effective_changes,
        )
        await transaction.auditlog.create(
            data={
                "organizationId": current_user.organizationId,
                "userId": current_user.id,
                "action": "SYSTEM_SETTINGS_UPDATED",
                "resource": "SystemSettings",
                "resourceId": settings.id,
                "details": json.dumps(effective_changes),
            }
        )
    return updated

@router.get("/actions", dependencies=[Depends(require_agent_token)])
async def get_pending_actions():
    actions = await prisma.actionqueue.find_many(
        where={"status": "PENDING"}
    )
    return actions


@router.get("/actions/history")
async def get_action_history(
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(require_role(["ADMIN", "OPERATOR", "VIEWER"])),
):
    return await prisma.actionqueue.find_many(
        where={"organizationId": current_user.organizationId},
        take=limit,
        order={"createdAt": "desc"},
    )


@router.post("/actions")
async def create_action(
    payload: ActionRequest,
    current_user=Depends(require_role(["ADMIN", "OPERATOR"])),
):
    settings = await prisma.systemsettings.find_first()
    if not settings or not settings.autoRecovery:
        raise HTTPException(
            status_code=409,
            detail="Enable Auto Recovery before queueing an action.",
        )

    process, create_time = get_eligible_process(payload.target)
    return await queue_termination_action(
        payload.target,
        process,
        create_time,
        current_user,
    )

@router.post(
    "/actions/{action_id}/complete",
    dependencies=[Depends(require_agent_token)],
)
async def complete_action(action_id: str, completion: ActionCompletion):
    async with prisma.tx() as transaction:
        action = await transaction.actionqueue.find_unique(where={"id": action_id})
        if action is None:
            raise HTTPException(status_code=404, detail="Action not found.")
        if action.status != "PENDING":
            raise HTTPException(status_code=409, detail="Action has already been completed.")

        updated = await transaction.actionqueue.update(
            where={"id": action_id},
            data={
                "status": completion.status,
                "result": completion.result[:2000],
                "completedAt": datetime.now(timezone.utc),
            },
        )
        if action.organizationId and action.requestedByUserId:
            await transaction.auditlog.create(
                data={
                    "organizationId": action.organizationId,
                    "userId": action.requestedByUserId,
                    "action": "PROCESS_TERMINATION_COMPLETED",
                    "resource": "ActionQueue",
                    "resourceId": action.id,
                    "details": json.dumps(
                        {
                            "status": completion.status,
                            "result": completion.result[:1000],
                            "completedBy": "windows-agent",
                        }
                    ),
                }
            )
    return updated
