from fastapi import APIRouter
from typing import List
from app.schemas.extended import OrganizationCreate, OrganizationResponse
from app.core.db import prisma

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post("/", response_model=OrganizationResponse)
async def create_organization(data: OrganizationCreate):
    return await prisma.organization.create(
        data=data.model_dump(),
    )


@router.get("/", response_model=List[OrganizationResponse])
async def get_organizations():
    return await prisma.organization.find_many(order={"createdAt": "desc"})
