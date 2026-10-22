import json
import urllib.request
import urllib.parse
import urllib.error

base_url = "http://127.0.0.1:8000"

# 1. API Health check
print("=== 1. API System Health Check ===")
req = urllib.request.Request(f"{base_url}/api/v1/health")
with urllib.request.urlopen(req) as resp:
    status_code = resp.getcode()
    body = json.loads(resp.read().decode("utf-8"))
    print(f"Status Code: {status_code}")
    print(f"Response: {json.dumps(body, indent=2)}")
    assert status_code == 200
    assert body.get("status") == "ok"
    print("API Health Check: PASS")

# 2. Authenticate
print("\n=== 2. Authenticate Admin ===")
login_form = urllib.parse.urlencode({
    "username": "admin@localhost",
    "password": "caXK6HxqFUVS5buIi1ayl2wEA2w4kTsI8rtuCRj_9rA"
}).encode("utf-8")

login_req = urllib.request.Request(
    f"{base_url}/api/v1/auth/login",
    data=login_form,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    method="POST"
)
with urllib.request.urlopen(login_req) as resp:
    login_body = json.loads(resp.read().decode("utf-8"))
    token = login_body["access_token"]
    print(f"Authenticated successfully. User: {login_body['user']['email']}, Role: {login_body['user']['role']}")

auth_headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# 3. ML Health Endpoints
print("\n=== 3. ML Service Health Endpoints ===")

endpoints = [
    ("/api/v1/ml/cluster/health", "Alert Clustering Health"),
    ("/api/v1/ml/risk/health", "Risk Prediction Health"),
    ("/api/v1/ml/root-cause/health", "Root Cause Analysis Health"),
    ("/api/v1/ml/analyze/health", "ML Orchestrator Health"),
]

for path, label in endpoints:
    req = urllib.request.Request(f"{base_url}{path}", headers=auth_headers)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        print(f"\n{label} ({path}) [Status: {resp.getcode()}]:")
        print(json.dumps(data, indent=2))
        assert resp.getcode() == 200

# 4. ML Prediction Endpoints
print("\n=== 4. ML Prediction Endpoints ===")

# Anomaly prediction
anomaly_payload = json.dumps({
    "value": 85.0,
    "sin_hour": 0.5,
    "cos_hour": 0.86,
    "rolling_mean_5": 50.0,
    "rolling_std_5": 1.2,
    "lag_1": 49.5
}).encode("utf-8")

req = urllib.request.Request(
    f"{base_url}/api/v1/ml/anomaly/predict",
    data=anomaly_payload,
    headers=auth_headers,
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print(f"\nAnomaly Prediction Response [Status: {resp.getcode()}]:")
    print(json.dumps(res, indent=2))
    assert resp.getcode() == 200

# Risk prediction
risk_payload = json.dumps({
    "deployment_size": 250,
    "files_changed": 12,
    "code_churn": 45,
    "developer_experience": 0.85
}).encode("utf-8")

req = urllib.request.Request(
    f"{base_url}/api/v1/ml/risk/predict",
    data=risk_payload,
    headers=auth_headers,
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print(f"\nRisk Prediction Response [Status: {resp.getcode()}]:")
    print(json.dumps(res, indent=2))
    assert resp.getcode() == 200

# Cluster prediction
cluster_payload = json.dumps({
    "log_text": "High CPU utilization on host worker-node-01 memory pressure detected"
}).encode("utf-8")

req = urllib.request.Request(
    f"{base_url}/api/v1/ml/cluster",
    data=cluster_payload,
    headers=auth_headers,
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print(f"\nCluster Prediction Response [Status: {resp.getcode()}]:")
    print(json.dumps(res, indent=2))
    assert resp.getcode() == 200

print("\n=======================================================")
print("ALL API HEALTH CHECKS AND ML ENDPOINT CHECKS: PASS")
print("=======================================================")
