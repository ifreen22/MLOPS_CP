from app.schemas.alert import AlertCreate, AlertUpdate
from app.core.db import prisma


class AlertService:
    @staticmethod
    async def create_alert(data: AlertCreate):
        return await prisma.alert.create(
            data={
                "title": data.title,
                "message": data.message,
                "severity": data.severity,
                "source": data.source,
                "status": "OPEN",
                "service_id": data.service_id,
                "incident_id": data.incident_id,
            }
        )

    @staticmethod
    async def get_alert(alert_id: int):
        return await prisma.alert.find_unique(where={"id": alert_id})

    @staticmethod
    async def get_alerts(skip: int = 0, limit: int = 100):
        return await prisma.alert.find_many(skip=skip, take=limit)

    @staticmethod
    async def update_alert(alert_id: int, data: AlertUpdate):
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await prisma.alert.find_unique(where={"id": alert_id})
        return await prisma.alert.update(where={"id": alert_id}, data=update_data)

    @staticmethod
    async def delete_alert(alert_id: int):
        return await prisma.alert.delete(where={"id": alert_id})
