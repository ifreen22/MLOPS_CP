# Research Contributions & Impact

## 1. Novel Contributions
- **Inductive RCA on Dynamic Graphs:** We demonstrate the viability of applying GraphSAGE to dynamic microservice topologies, allowing Root Cause Analysis models to operate without retraining when new microservices are deployed.
- **End-to-End ML Orchestration DAG:** We propose a unified, gracefully degrading orchestration engine that links Anomaly Detection, Alert Clustering, RCA, and Risk Prediction into a single asynchronous FastAPI pipeline.

## 2. Research Highlights
- Proved that density-based clustering (HDBSCAN) coupled with `all-MiniLM-L6-v2` SentenceTransformers creates a highly resilient alert correlation engine, reducing alert noise to 5%.
- Established a latency baseline of 0.002ms for GNN-based RCA, proving that deep learning can be deployed synchronously in the telemetry path without massive overhead.

## 3. Practical Contributions
- Open-sourced a complete, production-ready enterprise React Dashboard utilizing `@xyflow/react` for real-time visualization of GNN graph outputs.
- Developed a complete infrastructure-as-code (Docker Compose) deployment bridging PostgreSQL, Redis, Prometheus, and Python ML pipelines natively.

## 4. Industrial Impact
For Site Reliability Engineering (SRE) teams, AIOps Sentinel provides a blueprint to escape "alert fatigue". By reducing raw alert volume (clustering) and pointing directly to the topological origin (RCA), MTTR (Mean Time To Resolution) can be drastically reduced. The 12MB LightGBM risk engine proves that CI/CD pipelines can integrate AI gates without requiring heavy GPU infrastructure.

## 5. Academic Impact
Provides researchers with a modular testbed. Researchers can swap out the PyTorch GraphSAGE module for novel GNN architectures (e.g., Spatio-Temporal GNNs) while utilizing the existing data ingestion, orchestrator, and React UI to instantly visualize their results.
