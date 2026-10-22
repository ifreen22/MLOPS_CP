import sys
import time
import json
import asyncio
from backend.app.ml_services.orchestrator.service import AIOrchestratorService

async def trace():
    start = time.time()
    orchestrator = AIOrchestratorService()
    
    payload = {
        'cpu_usage': 98.5,
        'memory_usage': 85.0,
        'network_latency': 350.0,
        'error_rate': 0.15,
        'service_id': 'frontend-svc'
    }
    
    print("====================================================")
    print("PHASE 10: AUTOMATION VALIDATION (TRACE PIPELINE)")
    print("====================================================\n")
    
    print(f"[{time.time()-start:.4f}s] [1] Telemetry Ingested: {payload}")
    
    t_start = time.time()
    print(f"[{t_start-start:.4f}s] [2] Sending to AI Orchestrator...")
    
    res = orchestrator.analyze_telemetry(payload)
    
    print(f"[{time.time()-start:.4f}s] [3] Prediction / Threshold Evaluation Complete.")
    
    anomaly = res.get('anomaly_detection', {})
    print(f" -> Anomaly Found: {anomaly.get('is_anomaly')} (Score: {anomaly.get('anomaly_score')})")
    
    rca = res.get('root_cause_analysis', {})
    print(f" -> RCA Target: {rca.get('root_cause_node')} (Confidence: {rca.get('confidence')})")
    
    risk = res.get('risk_prediction', {})
    print(f" -> Risk Level: {risk.get('risk_level')} (Probability: {risk.get('risk_probability')})")
    
    cluster = res.get('alert_clustering', {})
    print(f" -> Alert Cluster: {cluster.get('cluster_id')}")
    
    action = res.get('recommended_action')
    print(f" -> Playbook Recommended: {action}")
    
    print(f"\nTrace completed in {time.time()-start:.4f}s")
    print("\nFull JSON Response:")
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    asyncio.run(trace())
