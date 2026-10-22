from app.schemas.incident import IncidentCreate, IncidentUpdate
from app.core.db import prisma


class IncidentService:
    @staticmethod
    async def create_incident(data: IncidentCreate):
        return await prisma.incident.create(
            data={
                "title": data.title,
                "description": data.description,
                "severity": data.severity,
                "status": data.status,
                "service_id": data.service_id,
            }
        )

    @staticmethod
    async def get_incident(incident_id: int):
        return await prisma.incident.find_unique(where={"id": incident_id})

    @staticmethod
    async def get_incidents(skip: int = 0, limit: int = 100):
        return await prisma.incident.find_many(skip=skip, take=limit)

    @staticmethod
    async def update_incident(incident_id: int, data: IncidentUpdate):
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await prisma.incident.find_unique(where={"id": incident_id})
        return await prisma.incident.update(where={"id": incident_id}, data=update_data)

    @staticmethod
    async def delete_incident(incident_id: int):
        return await prisma.incident.delete(where={"id": incident_id})
