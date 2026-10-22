# Publication Figures (Mermaid)

## 1. Overall Architecture
```mermaid
graph TD
    A[Telemetry / OpenTelemetry] --> B[API Gateway]
    B --> C[FastAPI Backend]
    C --> D[(PostgreSQL)]
    C --> E[AI Orchestrator]
    E --> F[ML Models]
    C --> G[React SPA Mission Control]
    H[Prometheus] --> C
```

## 2. ML Pipeline
```mermaid
flowchart LR
    A[Raw Telemetry] --> B[Isolation Forest: Anomaly]
    B -->|Anomalous| C[SentenceTransformers]
    C --> D[HDBSCAN: Clustering]
    D --> E[GraphSAGE: RCA]
    E --> F[LightGBM: Risk Score]
```

## 3. AI Orchestrator
```mermaid
stateDiagram-v2
    [*] --> Ingest
    Ingest --> DetectAnomaly
    DetectAnomaly --> ClusterAlerts : Anomaly Detected
    DetectAnomaly --> Safe : Normal
    ClusterAlerts --> RootCauseAnalysis
    RootCauseAnalysis --> PredictRisk
    PredictRisk --> FormatResponse
    FormatResponse --> [*]
```

## 4. Deployment Pipeline
```mermaid
flowchart TD
    A[Code Push] --> B[Docker Build]
    B --> C[Run PyTest]
    C --> D[Run TSC]
    D --> E[Docker Compose Up]
    E --> F[Nginx Reverse Proxy]
```

## 5. Docker Architecture
```mermaid
graph TD
    A[Nginx:80] --> B[Frontend: Vite Node]
    A --> C[Backend: FastAPI Uvicorn]
    C --> D[PostgreSQL:5432]
    C --> E[Prometheus:9090]
    C --> F[Promtail/Loki]
```

## 6. Data Flow
```mermaid
sequenceDiagram
    participant User
    participant React
    participant API
    participant DB
    participant ML
    User->>React: View Dashboard
    React->>API: GET /api/v1/ml/analyze
    API->>ML: Run Orchestrator DAG
    ML-->>API: Unified ML JSON
    API->>DB: Log Transaction
    API-->>React: 200 OK + Data
    React-->>User: Render Dashboard
```

## 7. RCA Graph Flow
```mermaid
graph LR
    A[Service Nodes] --> B[Edge Topology]
    A & B --> C[PyTorch Geometric Data]
    C --> D[GraphSAGE Convolution 1]
    D --> E[GraphSAGE Convolution 2]
    E --> F[Log Softmax Classification]
    F --> G[Root Cause Node ID]
```

## 8. Risk Prediction Flow
```mermaid
flowchart TD
    A[Deployment Meta] --> B[Feature Extraction]
    B --> C[Target Encoding]
    C --> D[LightGBM Trees]
    D --> E{Probability > 0.5?}
    E -->|Yes| F[Risk = 1]
    E -->|No| G[Risk = 0]
```

## 9. Sequence Diagram (Alert Processing)
```mermaid
sequenceDiagram
    participant Source
    participant API
    participant HDBSCAN
    Source->>API: POST /alerts
    API->>HDBSCAN: Embed + Cluster
    HDBSCAN-->>API: Cluster IDs
    API-->>Source: Grouped Alerts
```

## 10. Component Diagram
```mermaid
classDiagram
    class OrchestratorService {
        +analyze_telemetry()
    }
    class AnomalyDetector {
        +detect(metrics)
    }
    class AlertClusterer {
        +cluster(alerts)
    }
    class RCAModel {
        +predict_root_cause(graph)
    }
    OrchestratorService --> AnomalyDetector
    OrchestratorService --> AlertClusterer
    OrchestratorService --> RCAModel
```
