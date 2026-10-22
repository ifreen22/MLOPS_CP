# AIOps Sentinel — Project Structure & Directory Layout

This document details the code organization, architectural boundaries, and purpose of every directory and key module across the AIOps Sentinel repository.

---

## 1. Directory Tree Overview

```text
MLOPS_CP/
├── .github/                       # GitHub Actions workflows & issue templates
│   ├── ISSUE_TEMPLATE/            # Standardized bug, feature, and doc templates
│   └── workflows/
│       └── ci-cd.yml              # CI pipeline (lint, test, coverage, playwright, docker)
│
├── aiops-sentinel/                # Production React 18 / Vite Frontend Application
│   ├── e2e/                       # Playwright browser end-to-end automation suites
│   │   └── production.spec.ts     # 8 full user interaction workflows across all views
│   ├── src/
│   │   ├── components/            # Reusable UI widgets, navigation, theme toggles
│   │   │   ├── layout/            # AppLayout, sidebar navigation, headers
│   │   │   └── ThemeToggle.tsx    # Dark/light theme switcher component
│   │   ├── features/              # Feature-driven modular views
│   │   │   ├── alert-clustering/  # HDBSCAN clustering visualizations & mode toggles
│   │   │   ├── auth/              # Login screen, JWT storage, credential management
│   │   │   ├── change-intelligence/# Deployment risk charts & SHAP risk factors
│   │   │   ├── mission-control/   # Real-time hardware telemetry gauges & controls
│   │   │   ├── playbooks/         # Remediation runbooks index & execution modals
│   │   │   ├── root-cause/        # Interactive GraphSAGE topological RCA canvas
│   │   │   ├── settings/          # OPA Rego editor, service tiers, webhook settings
│   │   │   ├── situations/        # Situation Room, incident ledger, action buttons
│   │   │   └── slo/               # SLO compliance dashboards & error budget tracking
│   │   ├── services/
│   │   │   └── api.ts             # Axios HTTP client, Zod schemas, auth interceptors
│   │   ├── App.tsx                # React Router v6 routing & route authorization guards
│   │   └── main.tsx               # DOM bootstrap with TanStack Query provider
│   ├── Dockerfile                 # Multi-stage Nginx production build
│   ├── package.json               # NPM dependencies & test scripts
│   ├── playwright.config.ts       # Playwright E2E configuration & webServer specs
│   └── vitest.config.ts           # Vitest unit test runner config with happy-dom
│
├── backend/                       # Core FastAPI & Python Microservice Backend
│   ├── agent/
│   │   └── windows_agent.py       # Telemetry collection & process remediation daemon
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── controllers/   # REST controllers for all system domains
│   │   │       │   ├── alert_controller.py
│   │   │       │   ├── auth_controller.py
│   │   │       │   ├── dashboard_controller.py
│   │   │       │   ├── incident_controller.py
│   │   │       │   ├── ml_anomaly_controller.py
│   │   │       │   ├── ml_alert_clustering_controller.py
│   │   │       │   ├── ml_rca_controller.py
│   │   │       │   ├── ml_risk_controller.py
│   │   │       │   ├── ml_orchestrator_controller.py
│   │   │       │   ├── ml_registry_controller.py
│   │   │       │   ├── notification_controller.py
│   │   │       │   ├── playbook_controller.py
│   │   │       │   ├── policy_controller.py
│   │   │       │   ├── situation_controller.py
│   │   │       │   ├── slo_controller.py
│   │   │       │   ├── system_controller.py
│   │   │       │   ├── telemetry_controller.py
│   │   │       │   ├── topology_controller.py
│   │   │       │   └── user_controller.py
│   │   │       └── router.py      # Unified APIRouter mount with auth dependencies
│   │   ├── core/
│   │   │   ├── auth.py            # Bcrypt hashing, JWT generation, RBAC decorators
│   │   │   ├── db.py              # Prisma ORM connection lifecycle & bootstrap
│   │   │   └── rate_limit.py      # SlowAPI sliding-window rate limiters
│   │   ├── ml_services/           # Machine learning models, pipelines & trainers
│   │   │   ├── alert_clustering/  # HDBSCAN clustering engine & SentenceTransformers
│   │   │   ├── anomaly_detection/ # Isolation Forest model with cyclical feature engineering
│   │   │   ├── risk_prediction/   # LightGBM classifier & TreeSHAP explainers
│   │   │   ├── root_cause/        # GraphSAGE GNN in PyTorch Geometric
│   │   │   ├── ml_orchestrator.py # Multi-model unified DAG pipeline
│   │   │   └── registry.py        # MLflow model tracking, versions & stages
│   │   ├── schemas/               # Pydantic v2 data transfer schemas
│   │   └── main.py                # FastAPI ASGI app bootstrap, middleware, lifespan
│   ├── prisma/
│   │   └── schema.prisma          # PostgreSQL relational schema (users, telemetry, etc.)
│   ├── tests/                     # 124 comprehensive backend test suites (>95% coverage)
│   ├── .coveragerc                # Coverage instrumentation settings & branch coverage
│   ├── Dockerfile                 # Python 3.13 lightweight container definition
│   ├── pytest.ini                 # Pytest runner configuration
│   ├── requirements.txt           # Production Python dependencies
│   └── requirements-test.txt      # Testing & coverage toolchain dependencies
│
├── observability/                 # Observability & Monitoring Infrastructure Configs
│   ├── grafana/
│   │   ├── dashboards/            # Pre-configured Grafana monitoring dashboards
│   │   └── provisioning/          # Automated datasource & dashboard providers
│   ├── loki/                      # Grafana Loki storage & schema configurations
│   ├── otel-collector/            # OpenTelemetry Collector pipelines & exporters
│   ├── prometheus/                # Prometheus scrape targets & alerting rules
│   └── promtail/                  # Promtail container log scrapers
│
├── docs/                          # Specialized architecture and verification reports
│
├── .env.example                   # Root environment configuration template
├── .gitattributes                 # Git line-ending and binary tracking rules
├── .gitignore                     # Enterprise-grade Git exclusion rules
├── docker-compose.yml             # 12-microservice local production orchestration
├── nginx.conf                     # Ingress reverse proxy configuration
├── windows_agent.py               # Standalone root launcher for Windows Host Daemon
├── windows-agent-requirements.txt # Minimal dependencies for host telemetry agent
│
├── setup.ps1 / setup.sh           # Automated turnkey installation scripts
├── run.ps1 / run.sh               # Service launch and background agent scripts
├── stop.ps1 / stop.sh             # Graceful teardown scripts
├── reset.ps1                      # Environment wipe and database reset utility
└── healthcheck.ps1 / healthcheck.sh# Automated 24-component health audit utility
```

