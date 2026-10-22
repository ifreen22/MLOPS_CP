import os

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

component_arch = """# Component Architecture
```mermaid
flowchart TD
    subgraph UI
        Dashboard[React Dashboard]
        SituationRoom[Situation Room]
        RiskPanel[Risk Prediction Panel]
    end

    subgraph API Gateway
        FastAPI[FastAPI Router]
    end

    subgraph Controllers
        OrchestratorCtrl[Orchestrator Controller]
        AlertCtrl[Alert Controller]
        MetricCtrl[Metric Controller]
    end

    subgraph Services
        OrchSvc[AI Orchestrator Service]
        RcaSvc[RCA Service]
        RiskSvc[Risk Service]
    end

    subgraph Models
        GS[GraphSAGE Model]
        LGB[LightGBM Model]
        HDB[HDBSCAN Model]
    end

    UI --> FastAPI
    FastAPI --> OrchestratorCtrl
    OrchestratorCtrl --> OrchSvc
    OrchSvc --> RcaSvc
    RcaSvc --> GS
    OrchSvc --> RiskSvc
    RiskSvc --> LGB
```
"""

backend_arch = """# Backend Architecture
```mermaid
flowchart LR
    Request --> AuthMiddleware
    AuthMiddleware --> Router
    Router --> PydanticValidation
    PydanticValidation --> Controller
    Controller --> ServiceLayer
    ServiceLayer --> PrismaClient
    PrismaClient --> PostgresDB
    ServiceLayer --> MLModels
    ServiceLayer --> RedisCache
```
"""

deployment_arch = """# Deployment Architecture
```mermaid
flowchart TD
    Internet((Internet))
    
    subgraph Docker Host
        Nginx[Nginx Reverse Proxy]
        
        subgraph Services
            React[Vite Frontend :80]
            API[FastAPI :8000]
        end
        
        subgraph Data
            PG[(PostgreSQL :5432)]
            Redis[(Redis :6379)]
        end
        
        subgraph Observability
            Prom[Prometheus]
            Graf[Grafana]
            Otel[Otel Collector]
        end
    end
    
    Internet -->|HTTPS/443| Nginx
    Nginx --> React
    Nginx --> API
    API <--> PG
    API <--> Redis
    API -.-> Otel
    Otel -.-> Prom
    Prom -.-> Graf
```
"""

class_uml = """# Class Diagram
```mermaid
classDiagram
    class OrchestratorService {
        +analyze_telemetry(payload: Dict)
        +get_health()
    }
    class RiskPredictionService {
        +predict(features: Dict)
    }
    class RootCauseAnalysisService {
        +predict_root_cause(batch: List)
    }
    class TelemetryPayload {
        +float cpu_usage
        +float deployment_size
        +float anomaly_score
    }
    OrchestratorService --> RiskPredictionService
    OrchestratorService --> RootCauseAnalysisService
    OrchestratorService ..> TelemetryPayload : Validates
```
"""

create_file("docs/architecture/component.md", component_arch)
create_file("docs/architecture/backend.md", backend_arch)
create_file("docs/deployment/architecture.md", deployment_arch)
create_file("docs/uml/class.md", class_uml)

print("Batch 2 documentation generated successfully!")
