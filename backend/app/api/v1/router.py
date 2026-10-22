from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.api.v1.controllers import (
    incident_controller,
    alert_controller,
    service_controller,
    deployment_controller,
    user_controller,
    organization_controller,
    dashboard_controller,
    log_controller,
    metric_controller,
    trace_controller,
    playbook_controller,
    risk_score_controller,
    telemetry_controller,
    ml_anomaly_controller,
    topology_controller,
    ml_alert_clustering_controller,
    ml_rca_controller,
    ml_risk_controller,
    ml_orchestrator_controller,
    situation_controller,
    slo_controller,
    policy_controller,
    notification_controller,
    ml_registry_controller,
)

api_router = APIRouter(dependencies=[Depends(get_current_user)])

api_router.include_router(incident_controller.router)
api_router.include_router(alert_controller.router)
api_router.include_router(service_controller.router)
api_router.include_router(deployment_controller.router)
api_router.include_router(user_controller.router)
api_router.include_router(organization_controller.router)
api_router.include_router(dashboard_controller.router)
api_router.include_router(log_controller.router)
api_router.include_router(metric_controller.router)
api_router.include_router(trace_controller.router)
api_router.include_router(playbook_controller.router)
api_router.include_router(risk_score_controller.router)
api_router.include_router(telemetry_controller.router)
api_router.include_router(ml_anomaly_controller.router)
api_router.include_router(topology_controller.router)
api_router.include_router(ml_alert_clustering_controller.router)
api_router.include_router(ml_rca_controller.router)
api_router.include_router(ml_risk_controller.router)
api_router.include_router(ml_orchestrator_controller.router)
api_router.include_router(situation_controller.router)
api_router.include_router(slo_controller.router)
api_router.include_router(policy_controller.router)
api_router.include_router(notification_controller.router)
api_router.include_router(ml_registry_controller.router)