---

## 2. Layer-by-Layer Architectural Separation

### 2.1 Presentation Layer (`aiops-sentinel/`)
- Pure client-side single-page application built on React 18, bundled with Vite.
- Implements code-splitting and route-level lazy loading (`React.lazy`, `Suspense`).
- Employs TanStack Query for cache invalidation and real-time polling synchronization with backend telemetry feeds.

### 2.2 Application & Business Logic (`backend/app/`)
- Implements the Model-Controller-Service pattern:
  - **Controllers:** Handle HTTP input validation, serialize Pydantic responses, and enforce RBAC guards (`require_role(["ADMIN", "OPERATOR"])`).
  - **Core:** Houses cryptographic security primitives, JWT tokens, and Prisma database client lifecycles.
  - **ML Services:** Contains algorithmic models, vectorizers, and graph neural network trainers isolated from HTTP transport logic.

### 2.3 Data & Persistence (`backend/prisma/`)
- Single source of truth for the database schema in [`schema.prisma`](file:///c:/Users/Ifreen/Downloads/MLOPS_CP/backend/prisma/schema.prisma).
- Automated migrations and type-safe schema synchronization across Python (`prisma-client-py`) and TypeScript (`@prisma/client`).

### 2.4 Host Daemon (`windows_agent.py`)
- Independent background daemon running on the host OS.
- Communicates exclusively over HTTP with standard REST payloads, requiring zero socket sharing or privileged Docker socket mounts.
