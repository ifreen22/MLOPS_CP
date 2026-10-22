# AIOps Sentinel v1.0.0 — General Availability Release Notes

**Release Date:** October 2026  
**Status:** Production Ready (GA)  
**Test Suite Status:** 124/124 Tests Passing (95.42% Coverage) | 8/8 Playwright E2E Tests Passing | 12/12 Docker Services Healthy

---

## 1. Release Highlights

AIOps Sentinel v1.0.0 marks the first official general availability release of the enterprise-grade autonomous IT operations and self-healing telemetry platform.

### Core Capabilities Introduced in v1.0.0
- **Multi-Model Intelligence Pipeline:**
  - Integrated 4 distinct ML architectures: Time-Series Anomaly Detection (Isolation Forest), Alert Clustering (HDBSCAN + SentenceTransformers), Root Cause Analysis (GraphSAGE GNN in PyTorch Geometric), and Deployment Risk Prediction (LightGBM with TreeSHAP).
  - Multi-Engine ML Orchestrator executing automated health scoring DAGs.
  - MLflow Model Registry integration with automated versioning and stage transitions.
- **Closed-Loop Hardware Remediation:**
  - Native Windows OS telemetry daemon (`windows_agent.py`) streaming sub-second CPU, RAM, disk, network, and process metrics into PostgreSQL.
  - Authenticated `ActionQueue` enabling guarded termination of rogue high-impact processes (`TERMINATE_PROCESS`) with execution verification.
- **Enterprise Security & Cryptographic RBAC:**
  - 3-tier Role-Based Access Control matrix (`ADMIN`, `OPERATOR`, `VIEWER`).
  - Strict isolation: Operators can toggle monitoring but are blocked (HTTP 403) from activating autonomous recovery; Viewers are restricted to read-only access.
  - Bcrypt password hashing, JWT bearer tokens, and Open Policy Agent (OPA) with in-browser Rego policy editing.
- **Full-Stack Observability Stack:**
  - 12 pre-configured microservices: FastAPI, React/Vite, PostgreSQL 15, Redis 7, Prometheus, Grafana, Loki, Promtail, OpenTelemetry Collector, cAdvisor, Node Exporter, and Nginx.
- **Enterprise Developer Experience & Turnkey Setup:**
  - Turnkey setup scripts (`setup.ps1` / `setup.sh`) and health check audit tools (`healthcheck.ps1` / `healthcheck.sh`).
  - Zero-to-hero installation documentation covering fresh Windows, Linux, and macOS environments.

---

## 2. Test & Verification Metrics

- **Backend Pytest Tests:** 124 passed (0 failures, 0 errors).
- **Line & Branch Coverage:** **95.42%** (2,884 statements, 568 branches, strictly above the 95.01% release gate).
- **Frontend Unit Tests:** 3 test files, 3 passed (Vitest + happy-dom).
- **Playwright End-to-End Tests:** 8/8 passing across all views in Chromium.
- **Docker Stack Health:** 12/12 containers running and verified healthy.

---

## 3. Breaking Changes & Upgrade Path
- Initial release. No prior upgrade migrations required.
