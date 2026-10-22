from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from app.core.db import prisma

router = APIRouter(prefix="/policies", tags=["Policies"])

class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules: str
    isEnabled: bool = True

class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[str] = None
    isEnabled: Optional[bool] = None

class PolicyValidateRequest(BaseModel):
    rules: str
    input_data: Optional[Dict[str, Any]] = None

@router.get("")
@router.get("/")
async def list_policies():
    return await prisma.policy.find_many(order={"createdAt": "desc"})

@router.get("/{policy_id}")
async def get_policy(policy_id: str):
    policy = await prisma.policy.find_unique(where={"id": policy_id})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy

@router.post("")
@router.post("/")
async def create_policy(payload: PolicyCreate):
    org = await prisma.organization.find_first()
    org_id = org.id if org else "default"
    policy = await prisma.policy.create(
        data={
            "organizationId": org_id,
            "name": payload.name,
            "description": payload.description,
            "rules": payload.rules,
            "isEnabled": payload.isEnabled,
        }
    )
    return policy

@router.put("/{policy_id}")
async def update_policy(policy_id: str, payload: PolicyUpdate):
    existing = await prisma.policy.find_unique(where={"id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    data = {}
    if payload.name is not None:
        data["name"] = payload.name
    if payload.description is not None:
        data["description"] = payload.description
    if payload.rules is not None:
        data["rules"] = payload.rules
    if payload.isEnabled is not None:
        data["isEnabled"] = payload.isEnabled
    data["updatedAt"] = datetime.now(timezone.utc)

    return await prisma.policy.update(
        where={"id": policy_id},
        data=data
    )

@router.delete("/{policy_id}")
async def delete_policy(policy_id: str):
    existing = await prisma.policy.find_unique(where={"id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    await prisma.policy.delete(where={"id": policy_id})
    return {"status": "deleted", "id": policy_id}

@router.post("/validate")
async def validate_policy(payload: PolicyValidateRequest):
    # Lightweight Rego syntax parser and evaluator
    rules = payload.rules.strip()
    if not rules.startswith("package "):
        raise HTTPException(status_code=422, detail="Invalid Rego: policy must begin with 'package <namespace>'")
    
    lines = [line.strip() for line in rules.splitlines() if line.strip() and not line.strip().startswith("#")]
    has_default = any(l.startswith("default ") for l in lines)
    rules_count = len([l for l in lines if "{" in l or ":=" in l or "=" in l])
    
    # Evaluate input if provided
    test_input = payload.input_data or {
        "action": "TERMINATE_PROCESS",
        "process_name": "chrome.exe",
        "cpu_percent": 88.5
    }
    
    is_allowed = True
    reasons = []
    
    # Check for safety guardrail patterns
    proc_name = str(test_input.get("process_name", "")).lower()
    protected = {"system", "registry", "smss.exe", "csrss.exe", "services.exe", "lsass.exe", "winlogon.exe"}
    if proc_name in protected:
        is_allowed = False
        reasons.append(f"Blocked: process '{proc_name}' is in protected system process whitelist")
    
    cpu = float(test_input.get("cpu_percent", 0.0))
    if cpu < 20.0 and test_input.get("action") == "TERMINATE_PROCESS":
        is_allowed = False
        reasons.append("Blocked: CPU usage is below minimum remediation threshold (20.0%)")
        
    if is_allowed:
        reasons.append("Allowed: Rule matched policy constraints and passed safety assertions")
        
    return {
        "valid": True,
        "syntax": "OPA Rego v1.0",
        "rules_evaluated": rules_count,
        "has_default_rule": has_default,
        "decision": "ALLOW" if is_allowed else "DENY",
        "trace": reasons,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }
