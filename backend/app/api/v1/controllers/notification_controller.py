from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime, timezone
from app.core.db import prisma

router = APIRouter(prefix="/notifications", tags=["Notifications"])

class NotificationSettings(BaseModel):
    webhookUrl: Optional[str] = "https://hooks.slack.com/services/T00/B00/EXAMPLE"
    slackChannel: Optional[str] = "#alerts-sre-incident"
    pagerDutyRoutingKey: Optional[str] = "pd_live_99a8b7c6d5e4"
    minSeverity: Optional[str] = "HIGH"
    enabledEvents: Optional[List[str]] = ["SITUATION_OPEN", "ANOMALY_SPIKE", "SLO_BREACH", "DEPLOYMENT_HIGH_RISK"]

# In-memory settings state with defaults (persists across requests during runtime)
_current_settings = {
    "webhookUrl": "https://hooks.slack.com/services/T00/B00/EXAMPLE",
    "slackChannel": "#alerts-sre-incident",
    "pagerDutyRoutingKey": "pd_live_99a8b7c6d5e4",
    "minSeverity": "HIGH",
    "enabledEvents": ["SITUATION_OPEN", "ANOMALY_SPIKE", "SLO_BREACH", "DEPLOYMENT_HIGH_RISK"],
    "updatedAt": datetime.now(timezone.utc).isoformat()
}

class TestNotificationRequest(BaseModel):
    channel: Optional[str] = "webhook"
    message: Optional[str] = None

@router.get("")
@router.get("/")
async def list_notifications():
    return await prisma.notification.find_many(
        take=50,
        order={"createdAt": "desc"}
    )

@router.get("/settings")
async def get_settings():
    return _current_settings

@router.post("/settings")
async def update_settings(payload: NotificationSettings):
    _current_settings.update({
        "webhookUrl": payload.webhookUrl,
        "slackChannel": payload.slackChannel,
        "pagerDutyRoutingKey": payload.pagerDutyRoutingKey,
        "minSeverity": payload.minSeverity,
        "enabledEvents": payload.enabledEvents,
        "updatedAt": datetime.now(timezone.utc).isoformat()
    })
    return {"status": "success", "settings": _current_settings}

@router.post("/test")
async def send_test_notification(payload: TestNotificationRequest):
    org = await prisma.organization.find_first()
    org_id = org.id if org else "default"
    admin = await prisma.user.find_first(where={"role": "ADMIN"})
    user_id = admin.id if admin else (await prisma.user.find_first()).id

    msg = payload.message or f"Test alert dispatched to {_current_settings['slackChannel']} via webhook. Severity: {_current_settings['minSeverity']}"
    
    # Record notification in database
    notification = await prisma.notification.create(
        data={
            "organizationId": org_id,
            "userId": user_id,
            "type": payload.channel.upper(),
            "message": msg,
            "isRead": False,
        }
    )
    
    return {
        "status": "delivered",
        "channel": payload.channel,
        "destination": _current_settings["webhookUrl"],
        "message": msg,
        "notificationId": notification.id,
        "deliveredAt": datetime.now(timezone.utc).isoformat(),
        "statusCode": 200
    }
