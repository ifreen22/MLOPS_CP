# AIOps Sentinel — Frequently Asked Questions (FAQ)

---

## 1. General Questions

### Q: What is AIOps Sentinel?
**A:** AIOps Sentinel is an autonomous IT operations (AIOps) and telemetry observability platform. It monitors host operating systems and containerized microservices in real time, detects metric anomalies via machine learning, clusters related alerts into single incidents (Situations) to eliminate alert fatigue, isolates root cause nodes using Graph Neural Networks (GraphSAGE), and executes guarded self-healing remediations.

### Q: How is this different from traditional Prometheus and Grafana?
**A:** Traditional monitoring setups are **passive and descriptive**—they tell you *after* a threshold has breached and require human engineers to triage the issue. AIOps Sentinel is **active and prescriptive**:
1. It detects subtle multi-variate anomalies before hard thresholds fail.
2. It groups hundreds of redundant alerts into a single actionable incident using natural language embeddings.
3. It maps microservice dependencies to pinpoint the exact root cause node.
4. It can automatically terminate runaway processes or trigger self-healing playbooks.

---

## 2. Machine Learning & Telemetry

### Q: Does the auto-remediation actually terminate processes, or is it simulated?
**A:** It is **100% genuine and closed-loop**. Unlike toy prototypes that merely record a `simulated_target_healthy` database flag, AIOps Sentinel features a real host daemon (`windows_agent.py`) that polls an authenticated database `ActionQueue`, verifies the process PID against safety policies, terminates the process using native operating system calls (`psutil`), and reports execution logs back with cryptographic audit confirmation.

### Q: Which Machine Learning models are implemented?
**A:** The platform includes 4 distinct production machine learning models and an orchestrator:
1. **Isolation Forest:** Multi-variate time-series hardware anomaly detection with cyclical harmonic features.
2. **HDBSCAN + SentenceTransformers (`all-MiniLM-L6-v2`):** Unsupervised dense-vector alert clustering.
3. **GraphSAGE GNN:** Topological microservice dependency root cause analysis built on PyTorch Geometric.
4. **LightGBM Classifier:** Pre-deployment change risk scoring with TreeSHAP explainability.
5. **ML Orchestrator:** Unified DAG combining all models into real-time health evaluations.

### Q: Where does the telemetry data come from?
**A:** Real telemetry data is streamed directly from your host machine via `windows_agent.py`. It samples genuine CPU frequencies, load averages, memory partitions, disk reads/writes, network socket throughput, and running OS processes.

---

## 3. Architecture & Security

### Q: How is security and authorization enforced?
**A:** The platform implements enterprise-grade Role-Based Access Control (RBAC) across three distinct tiers:
- **`ADMIN`:** Complete administrative control over users, organizations, system settings, and auto-recovery activation.
- **`OPERATOR`:** Operations access to toggle telemetry monitoring and resolve situations. Strictly forbidden (HTTP 403) from creating users or enabling auto-recovery.
- **`VIEWER`:** Read-only visibility across dashboards, charts, and audit histories.
All API routes are protected by bcrypt password hashing and short-lived JWT bearer tokens.

### Q: Why use Prisma ORM instead of traditional SQLAlchemy?
**A:** Prisma provides unified, type-safe schema synchronization across both our Python backend (`prisma-client-py`) and our TypeScript tooling (`@prisma/client`), eliminating schema drift between backend models and frontend data representations.

---

## 4. Testing & Verification

### Q: How is the codebase tested?
**A:** The repository maintains continuous testing across the entire stack:
- **Backend:** 124 passing Pytest tests with **95.42% measured line and branch coverage**.
- **Frontend Unit:** Vitest component tests verifying theme switching, telemetry rendering, and auth.
- **Frontend E2E:** 8 passing Playwright browser automation tests running against Chromium, clicking every tab and action button across all 8 views.
- **System Audit:** Automated script (`healthcheck.ps1`) verifying all 12 Docker containers and 11 HTTP health probes.

### Q: Can I run this project on Linux or macOS?
**A:** Yes. The entire microservice stack runs inside Docker Compose on any operating system supporting Docker (Ubuntu, Debian, macOS, or Windows WSL 2). We provide both PowerShell (`.ps1`) and Bash (`.sh`) setup scripts.
