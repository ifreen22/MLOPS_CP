from app.schemas.deployment import DeploymentCreate, DeploymentUpdate
from app.core.db import prisma


class DeploymentService:
    @staticmethod
    async def create_deployment(data: DeploymentCreate):
        return await prisma.deployment.create(
            data={
                "version": data.version,
                "status": data.status,
                "environment": data.environment,
                "service_id": data.service_id,
            }
        )

    @staticmethod
    async def get_deployment(deployment_id: int):
        return await prisma.deployment.find_unique(where={"id": deployment_id})

    @staticmethod
    async def get_deployments(skip: int = 0, limit: int = 100):
        return await prisma.deployment.find_many(skip=skip, take=limit)

    @staticmethod
    async def update_deployment(deployment_id: int, data: DeploymentUpdate):
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await prisma.deployment.find_unique(where={"id": deployment_id})
        return await prisma.deployment.update(
            where={"id": deployment_id}, data=update_data
        )

    @staticmethod
    async def delete_deployment(deployment_id: int):
        return await prisma.deployment.delete(where={"id": deployment_id})
