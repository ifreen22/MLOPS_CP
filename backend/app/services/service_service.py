from app.schemas.service import ServiceCreate, ServiceUpdate
from app.core.db import prisma


class ServiceService:
    @staticmethod
    async def create_service(data: ServiceCreate):
        return await prisma.service.create(
            data={
                "name": data.name,
                "description": data.description,
                "repo_url": data.repo_url,
                "cluster_id": data.cluster_id,
            }
        )

    @staticmethod
    async def get_service(service_id: int):
        return await prisma.service.find_unique(where={"id": service_id})

    @staticmethod
    async def get_services(skip: int = 0, limit: int = 100):
        return await prisma.service.find_many(skip=skip, take=limit)

    @staticmethod
    async def update_service(service_id: int, data: ServiceUpdate):
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await prisma.service.find_unique(where={"id": service_id})
        return await prisma.service.update(where={"id": service_id}, data=update_data)

    @staticmethod
    async def delete_service(service_id: int):
        return await prisma.service.delete(where={"id": service_id})
