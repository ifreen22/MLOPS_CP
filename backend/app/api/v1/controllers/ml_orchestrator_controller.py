from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from app.ml_services.orchestrator.service import orchestrator_service
import logging
import math
from datetime import datetime, timezone
from app.api.v1.controllers import system_controller

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ML Orchestration Engine"])

class TelemetryPayload(BaseModel):
    # Anomaly Detection subset
    cpu_usage: Optional[float] = Field(None, description="CPU usage metric")
    sin_hour: Optional[float] = Field(None, description="Time encoded sine")
    cos_hour: Optional[float] = Field(None, description="Time encoded cosine")
    rolling_mean: Optional[float] = Field(None, description="Rolling mean of metric")
    rolling_std: Optional[float] = Field(None, description="Rolling standard deviation")
    lag_1: Optional[float] = Field(None, description="T-1 lag feature")
    
    # Alert Clustering subset
    log_text: Optional[str] = Field(None, description="Actual log or alert text")
    
    # RCA subset (7 nodes x 5 features)
    topology_batch: Optional[List[List[float]]] = Field(None, description="7x5 Topology matrix for GNN")
    
    # Risk Prediction subset
    deployment_size: Optional[float] = None
    files_changed: Optional[float] = None
    code_churn: Optional[float] = None
    developer_experience: Optional[float] = None
    deployment_time: Optional[float] = None
    day_of_week: Optional[float] = None
    rollback_count: Optional[float] = None
    previous_incident_count: Optional[float] = None
    cpu_increase: Optional[float] = None
    memory_increase: Optional[float] = None
    network_latency: Optional[float] = None
    disk_io: Optional[float] = None
    service_dependency_count: Optional[float] = None

@router.get("/ml/analyze/health")
def orchestrator_health():
    try:
        return orchestrator_service.get_health()
    except Exception as e:
        logger.error(f"Orchestrator health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from app.core.db import prisma

@router.post("/ml/analyze")
async def analyze_telemetry(payload: Optional[TelemetryPayload] = None):
    try:
        live_data = system_controller.last_telemetry
        if not live_data:
            if payload is None:
                return {
                    "status": "unavailable",
                    "analysis": {"recommended_actions": []},
                    "detail": "Host telemetry is not available.",
                }
            results = orchestrator_service.analyze_telemetry(
                payload.model_dump(exclude_unset=True)
            )
            return {"status": "success", "analysis": results}
            
        cpu_usage = live_data.get('cpu', {}).get('usage_percent', 0)
        processes = live_data.get('processes', [])
        history = await prisma.hosttelemetry.find_many(
            take=5,
            order={"timestamp": "desc"},
        )
        cpu_history = [record.cpuUsage for record in reversed(history)]
        if not cpu_history:
            cpu_history = [cpu_usage]
        current_hour = datetime.now(timezone.utc).hour
        
        heaviest_proc = None
        if processes:
            eligible_processes = [
                process for process in processes if int(process.get("pid", 0) or 0) > 4
            ]
            if eligible_processes:
                heaviest_proc = max(
                    eligible_processes,
                    key=lambda process: process.get("cpu_percent", 0) or 0,
                )
            
        payload_dict = {
            "cpu_usage": cpu_usage,
            "sin_hour": math.sin(2 * math.pi * current_hour / 24),
            "cos_hour": math.cos(2 * math.pi * current_hour / 24),
            "rolling_mean": sum(cpu_history) / len(cpu_history),
            "rolling_std": (
                sum((value - sum(cpu_history) / len(cpu_history)) ** 2 for value in cpu_history)
                / len(cpu_history)
            ) ** 0.5,
            "lag_1": cpu_history[-2] if len(cpu_history) > 1 else cpu_usage,
            "cpu_increase": cpu_usage / 100.0,
            "memory_increase": live_data.get('ram', {}).get('percent', 0) / 100.0,
            "network_latency": (live_data.get('network', {}).get('upload_speed', 0) + live_data.get('network', {}).get('download_speed', 0)) / 1024,
            "disk_io": live_data.get('disk', {}).get('percent', 0),
        }
        if payload and payload.log_text and payload.log_text.strip():
            payload_dict["log_text"] = payload.log_text
        
        results = orchestrator_service.analyze_telemetry(payload_dict)
        
        # Override recommended actions based on REAL telemetry
        actions = []
        if heaviest_proc and heaviest_proc.get('cpu_percent', 0) > 20:
            proc_name = heaviest_proc['name'].lower()
            pid = heaviest_proc['pid']

            if 'chrome' in proc_name:
                actions.append("Close Chrome tabs to free up CPU.")
            elif 'docker' in proc_name:
                actions.append("Stop unnecessary Docker containers.")
            elif 'code' in proc_name:
                actions.append("Restart VS Code or close heavy extensions.")
            elif 'postgres' in proc_name:
                actions.append("Restart PostgreSQL service.")
            else:
                actions.append(f"Consider reviewing high-CPU process: {heaviest_proc['name']} (PID: {pid})")
                
        if live_data.get('ram', {}).get('percent', 0) > 85:
            actions.append("Increase swap memory or close heavy applications. RAM usage is critically high.")
            
        if live_data.get('disk', {}).get('percent', 0) > 90:
            actions.append("Free disk space immediately. Clear temp files.")
            
        if not actions:
            actions.append("Systems operating normally based on host telemetry.")

        results["recommended_actions"] = actions
        
        return {"status": "success", "analysis": results}
    except Exception as e:
        logger.error(f"Orchestrator analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Orchestration pipeline failed: {str(e)}")
