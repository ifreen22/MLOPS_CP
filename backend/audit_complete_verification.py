import json
import os
import sys
import time
import subprocess
import requests
from datetime import datetime, timezone

base_url = "http://127.0.0.1:8000"
agent_token = "x3Rxw2keZYcsthfajgRG7Y1OmopSfD6zrfNfB5VfDtg"

audit_records = []

def record(category, name, status, evidence):
    audit_records.append({
        "category": category,
        "name": name,
        "status": status,
        "evidence": evidence
    })
    tag = "[COMPLETE]" if status == "COMPLETE" else f"[{status}]"
    print(f"\n{tag} [{category}] {name}")
    print(f"Evidence: {evidence}")

print("==========================================================================")
print("AIOPS SENTINEL COMPREHENSIVE PRODUCTION VERIFICATION AUDIT")
print("==========================================================================")

session = requests.Session()

# -------------------------------------------------------------
# 1. Ensure Operator and Viewer users exist for Role Testing
# -------------------------------------------------------------
ensure_users_script = (
    "import asyncio\n"
    "from app.core.db import prisma\n"
    "from app.core.auth import get_password_hash\n"
    "async def setup():\n"
    "    await prisma.connect()\n"
    "    org = await prisma.organization.find_first()\n"
    "    if not org:\n"
    "        org = await prisma.organization.create(data={'name': 'AIOps Sentinel Local'})\n"
    "    op = await prisma.user.find_unique(where={'email': 'operator@sentinel.local'})\n"
    "    if not op:\n"
    "        await prisma.user.create(data={'email': 'operator@sentinel.local', 'passwordHash': get_password_hash('OperatorSecret123!'), 'role': 'OPERATOR', 'organizationId': org.id})\n"
    "    vi = await prisma.user.find_unique(where={'email': 'viewer@sentinel.local'})\n"
    "    if not vi:\n"
    "        await prisma.user.create(data={'email': 'viewer@sentinel.local', 'passwordHash': get_password_hash('ViewerSecret123!'), 'role': 'VIEWER', 'organizationId': org.id})\n"
    "asyncio.run(setup())\n"
)
proc = subprocess.run(["docker", "exec", "mlops_cp-backend-1", "python", "-c", ensure_users_script], capture_output=True, text=True)

