# AIOps Sentinel — API Reference Manual

> **Base URL:** `http://localhost:8000` (or `http://localhost:8081/api/v1` via Nginx ingress)  
> **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
> **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Table of Contents
1. [Authentication & Security](#1-authentication--security)
2. [User Management & RBAC](#2-user-management--rbac)
3. [System Telemetry & Self-Healing Actions](#3-system-telemetry--self-healing-actions)
4. [Hardware Telemetry Probes](#4-hardware-telemetry-probes)
5. [Incidents, Situations & Alerts](#5-incidents-situations--alerts)
6. [Remediation Playbooks](#6-remediation-playbooks)
7. [Service Level Objectives (SLOs)](#7-service-level-objectives-slos)
8. [Open Policy Agent (OPA) Security Policies](#8-open-policy-agent-opa-security-policies)
9. [Machine Learning Engines & Registry](#9-machine-learning-engines--registry)
10. [Observability, Logs, Metrics & Traces](#10-observability-logs-metrics--traces)

---

## 1. Authentication & Security

All authenticated endpoints require a valid JWT passed in the HTTP Authorization header:
```http
Authorization: Bearer <your-access-token>
```

### `POST /api/v1/auth/login`
- **Description:** Authenticates user credentials via OAuth2 password form flow.
- **Content-Type:** `application/x-www-form-urlencoded`
- **Request Body:**
  - `username` (string, required): User email address.
  - `password` (string, required): User password.
- **Response `200 OK`:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "expires_in": 1800,
    "user": {
      "id": "usr_94f8a1",
      "email": "admin@localhost",
      "role": "ADMIN",
      "organizationId": "org_01"
    }
  }
  ```

### `GET /api/v1/auth/me`
- **Description:** Returns the authenticated user's profile and RBAC role.
- **Authorization:** `Bearer Token` (`ADMIN`, `OPERATOR`, `VIEWER`)
- **Response `200 OK`:** Profile object.

### `GET /api/v1/auth/status`
- **Description:** Reports whether an administrator account has been bootstrapped.
- **Authorization:** None (Public)

---

## 2. User Management & RBAC

### `GET /api/v1/users/`
- **Description:** Lists all users in the organization.
- **Authorization:** `ADMIN` role only.
- **Response `200 OK`:** Array of user records.

### `POST /api/v1/users/`
- **Description:** Provisions a new user account.
- **Authorization:** `ADMIN` role only.
- **Request Body:**
  ```json
  {
    "email": "operator@sentinel.local",
    "password": "SecurePassword123!",
    "firstName": "Operations",
    "lastName": "Engineer",
    "role": "OPERATOR"
  }
  ```
- **Response `201 Created`:** Created user object.

### `GET /api/v1/users/audit-logs`
- **Description:** Queries the tamper-evident security audit log recording user and agent events.
- **Authorization:** `ADMIN` or `OPERATOR`.

---

## 3. System Telemetry & Self-Healing Actions

### `POST /api/v1/system/telemetry`
- **Description:** Ingests live hardware metrics and process tables from the host daemon.
- **Authorization:** `X-Agent-Token` header.
- **Request Body:**
  ```json
  {
    "timestamp": "2026-10-22T21:10:00Z",
    "cpu": { "usage_percent": 45.2, "logical_cores": 8, "physical_cores": 4 },
    "ram": { "total": 17179869184, "used": 8589934592, "percent": 50.0 },
    "disk": { "total": 512110190592, "used": 256055095296, "percent": 50.0 },
    "network": { "upload_speed": 1048576, "download_speed": 2097152 },
    "processes": [
      { "pid": 4128, "name": "python.exe", "cpu_percent": 12.5, "memory_percent": 4.1 }
    ],
    "system": { "hostname": "node-prod-01", "os": "Windows", "version": "11" }
  }
  ```
- **Response `200 OK`:** `{"status": "recorded", "id": "rec_0918"}`

### `GET /api/v1/system/settings`
- **Description:** Retrieves system monitoring state, autoRecovery status, and polling interval.

### `POST /api/v1/system/settings`
- **Description:** Updates system telemetry settings.
- **Authorization:**
  - `isMonitoring`: `ADMIN`, `OPERATOR`.
  - `autoRecovery`: `ADMIN` only (Operators receive `HTTP 403 Forbidden`).

### `POST /api/v1/system/actions`
- **Description:** Queues a guarded self-healing remediation action.
- **Authorization:** `ADMIN` or `OPERATOR`.
- **Request Body:**
  ```json
  {
    "actionType": "TERMINATE_PROCESS",
    "target": 8888
  }
  ```

### `GET /api/v1/system/actions`
- **Description:** Polled by the host daemon to fetch `PENDING` actions.
- **Authorization:** `X-Agent-Token` header.

### `POST /api/v1/system/actions/{action_id}/complete`
- **Description:** Reports action completion status back to the platform.
- **Authorization:** `X-Agent-Token` header.
- **Request Body:**
  ```json
  {
    "status": "SUCCESS",
    "result": "Process 8888 terminated safely."
  }
  ```

---

## 4. Hardware Telemetry Probes

Dedicated sub-second endpoints for granular hardware monitoring:
- `GET /api/v1/cpu` — Instantaneous CPU frequency, load averages, and core distributions.
- `GET /api/v1/memory` — RAM and swap memory allocation stats.
- `GET /api/v1/storage` — Mounted storage partitions, filesystems, and usage.
- `GET /api/v1/network` — Network adapter speeds and byte throughput.
- `GET /api/v1/processes` — Current top processes sorted by CPU and memory impact.
- `GET /api/v1/gpu` — GPU hardware load, VRAM, and temperature (if available).
- `GET /api/v1/battery` — Mobile/laptop battery charge state and AC power status.

---

## 5. Incidents, Situations & Alerts

### `GET /api/v1/alerts/`
- **Description:** Queries raw alert telemetry stream.

### `POST /api/v1/alerts/`
- **Description:** Ingests an alert from PromQL alertmanagers or external monitoring systems.

### `GET /api/v1/situations/`
- **Description:** Lists all clustered incidents (Situations) grouped by the HDBSCAN NLP engine.

### `POST /api/v1/situations/{id}/resolve`
- **Description:** Marks a situation and its underlying correlated alerts as resolved.

---

## 6. Remediation Playbooks

### `GET /api/v1/playbooks/`
- **Description:** Retrieves searchable catalog of pre-configured runbooks (e.g. Restart Pod, Drain Node, Flush Cache).

### `POST /api/v1/playbooks/{id}/execute`
- **Description:** Triggers audited execution of a playbook against a target service or host.

---

## 7. Service Level Objectives (SLOs)

### `GET /api/v1/slos/`
- **Description:** Computes real-time compliance percentages and remaining error budgets from historical host telemetry over sliding time windows (1h, 24h, 7d).

### `POST /api/v1/slos/`
- **Description:** Defines a new Service Level Objective.
- **Request Body:**
  ```json
  {
    "name": "Host Memory Headroom",
    "metric": "memory_usage",
    "threshold": 85.0,
    "targetPercent": 99.5,
    "windowHours": 24
  }
  ```

---

## 8. Open Policy Agent (OPA) Security Policies

- `GET /api/v1/policies/` — Retrieves active Rego policy rules.
- `POST /api/v1/policies/` — Deploys a new Rego policy definition.
- `POST /api/v1/policies/validate` — Dry-runs a Rego policy against an arbitrary JSON input payload.

---

## 9. Machine Learning Engines & Registry

### Anomaly Detection
- `GET /api/v1/ml/anomaly/health` — Anomaly detection engine status.
- `POST /api/v1/ml/anomaly/predict` — Single observation anomaly scoring.
- `POST /api/v1/ml/anomaly/batch` — High-throughput batch anomaly scoring.

### Alert Intelligence & Clustering
- `GET /api/v1/ml/cluster/health` — Clusterer engine status.
- `POST /api/v1/ml/cluster` — Scores an alert string against cluster centroids.
- `POST /api/v1/ml/cluster/batch` — Batch clusters an array of alert strings.
- `GET /api/v1/ml/cluster/statistics` — Open alerts vs situation clustering ratio.
- `POST /api/v1/ml/cluster/run` — Executes end-to-end alert clustering on open DB alerts.

### Root Cause Analysis (RCA)
- `GET /api/v1/ml/root-cause/health` — GraphSAGE GNN engine readiness.
- `POST /api/v1/ml/root-cause/predict` — Runs graph neural network neighborhood inference.
- `POST /api/v1/ml/root-cause/train` — Retrains GNN weights on updated topology graphs.

### Deployment Risk Prediction
- `GET /api/v1/ml/risk/health` — LightGBM model readiness.
- `POST /api/v1/ml/risk/predict` — Scores commit and deployment risk with TreeSHAP explanations.
- `POST /api/v1/ml/risk/batch` — Batch deployment risk prediction.

### Multi-Model Orchestrator & Registry
- `GET /api/v1/ml/analyze/health` — Unified orchestrator DAG readiness.
- `GET /api/v1/ml/registry/` — Lists active models in the MLflow model registry.
- `GET /api/v1/ml/registry/experiments` — Queries MLflow experiment tracking history.

---

## 10. Observability, Logs, Metrics & Traces

- `GET /api/v1/health` — Central platform liveness and readiness probe.
- `GET /internal/metrics` — ASGI Prometheus metric scraper exporting standard OpenMetrics text.
- `GET /api/v1/logs/` — Queries structured application and container logs.
- `GET /api/v1/metrics/` — Ingests or queries timeseries metrics.
- `GET /api/v1/traces/` — Ingests or queries OpenTelemetry trace spans.
- `GET /api/v1/topology/` — Renders graph topology nodes and directed dependency edges.
