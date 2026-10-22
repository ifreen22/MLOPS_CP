import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# ==========================================
# ARCHITECTURE DIAGRAMS
# ==========================================

high_level = """# High-Level Architecture
This diagram outlines the complete AIOps Sentinel platform, depicting how the frontend, backend, ML engines, database, and observability layers interact.

```mermaid
flowchart TD
    subgraph Client Layer
        UI[React + Vite SPA]
    end

    subgraph Edge Layer
        Nginx[Nginx Reverse Proxy]
    end

    subgraph Application Layer
        API[FastAPI Backend]
        Orchestrator[AI Orchestrator Engine]
    end

    subgraph ML Pipeline Layer
        AD[Anomaly Detection - Isolation Forest]
        AC[Alert Clustering - HDBSCAN]
        RCA[Root Cause Analysis - GraphSAGE]
        RP[Risk Prediction - LightGBM]
    end

    subgraph Data Layer
        PG[(PostgreSQL via Prisma)]
        Redis[(Redis Cache)]
    end

    subgraph Observability Layer
        Prometheus[Prometheus]
        Grafana[Grafana]
        Loki[Loki]
        Otel[OpenTelemetry Collector]
    end

    UI -->|HTTPS| Nginx
    Nginx -->|Route /api| API
    Nginx -->|Route /| UI
    
    API <--> Orchestrator
    Orchestrator --> AD
    Orchestrator --> AC
    Orchestrator --> RCA
    Orchestrator --> RP
    
    API <--> PG
    API <--> Redis

    API -.->|OTLP Traces| Otel
    API -.->|Logs| Loki
    API -.->|Metrics| Prometheus
```
"""

ml_pipeline = """# ML Pipeline Architecture
This details the sequential data flow of the ML Orchestrator.

```mermaid
flowchart LR
    Input[Raw Telemetry\nJSON Batch] --> Preprocess[Feature Engineering & Normalization]
    
    Preprocess --> AD[Isolation Forest]
    AD -->|is_anomaly, score| AC[HDBSCAN + all-MiniLM-L6-v2]
    
    AC -->|cluster_id, confidence| RCA[GraphSAGE Topology Analysis]
    RCA -->|root_cause_node, blast_radius| RP[LightGBM Risk Prediction]
    
    RP -->|risk_probability, SHAP| Output[Unified JSON Result]
```
"""

# ==========================================
# UML DIAGRAMS
# ==========================================

sequence = """# Sequence Diagram: ML Orchestration
```mermaid
sequenceDiagram
    participant User as SRE Dashboard
    participant API as FastAPI Router
    participant Orch as OrchestratorService
    participant IF as Anomaly Service (IF)
    participant HDB as Clustering Service (HDBSCAN)
    participant GS as Root Cause Service (GraphSAGE)
    participant LGB as Risk Service (LightGBM)

    User->>API: POST /api/v1/ml/analyze (Telemetry)
    API->>Orch: analyze_telemetry(payload)
    
    Orch->>IF: predict(payload)
    IF-->>Orch: anomaly_status, score
    
    Orch->>HDB: cluster(payload)
    HDB-->>Orch: cluster_id
    
    Orch->>GS: infer_topology_cause(payload)
    GS-->>Orch: root_cause_node
    
    Orch->>LGB: predict_risk(payload, anomaly_score)
    LGB-->>Orch: risk_probability, SHAP values
    
    Orch->>Orch: generate_recommendations()
    Orch-->>API: Unified MLAnalysisResult
    API-->>User: HTTP 200 JSON
```
"""

# ==========================================
# DATABASE
# ==========================================

er_diagram = """# Database Entity-Relationship Diagram
```mermaid
erDiagram
    ORGANIZATION ||--o{ USER : contains
    ORGANIZATION ||--o{ INCIDENT : owns
    USER ||--o{ INCIDENT : "assigned to"
    SERVICE ||--o{ INCIDENT : triggers
    INCIDENT ||--o{ ALERT : contains
    INCIDENT ||--o{ ALERT_CLUSTER : groups
    SERVICE ||--o{ ALERT : generates
    SERVICE ||--o{ METRIC : tracks
    SERVICE ||--o{ LOG : generates
    SERVICE ||--o{ DEPLOYMENT : deploys
    DEPLOYMENT ||--|| RISK_SCORE : "assessed by"
```
"""

# ==========================================
# API DOCUMENTATION
# ==========================================

api_docs = """# API Documentation (OpenAPI Spec Equivalent)

## `POST /api/v1/ml/analyze`
Executes the full AI Orchestration pipeline.

**Request Body (`application/json`)**:
```json
{
  "cpu_usage": 0.85,
  "sin_hour": 0.5,
  "cos_hour": 0.5,
  "rolling_mean": 0.6,
  "rolling_std": 0.1,
  "lag_1": 0.8,
  "log_text": "CPU overload on frontend service connected to cart database.",
  "deployment_size": 25.0,
  "files_changed": 5.0,
  "code_churn": 120.0
}
```

**Response (`200 OK`)**:
```json
{
  "status": "success",
  "analysis": {
    "anomaly_detection": { "is_anomaly": true, "anomaly_score": 0.92 },
    "alert_clustering": { "cluster_id": 4, "confidence": 0.88 },
    "root_cause_analysis": { "root_cause_node": "cart-db", "confidence": 0.94 },
    "risk_prediction": { "risk_probability": 0.89, "risk_level": "High" },
    "recommended_actions": [
      "Investigate active telemetry anomaly on cart-db.",
      "Deployment blocked: Automatic Rollback Recommended."
    ]
  }
}
```
"""

# ==========================================
# TABLES & METRICS
# ==========================================

model_metrics = """# Final Model Validation Tables

### 1. Risk Prediction Engine (Phase 4.4)
| Model | F1 Score | Recall | Precision | False Negative Rate | Memory (MB) |
|---|---|---|---|---|---|
| LightGBM (Production) | **0.593** | 0.449 | 0.871 | **55.1%** | 12 MB |
| Random Forest | 0.495 | 0.329 | 1.000 | 67.1% | 45 MB |
| Logistic Regression | 0.428 | 0.272 | 1.000 | 72.8% | 2 MB |

### 2. Root Cause Analysis Engine (Phase 4.3)
| Model | Top-1 Accuracy | Train Time (s) | Inference Latency (ms) | Notes |
|---|---|---|---|---|
| GraphSAGE (Production) | **0.94** | 4.2 | **0.002** | Handles dynamic topology |
| XGBoost | 0.96 | 12.0 | 1.5 | Fails on new nodes |
| GAT | 0.60 | >50 | 0.05 | CPU Attention overhead |

### 3. Alert Clustering Engine (Phase 4.2)
| Model | Silhouette Score | Inference Latency (ms) | Noise % |
|---|---|---|---|
| HDBSCAN (Production) | **0.65** | 12.0 | 5% |
| K-Means | 0.52 | 2.5 | N/A |
| DBSCAN | 0.45 | 10.0 | 25% |
"""

create_file("docs/architecture/high_level.md", high_level)
create_file("docs/architecture/ml_pipeline.md", ml_pipeline)
create_file("docs/uml/sequence.md", sequence)
create_file("docs/database/er_diagram.md", er_diagram)
create_file("docs/api/endpoints.md", api_docs)
create_file("docs/tables/model_metrics.md", model_metrics)

print("Documentation generated successfully!")
