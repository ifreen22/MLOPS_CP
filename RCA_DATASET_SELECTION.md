# Root Cause Analysis (RCA) Dataset Selection

## 1. Candidate Datasets Evaluated

| Dataset | Topology Size | Telemetry Types | Ground Truth Labels | Scalability | Suitability for GNNs |
|---|---|---|---|---|---|
| **Sock Shop (Fault Injection)** | 14 Microservices | Metrics, Traces | Yes (Fault types & locations) | Medium | Excellent (Well-defined edges) |
| **TrainTicket** | 40+ Microservices | Metrics, Traces, Logs | Yes (Complex failures) | High | Good (Highly noisy) |
| **Alibaba Cluster Trace** | 10k+ Nodes | VM/Container Metrics | Partial (Evictions/OOMs) | Massive | Poor (Lacks app-level dependency edges) |
| **MicroSS** | 10 Microservices | Traces | Yes | Low | Medium |
| **OpenTelemetry Demo** | 12 Microservices | Traces, Metrics | No (Requires synthetic fault injection) | Medium | Low (Requires manual labeling) |

## 2. Selection
**Winner:** `Sock Shop Fault Injection Dataset` (Derived synthetic variant for Capstone).

### Scientific Justification
1. **Topology Definition:** Sock Shop provides a rigid, deterministic microservice dependency graph (Frontend -> Orders -> Payment, etc.). Graph Neural Networks (GCN, GAT, GraphSAGE) rely entirely on the Adjacency Matrix ($A$). Without a clean topology, message passing algorithms devolve into random noise.
2. **Feature Alignment:** It natively emits CPU, Memory, Latency, and Error rates (RED metrics) matching the exact schema engineered in Phase 2 of our AIOps platform.
3. **Reproducibility:** AIOps baseline models (like random walks or PageRank) are historically benchmarked against Sock Shop architectures. Selecting this allows our GNN architectures to be compared against known academic baselines fairly.

## 3. Capstone Implementation Strategy
Because downloading external 50GB trace datasets dynamically during evaluation is unstable, we will construct a **Synthetic Sock Shop Graph** mathematically mapping to the exact fault patterns (CPU spikes causing upstream latency propagation) observed in the real dataset. This guarantees 100% reproducibility and prevents data-leakage while testing the mathematical limits of the Message Passing frameworks.
