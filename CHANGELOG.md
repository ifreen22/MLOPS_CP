# Changelog

All notable changes to the AIOps Sentinel project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-22

### Added
- **Multi-Model ML Intelligence Pipeline:**
  - Multi-variate Isolation Forest anomaly detection engine with cyclical harmonic encodings (`sin_hour`, `cos_hour`) and 5-minute rolling statistics.
  - HDBSCAN unsupervised alert clustering using `all-MiniLM-L6-v2` dense vector representations.
  - GraphSAGE Graph Neural Network for microservice topology root cause analysis using PyTorch Geometric.
  - LightGBM Gradient Boosting deployment risk classifier with TreeSHAP explainability attributions.
  - Unified multi-model ML Orchestrator executing automated evaluation DAGs.
  - MLflow Model Registry tracking, experiment ledger, and stage transition workflows.
- **Hardware Telemetry & Closed-Loop Remediation:**
  - Dedicated native Windows OS telemetry agent (`windows_agent.py`) capturing CPU frequencies, core allocations, RAM, disk partitions, net I/O, and process tables.
  - Cryptographically authenticated `ActionQueue` with `X-Agent-Token` authorization.
  - Guarded closed-loop process termination (`TERMINATE_PROCESS`) with verification and audit callbacks.
- **Enterprise Security & Cryptographic RBAC:**
  - 3-tier Role-Based Access Control matrix (`ADMIN`, `OPERATOR`, `VIEWER`).
  - Bcrypt password hashing and JWT access tokens.
  - Open Policy Agent (OPA) integration with live in-browser Rego editor and validation endpoint.
  - Tamper-evident `AuditLog` recording all user, agent, and remediation events.
- **Frontend SPA Dashboard:**
  - High-tech Glassmorphism design system built on React 18, Vite, Tailwind CSS, Lucide icons, and Recharts.
  - 8 core operational views: Mission Control, Situation Room, Alert Clustering, Root Cause Graph, Remediation Playbooks, SLO Dashboard, Audit Logs, and Settings.
- **Full Observability Microservices Stack:**
  - Docker Compose orchestration of 12 production services: FastAPI, React/Vite, PostgreSQL 15, Redis 7, Prometheus, Grafana, Loki, Promtail, OpenTelemetry Collector, cAdvisor, Node Exporter, and Nginx.
- **Turnkey Packaging & Developer Experience:**
  - Turnkey setup automation scripts (`setup.ps1`, `setup.sh`).
  - Automated operational lifecycle scripts (`run.ps1`, `run.sh`, `stop.ps1`, `stop.sh`, `reset.ps1`).
  - Automated 24-component health audit utility (`healthcheck.ps1`, `healthcheck.sh`).
  - Zero-to-hero installation guide (`INSTALLATION.md`), system architecture (`ARCHITECTURE.md`), ML documentation (`ML_MODELS.md`), and API reference (`API_REFERENCE.md`).
- **Comprehensive Verification & Testing:**
  - 124 passing Pytest backend unit, integration, and performance tests.
  - 95.42% measured line and branch code coverage.
  - 3 passing Vitest component test suites.
  - 8 passing Playwright end-to-end browser automation workflows in Chromium.
