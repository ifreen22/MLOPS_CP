# Model Card: AIOps Sentinel RCA GraphSAGE

## Model Details
- **Architecture**: GraphSAGE (Graph Sample and Aggregate) with Mean Aggregator.
- **Version**: 1.0.0
- **Type**: Supervised Graph Neural Network (Node Classification)
- **Input**: 
  - Adjacency Matrix (Topological dependencies)
  - Node Features `[cpu, memory, latency, errors, anomaly_score]`
- **Output**: Softmax probability array defining likelihood of Root Cause per node.

## Intended Use
- **Primary Use Case**: Isolating the single failing microservice in an cascading infrastructure failure where multiple downstream and upstream dependencies are emitting synchronized alerts.
- **Out of Scope**: Not intended for log-level anomaly detection, nor predicting infrastructure failures before they happen (forecasting).

## Training Data
- **Dataset**: Synthetic Sock Shop Fault Topologies. 500 samples containing simulated CPU/Memory faults that propagate Latency/Error cascades upstream via Directed Acyclic Graph (DAG) BFS traversal.

## Evaluation Data & Metrics
- **Validation Protocol**: 80/20 train/test inductive split.
- **Primary Metrics**:
  - Top-1 Accuracy: 1.00
  - Top-3 Accuracy: 1.00
  - MRR (Mean Reciprocal Rank): 1.00
  - Inference Latency: 0.002 ms

## Ethical Considerations & Limitations
- **Topological Shifts**: The model was trained on a rigid DAG. If cyclic dependencies are introduced into the Kubernetes cluster (e.g. Service A calls Service B calls Service A), the message passing layer may suffer from over-smoothing, reducing classification confidence.
- **Scale Limits**: Inference memory requires dense Adjacency representations. For clusters exceeding 100,000 pods, the `A_tensor` will require migrating to sparse CSR tensors to prevent VRAM OOM faults.