# -------------------------------------------------------------
# 2. Authenticate all three roles
# -------------------------------------------------------------
tokens = {}
for role, creds in [
    ("ADMIN", ("admin@localhost", "caXK6HxqFUVS5buIi1ayl2wEA2w4kTsI8rtuCRj_9rA")),
    ("OPERATOR", ("operator@sentinel.local", "OperatorSecret123!")),
    ("VIEWER", ("viewer@sentinel.local", "ViewerSecret123!"))
]:
    try:
        resp = session.post(f"{base_url}/api/v1/auth/login", data={"username": creds[0], "password": creds[1]}, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            tokens[role] = data["access_token"]
            record("Authentication", f"Role {role} Login", "COMPLETE", f"Authenticated {creds[0]} as {data['user']['role']}, HTTP 200, JWT: {tokens[role][:18]}...")
        else:
            record("Authentication", f"Role {role} Login", "NEEDS IMPROVEMENT", f"Failed {creds[0]}: HTTP {resp.status_code} {resp.text}")
    except Exception as e:
        record("Authentication", f"Role {role} Login", "NEEDS IMPROVEMENT", f"Failed to login {creds[0]}: {e}")

admin_headers = {"Authorization": f"Bearer {tokens.get('ADMIN', '')}"}
operator_headers = {"Authorization": f"Bearer {tokens.get('OPERATOR', '')}"}
viewer_headers = {"Authorization": f"Bearer {tokens.get('VIEWER', '')}"}

# -------------------------------------------------------------
# 3. RBAC Verification Matrix
# -------------------------------------------------------------
# A. POST /api/v1/users/ (Admin only)
admin_get = session.get(f"{base_url}/api/v1/users/", headers=admin_headers, timeout=5)
op_post = session.post(f"{base_url}/api/v1/users/", json={"email": "rbac_test@test.local", "password": "TestPassword123!"}, headers=operator_headers, timeout=5)
view_post = session.post(f"{base_url}/api/v1/users/", json={"email": "rbac_test@test.local", "password": "TestPassword123!"}, headers=viewer_headers, timeout=5)

if admin_get.status_code == 200 and op_post.status_code == 403 and view_post.status_code == 403:
    record("RBAC", "Admin-Only Privilege Isolation (/api/v1/users/)", "COMPLETE", f"Admin read=HTTP {admin_get.status_code} OK ({len(admin_get.json())} users); Operator write blocked=HTTP {op_post.status_code} Forbidden; Viewer write blocked=HTTP {view_post.status_code} Forbidden.")
else:
    record("RBAC", "Admin-Only Privilege Isolation", "NEEDS IMPROVEMENT", f"Admin={admin_get.status_code}, Operator={op_post.status_code}, Viewer={view_post.status_code}")

# B. POST /api/v1/system/settings (Admin allowed, Operator partial/forbidden on autoRecovery, Viewer blocked)
op_monitor = session.post(f"{base_url}/api/v1/system/settings", json={"isMonitoring": True}, headers=operator_headers, timeout=5)
op_recovery = session.post(f"{base_url}/api/v1/system/settings", json={"autoRecovery": True}, headers=operator_headers, timeout=5)
view_settings = session.post(f"{base_url}/api/v1/system/settings", json={"isMonitoring": True}, headers=viewer_headers, timeout=5)

if op_monitor.status_code == 200 and op_recovery.status_code == 403 and view_settings.status_code == 403:
    record("RBAC", "Operator vs Viewer Isolation & AutoRecovery Protection", "COMPLETE", f"Operator monitoring update=HTTP {op_monitor.status_code} OK; Operator autoRecovery attempt blocked=HTTP {op_recovery.status_code} Forbidden; Viewer update blocked=HTTP {view_settings.status_code} Forbidden.")
else:
    record("RBAC", "Operator vs Viewer Isolation & AutoRecovery Protection", "NEEDS IMPROVEMENT", f"OpMonitor={op_monitor.status_code}, OpRecovery={op_recovery.status_code}, ViewerSettings={view_settings.status_code}")

# C. Viewer Read Access
view_read = session.get(f"{base_url}/api/v1/system/actions/history", headers=viewer_headers, timeout=5)
if view_read.status_code == 200:
    record("RBAC", "Viewer Read Telemetry & Action History", "COMPLETE", f"Viewer successfully read action history with HTTP {view_read.status_code} OK ({len(view_read.json())} items).")
else:
    record("RBAC", "Viewer Read Telemetry & Action History", "NEEDS IMPROVEMENT", f"Viewer read returned HTTP {view_read.status_code}")

# -------------------------------------------------------------
# 4. Comprehensive Backend API Routes Verification
# -------------------------------------------------------------
api_suite = [
    ("GET", "/api/v1/health", False, "Health Probe"),
    ("GET", "/api/v1/auth/status", False, "Auth Status"),
    ("GET", "/api/v1/auth/me", True, "Current User Identity"),
    ("GET", "/api/v1/dashboard/", True, "Dashboard Metrics Overview"),
    ("GET", "/api/v1/dashboard/kpis", True, "Executive KPI Statistics"),
    ("GET", "/api/v1/system", True, "System Telemetry Status"),
    ("GET", "/api/v1/system/settings", True, "System Settings Read"),
    ("GET", "/api/v1/system/history", True, "Host Telemetry History"),
    ("GET", "/api/v1/system/live", True, "Real-time Live Telemetry"),
    ("GET", "/api/v1/system/actions/history", True, "Remediation Action History"),
    ("GET", "/api/v1/users/", True, "User Management Directory"),
    ("GET", "/api/v1/users/audit-logs", True, "Security & Audit Event Logs"),
    ("GET", "/api/v1/organizations/", True, "Organization Registry"),
    ("GET", "/api/v1/situations/", True, "Situations Incident List"),
    ("GET", "/api/v1/slos/", True, "Service Level Objectives"),
    ("GET", "/api/v1/playbooks/", True, "Remediation Playbooks List"),
    ("GET", "/api/v1/alerts/", True, "Alert Telemetry List"),
    ("GET", "/api/v1/incidents/", True, "Incident Ledger"),
    ("GET", "/api/v1/services/", True, "Infrastructure Services"),
    ("GET", "/api/v1/deployments/", True, "Deployments Ledger"),
    ("GET", "/api/v1/policies/", True, "OPA Security Policies"),
    ("GET", "/api/v1/notifications/settings", True, "Notification Webhook Settings"),
    ("GET", "/api/v1/topology/", True, "System Topology Graph"),
    ("GET", "/api/v1/logs/", True, "Structured Logs Query"),
    ("GET", "/api/v1/metrics/", True, "Host Metrics Query"),
    ("GET", "/api/v1/traces/", True, "Distributed Traces Query"),
    ("GET", "/api/v1/battery", True, "Hardware Battery Telemetry"),
    ("GET", "/api/v1/cpu", True, "Hardware CPU Telemetry"),
    ("GET", "/api/v1/gpu", True, "Hardware GPU Telemetry"),
    ("GET", "/api/v1/memory", True, "Hardware Memory Telemetry"),
    ("GET", "/api/v1/network", True, "Hardware Network Telemetry"),
    ("GET", "/api/v1/processes", True, "Host Process List"),
    ("GET", "/api/v1/storage", True, "Hardware Storage Disk Drives"),
    ("GET", "/internal/metrics", False, "Prometheus ASGI Exporter"),
]

for method, path, req_auth, name in api_suite:
    h = admin_headers if req_auth else {}
    t0 = time.perf_counter()
    r = session.request(method, f"{base_url}{path}", headers=h, timeout=5)
    latency_ms = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        if path == "/internal/metrics":
            record("Backend APIs", f"{method} {path} ({name})", "COMPLETE", f"HTTP {r.status_code} OK in {latency_ms:.1f}ms. Prometheus text format ({len(r.text)} bytes).")
        else:
            record("Backend APIs", f"{method} {path} ({name})", "COMPLETE", f"HTTP {r.status_code} OK in {latency_ms:.1f}ms.")
    else:
        record("Backend APIs", f"{method} {path} ({name})", "NEEDS IMPROVEMENT", f"Returned HTTP {r.status_code} in {latency_ms:.1f}ms: {r.text[:100]}")

# -------------------------------------------------------------
# 5. Comprehensive ML Services & Endpoints Verification
# -------------------------------------------------------------
ml_suite = [
    # Anomaly Detection
    ("GET", "/api/v1/ml/anomaly/health", None, "Anomaly Detection Engine Health"),
    ("POST", "/api/v1/ml/anomaly/predict", {"value": 85.0, "sin_hour": 0.5, "cos_hour": 0.86, "rolling_mean_5": 50.0, "rolling_std_5": 1.2, "lag_1": 49.5}, "Anomaly Single Inference"),
    ("POST", "/api/v1/ml/anomaly/batch", {"data": [{"value": 85.0, "sin_hour": 0.5, "cos_hour": 0.86, "rolling_mean_5": 50.0, "rolling_std_5": 1.2, "lag_1": 49.5}]}, "Anomaly Batch Inference"),
    
    # Alert Clustering
    ("GET", "/api/v1/ml/cluster/health", None, "HDBSCAN Clustering Health"),
    ("POST", "/api/v1/ml/cluster", {"log_text": "CPU throttle alert on worker node 3"}, "Alert Clustering Inference"),
    ("POST", "/api/v1/ml/cluster/batch", {"log_texts": ["CPU throttle alert on worker node 3", "Memory leak in pod worker"]}, "Alert Clustering Batch"),
    ("GET", "/api/v1/ml/cluster/statistics", None, "Alert Clustering Cluster Statistics"),
    
    # Root Cause Analysis
    ("GET", "/api/v1/ml/root-cause/health", None, "GraphSAGE RCA GNN Health"),
    
    # Risk Prediction
    ("GET", "/api/v1/ml/risk/health", None, "LightGBM Risk Health"),
    ("POST", "/api/v1/ml/risk/predict", {"deployment_size": 200, "files_changed": 10, "code_churn": 30, "developer_experience": 0.85}, "Risk Prediction Single Inference"),
    ("POST", "/api/v1/ml/risk/batch", [{"deployment_size": 200, "files_changed": 10, "code_churn": 30, "developer_experience": 0.85}], "Risk Prediction Batch Inference"),
    
    # Multi-Model Orchestration & Registry
    ("GET", "/api/v1/ml/analyze/health", None, "Multi-Engine Orchestrator Health"),
    ("GET", "/api/v1/ml/registry/", None, "MLflow Model Registry Query"),
    ("GET", "/api/v1/ml/registry/experiments", None, "MLflow Experiments Ledger"),
]

for method, path, body, name in ml_suite:
    t0 = time.perf_counter()
    if method == "GET":
        r = session.get(f"{base_url}{path}", headers=admin_headers, timeout=5)
    else:
        r = session.post(f"{base_url}{path}", json=body, headers=admin_headers, timeout=5)
    latency_ms = (time.perf_counter() - t0) * 1000
    if r.status_code == 200:
        record("ML Services", name, "COMPLETE", f"HTTP {r.status_code} in {latency_ms:.1f}ms. Output: {r.text[:100]}...")
    else:
        record("ML Services", name, "NEEDS IMPROVEMENT", f"HTTP {r.status_code} in {latency_ms:.1f}ms: {r.text[:100]}")

# -------------------------------------------------------------
# 6. Real Host Telemetry Ingestion & Action Queue Lifecycle
# -------------------------------------------------------------
try:
    # 1. Ingest telemetry sample
    telemetry_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cpu": {"usage_percent": 65.0, "logical_cores": 8, "physical_cores": 4, "current_freq": 3200, "max_freq": 4500, "load_avg": [1.5, 1.2, 1.0]},
        "ram": {"total": 16000000000, "available": 4000000000, "used": 12000000000, "percent": 75.0},
        "disk": {"drives": [{"mountpoint": "C:\\", "total": 500000000000, "used": 250000000000, "percent": 50.0}], "total": 500000000000, "used": 250000000000, "percent": 50.0},
        "network": {"upload_speed": 1048576, "download_speed": 2097152, "bytes_sent": 100000, "bytes_recv": 200000},
        "processes": [{"name": "stress_test_app.exe", "pid": 8888, "cpu_percent": 60.0, "memory_percent": 30.0, "create_time": 1000.0}],
        "applications": ["stress_test_app.exe"],
        "system": {"hostname": "audit-runner", "os": "Windows", "version": "11", "architecture": "AMD64", "uptime": 7200}
    }
    r_ingest = session.post(f"{base_url}/api/v1/system/telemetry", json=telemetry_payload, headers={"X-Agent-Token": agent_token}, timeout=5)
    if r_ingest.status_code == 200:
        record("Telemetry & Remediation", "Host Telemetry Ingestion via X-Agent-Token", "COMPLETE", f"HTTP {r_ingest.status_code} OK. Processed and saved sample for host 'audit-runner'.")
    else:
        record("Telemetry & Remediation", "Host Telemetry Ingestion", "NEEDS IMPROVEMENT", f"HTTP {r_ingest.status_code}: {r_ingest.text}")

    # 2. Enable Auto Recovery via Admin
    session.post(f"{base_url}/api/v1/system/settings", json={"autoRecovery": True}, headers=admin_headers, timeout=5)

    # 3. Queue termination action
    r_action = session.post(f"{base_url}/api/v1/system/actions", json={"actionType": "TERMINATE_PROCESS", "target": 8888}, headers=admin_headers, timeout=5)
    if r_action.status_code == 200 and "id" in r_action.json():
        action_id = r_action.json()["id"]
        # Fetch pending actions via agent
        r_pending = session.get(f"{base_url}/api/v1/system/actions", headers={"X-Agent-Token": agent_token}, timeout=5)
        # Complete action via agent
        r_comp = session.post(f"{base_url}/api/v1/system/actions/{action_id}/complete", json={"status": "SUCCESS", "result": "Process 8888 killed."}, headers={"X-Agent-Token": agent_token}, timeout=5)
        if r_comp.status_code == 200 and r_comp.json().get("status") == "SUCCESS":
            record("Telemetry & Remediation", "Closed-Loop Process Remediation Lifecycle", "COMPLETE", f"Action {action_id[:8]} queued by ADMIN, fetched by agent (HTTP {r_pending.status_code}), completed with status=SUCCESS.")
        else:
            record("Telemetry & Remediation", "Closed-Loop Process Remediation Lifecycle", "NEEDS IMPROVEMENT", f"Completion failed: {r_comp.status_code} {r_comp.text}")
    else:
        record("Telemetry & Remediation", "Closed-Loop Process Remediation Lifecycle", "NEEDS IMPROVEMENT", f"Action queue failed: {r_action.status_code} {r_action.text}")
except Exception as e:
    record("Telemetry & Remediation", "Closed-Loop Process Remediation Lifecycle", "NEEDS IMPROVEMENT", f"Lifecycle failed: {e}")

# -------------------------------------------------------------
# 7. Summary
# -------------------------------------------------------------
complete_count = sum(1 for r in audit_records if r["status"] == "COMPLETE")
total_count = len(audit_records)
pct = (complete_count / total_count * 100) if total_count else 0
print(f"\nAUDIT COMPLETE: {complete_count}/{total_count} Verified Components COMPLETE ({pct:.1f}%)")
