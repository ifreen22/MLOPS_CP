from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.db import prisma

router = APIRouter(prefix="/situations", tags=["Situations"])


class SituationResolution(BaseModel):
    resolutionNote: str


@router.get("/")
async def list_situations():
    return await prisma.situation.find_many(
        include={"clusters": True},
        order={"updatedAt": "desc"},
    )


@router.get("/{situation_id}")
async def get_situation(situation_id: str):
    situation = await prisma.situation.find_unique(
        where={"id": situation_id},
        include={"clusters": True},
    )
    if situation is None:
        raise HTTPException(status_code=404, detail="Situation not found.")
    return situation


@router.post("/{situation_id}/resolve")
async def resolve_situation(situation_id: str, payload: SituationResolution):
    situation = await prisma.situation.find_unique(where={"id": situation_id})
    if situation is None:
        raise HTTPException(status_code=404, detail="Situation not found.")
    if situation.status != "OPEN":
        raise HTTPException(status_code=409, detail="Situation is not open.")

    return await prisma.situation.update(
        where={"id": situation_id},
        data={
            "status": "RESOLVED",
            "summary": f"{situation.summary or ''}\nResolution: {payload.resolutionNote}".strip(),
            "updatedAt": datetime.now(timezone.utc),
        },
    )
