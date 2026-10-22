import json

from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import get_current_user
from pydantic import BaseModel, Field
from typing import Optional

from app.core.db import prisma
from app.api.v1.controllers import system_controller

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])

BUILTIN_PLAYBOOK = {
    "id": "terminate-high-cpu-process",
    "name": "Terminate high-CPU process",
    "description": "Selects a process from recent host telemetry and asks the Windows agent to terminate it.",
    "failurePattern": "Sustained high CPU usage",
    "actionType": "TERMINATE_PROCESS",
    "riskClass": "high",
    "successRate": None,
    "runs": 0,
    "lastUsed": "Never",
    "version": "built-in",
}


async def _audit_playbook_execution(user, target_pid: int, outcome: str):
    async with prisma.tx() as transaction:
        await transaction.auditlog.create(
            data={
                "organizationId": user.organizationId,
                "userId": user.id,
                "action": "PLAYBOOK_EXECUTION",
                "resource": "Playbook",
                "resourceId": BUILTIN_PLAYBOOK["id"],
                "details": json.dumps({"targetPid": target_pid, "outcome": outcome}),
            }
        )


class PlaybookExecutionRequest(BaseModel):
    dryRun: bool = True
    pid: Optional[int] = Field(default=None, gt=4)


@router.get("/")
async def get_playbooks():
    playbooks = await prisma.playbook.find_many(order={"createdAt": "desc"})
    return [BUILTIN_PLAYBOOK, *playbooks]


@router.post("/{playbook_id}/execute")
async def execute_playbook(
    playbook_id: str,
    payload: PlaybookExecutionRequest,
    current_user=Depends(get_current_user),
):
    if playbook_id != BUILTIN_PLAYBOOK["id"]:
        raise HTTPException(status_code=404, detail="Playbook not found.")
    if not payload.dryRun and current_user.role not in {"ADMIN", "OPERATOR"}:
        raise HTTPException(
            status_code=403,
            detail="An operator or administrator is required to execute a playbook.",
        )
    last_telemetry = system_controller.last_telemetry
    if last_telemetry is None:
        raise HTTPException(status_code=409, detail="Host telemetry is not available.")

    target_pid = payload.pid
    if target_pid is None:
        candidate = next(
            (
                process
                for process in sorted(
                    last_telemetry.get("processes", []),
                    key=lambda process: float(process.get("cpu_percent", 0) or 0),
                    reverse=True,
                )
                if int(process.get("pid", 0) or 0) > 4
                and float(process.get("cpu_percent", 0) or 0) >= 20
            ),
            None,
        )
        target_pid = candidate.get("pid") if candidate else None

    if target_pid is None:
        raise HTTPException(status_code=409, detail="No eligible high-CPU process is present in live telemetry.")
    process, process_create_time = system_controller.get_eligible_process(target_pid)

    if payload.dryRun:
        await _audit_playbook_execution(current_user, target_pid, "DRY_RUN")
        return {
            "status": "dry_run",
            "actionType": BUILTIN_PLAYBOOK["actionType"],
            "target": target_pid,
            "process": process.get("name"),
            "message": "Preview only; no process was terminated.",
        }

    settings = await prisma.systemsettings.find_first()
    if not settings or not settings.autoRecovery:
        raise HTTPException(status_code=409, detail="Enable Auto Recovery before executing a playbook.")

    pending = await prisma.actionqueue.find_first(
        where={
            "organizationId": current_user.organizationId,
            "actionType": BUILTIN_PLAYBOOK["actionType"],
            "target": str(target_pid),
            "processCreateTime": process_create_time,
            "status": "PENDING",
        }
    )
    if pending:
        await _audit_playbook_execution(current_user, target_pid, "ALREADY_QUEUED")
        return {"status": "queued", "actionId": pending.id, "target": target_pid}

    action = await system_controller.queue_termination_action(
        target_pid,
        process,
        process_create_time,
        current_user,
    )
    await _audit_playbook_execution(current_user, target_pid, "QUEUED")
    return {"status": "queued", "actionId": action.id, "target": target_pid}
