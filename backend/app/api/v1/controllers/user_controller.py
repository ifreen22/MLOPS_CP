import json
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.core.auth import get_password_hash, require_role
from app.core.db import prisma
from app.schemas.extended import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


class UserStatusUpdate(BaseModel):
    isActive: bool


def _audit_entry(organization_id: str, user_id: str, action: str, resource_id: str, details: dict | None = None):
    return {
        "organizationId": organization_id,
        "userId": user_id,
        "action": action,
        "resource": "User",
        "resourceId": resource_id,
        "details": json.dumps(details) if details else None,
    }


async def _ensure_another_active_admin(transaction, organization_id: str):
    admin_count = await transaction.user.count(
        where={
            "organizationId": organization_id,
            "role": "ADMIN",
            "isActive": True,
        }
    )
    if admin_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The organization's last active administrator cannot be disabled or demoted.",
        )


async def _revoke_user_sessions(transaction, user_id: str):
    sessions = await transaction.authsession.find_many(
        where={"userId": user_id, "revokedAt": None}
    )
    for session in sessions:
        await transaction.authsession.update(
            where={"id": session.id},
            data={"revokedAt": datetime.now(timezone.utc)},
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    current_user=Depends(require_role(["ADMIN"])),
):
    if len(data.password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at most 72 UTF-8 bytes.",
        )
    existing_user = await prisma.user.find_unique(where={"email": data.email})
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    async with prisma.tx() as transaction:
        user = await transaction.user.create(
            data={
                "organizationId": current_user.organizationId,
                "email": data.email,
                "passwordHash": get_password_hash(data.password),
                "firstName": data.firstName,
                "lastName": data.lastName,
                "role": data.role,
            },
        )
        await transaction.auditlog.create(
            data=_audit_entry(
                current_user.organizationId,
                current_user.id,
                "USER_CREATED",
                user.id,
                {"email": user.email, "role": user.role},
            )
        )
    return user


@router.get("/", response_model=List[UserResponse])
async def get_users(current_user=Depends(require_role(["ADMIN"]))):
    return await prisma.user.find_many(
        where={"organizationId": current_user.organizationId},
        order={"createdAt": "desc"},
    )


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    current_user=Depends(require_role(["ADMIN"])),
):
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one field to update.")
    if "password" in changes:
        if len(changes["password"].encode("utf-8")) > 72:
            raise HTTPException(status_code=422, detail="Password must be at most 72 UTF-8 bytes.")
        changes["passwordHash"] = get_password_hash(changes.pop("password"))

    target = await prisma.user.find_first(
        where={"id": user_id, "organizationId": current_user.organizationId}
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if "email" in changes:
        existing = await prisma.user.find_unique(where={"email": changes["email"]})
        if existing is not None and existing.id != target.id:
            raise HTTPException(status_code=409, detail="A user with this email already exists.")
    if target.id == current_user.id and changes.get("role", target.role) != "ADMIN":
        raise HTTPException(status_code=409, detail="You cannot remove your own administrator role.")
    async with prisma.tx() as transaction:
        if (
            target.isActive
            and target.role == "ADMIN"
            and changes.get("role", target.role) != "ADMIN"
        ):
            await _ensure_another_active_admin(
                transaction, current_user.organizationId
            )
        updated = await transaction.user.update(
            where={"id": target.id},
            data=changes,
        )
        if "passwordHash" in changes:
            await _revoke_user_sessions(transaction, target.id)
        action = (
            "USER_ROLE_CHANGED"
            if "role" in changes and changes["role"] != target.role
            else "USER_UPDATED"
        )
        await transaction.auditlog.create(
            data=_audit_entry(
                current_user.organizationId,
                current_user.id,
                action,
                target.id,
                {
                    key: value
                    for key, value in changes.items()
                    if key != "passwordHash"
                },
            )
        )
    return updated


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: str,
    data: UserStatusUpdate,
    current_user=Depends(require_role(["ADMIN"])),
):
    target = await prisma.user.find_first(
        where={"id": user_id, "organizationId": current_user.organizationId}
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == current_user.id and not data.isActive:
        raise HTTPException(status_code=409, detail="You cannot disable your own account.")
    async with prisma.tx() as transaction:
        if target.isActive and target.role == "ADMIN" and not data.isActive:
            await _ensure_another_active_admin(
                transaction, current_user.organizationId
            )
        updated = await transaction.user.update(
            where={"id": target.id},
            data={"isActive": data.isActive},
        )
        if not data.isActive:
            await _revoke_user_sessions(transaction, target.id)
        await transaction.auditlog.create(
            data=_audit_entry(
                current_user.organizationId,
                current_user.id,
                "USER_ENABLED" if data.isActive else "USER_DISABLED",
                target.id,
                {"email": target.email},
            )
        )
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user=Depends(require_role(["ADMIN"])),
):
    target = await prisma.user.find_first(
        where={"id": user_id, "organizationId": current_user.organizationId}
    )
    if target is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.id == current_user.id:
        raise HTTPException(status_code=409, detail="You cannot delete your own account.")
    async with prisma.tx() as transaction:
        if target.isActive and target.role == "ADMIN":
            await _ensure_another_active_admin(
                transaction, current_user.organizationId
            )
        await transaction.user.update(
            where={"id": target.id},
            data={"isActive": False},
        )
        await _revoke_user_sessions(transaction, target.id)
        await transaction.auditlog.create(
            data=_audit_entry(
                current_user.organizationId,
                current_user.id,
                "USER_DELETED",
                target.id,
                {"email": target.email, "deactivated": True},
            )
        )


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    current_user=Depends(require_role(["ADMIN"])),
):
    entries = await prisma.auditlog.find_many(
        where={"organizationId": current_user.organizationId},
        take=limit,
        skip=skip,
        order={"createdAt": "desc"},
        include={"user": True},
    )
    return [
        {
            "id": entry.id,
            "action": entry.action,
            "resource": entry.resource,
            "resourceId": entry.resourceId,
            "details": entry.details,
            "createdAt": entry.createdAt,
            "userId": entry.userId,
            "userEmail": entry.user.email if entry.user else None,
        }
        for entry in entries
    ]
