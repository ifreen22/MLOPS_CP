# Telemetry & Data Platform Architecture
**Project**: AIOps Sentinel – Self-Healing Cloud Platform  
**Phase**: Phase 2 (Telemetry & Data Platform)  

## 1. Data Flow Architecture
The telemetry pipeline is designed to simulate a real-world enterprise Kubernetes environment:
1. **Data Generators**: Simulated microservices (`checkout-service`, `auth-api`, etc.) push synthetic metrics, logs, traces, and Kubernetes events into the ingestion layer.
2. **Ingestion Layer (FastAPI)**: REST endpoints receive POST payloads mimicking Prometheus (`/api/v1/metrics`), Loki (`/api/v1/logs`), and OpenTelemetry (`/api/v1/traces`).
3. **Storage Layer (PostgreSQL)**: Prisma ORM validates and persists the raw telemetry data into a normalized, strongly-typed schema.
4. **API Layer**: Fast-read endpoints serve the structured telemetry data to the frontend, complete with pagination (`skip`, `limit`) and time-range filtering (`start_time`, `end_time`).
5. **Presentation Layer**: The React UI polls the REST API using `@tanstack/react-query` (`refetchInterval: 5000`) for live Dashboard updates, Topology graphs, and Situation Room tracking.

## 2. Database Schema Overview
The Prisma Schema (`schema.prisma`) has been extended to support the full K8s topology and future Machine Learning metadata:

### Kubernetes Topology
- `Cluster`: Top-level environment (e.g., `us-east-1-prod-cluster`).
- `Namespace`: Logical isolation (e.g., `default`, `kube-system`).
- `Node`: Underlying compute instances (`EC2`).
- `Pod`: Ephemeral workloads tied to `Nodes` and `Namespaces`.
- `Service`: Logical application boundaries (`checkout-service`).
- `Deployment`: Code rollout tracking and versioning.

### Telemetry & Observability
- `Metric`: CPU/Memory consumption, disk IO, network latency.
- `Log`: Application standard output with severity levels.
- `Trace`: Distributed spans tracking request propagation.
- `K8sEvent`: Native Kubernetes control plane events (e.g., CrashLoopBackOff, OOMKilled).

### AIOps & Machine Learning (Future-Proofing)
- `Incident` / `Alert`: Correlated degradation events.
- `AlertCluster`: Groupings of raw alerts compressed by ML.
- `Prediction` / `RiskScore`: Output from anomaly and risk models.
- `Recommendation`: AI-driven remediation suggestions.
- `MLExperiment`: Audit tracking for model versions and hyperparameters.

## 3. API Endpoints

### Ingestion (POST)
- `POST /api/v1/metrics`: Accepts Prometheus-style metrics arrays.
- `POST /api/v1/logs`: Accepts structured JSON logs (mimicking Fluentd/Loki).
- `POST /api/v1/traces`: Accepts OpenTelemetry span payloads.
- `POST /api/v1/events`: Accepts Kubernetes control plane events.

### Consumption (GET)
All GET endpoints accept `?skip=0&limit=100&start_time=ISO8601&end_time=ISO8601`.
- `GET /api/v1/metrics`: Query raw telemetry series.
- `GET /api/v1/logs`: Search application logs.
- `GET /api/v1/traces`: Retrieve distributed traces for root cause analysis.
- `GET /api/v1/incidents`: Pull correlated multi-alert situations.
- `GET /api/v1/alerts`: Pull raw stream alerts.
- `GET /api/v1/deployments`: Audit code rollouts.
- `GET /api/v1/services`: Get service health catalog.
- `GET /api/v1/topology?env=prod`: Retrieve the dynamic K8s service dependency mesh.

## 4. Telemetry Generators
`app/data_seed.py` acts as the primary telemetry generator:
- **Topology Generation**: Scaffolds a virtual 3-node Kubernetes cluster with 5 microservices running 15 pods total.
- **Metric Simulation**: Iterates over a 60-minute historical window, generating baseline CPU/Memory traffic.
- **Incident Injection**: Injects deterministic anomalies (e.g., `checkout-service` CPU spiking from 30% to 99%), followed by generating corresponding `ERROR` logs and `CRITICAL` alerts.

## 5. Future Integration Points
- **Message Brokers**: Introduce Apache Kafka or Redis Pub/Sub between the ingestion endpoints and the PostgreSQL database to handle extreme high-throughput telemetry bursting.
- **WebSockets**: Transition the frontend from 5-second REST polling to real-time WebSockets for sub-second Topology graph rendering.
- **Timeseries Database**: Migrate the `Metric` and `Log` tables from PostgreSQL to TimescaleDB or ClickHouse as data volume scales beyond standard relational capabilities.
- **ML Integration**: Connect the stubbed `app/ml_services/` classes to load PyTorch `.pt` models to asynchronously process the telemetry payloads written to the DB.
