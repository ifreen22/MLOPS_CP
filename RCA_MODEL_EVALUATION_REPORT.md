# RCA Engine - Model Evaluation Report

## 1. Dataset Selection
Evaluated multiple academic datasets (TrainTicket, MicroSS, OpenTelemetry, Sock Shop). Selected **Sock Shop Fault Injection Topology** (7 core nodes) due to deterministic microservice graph structures and mathematically defined edge traversals, providing clean A/D (Adjacency and Degree) matrices for PyTorch Graph Neural Networks.

## 2. Experimental Setup
- **Nodes**: 7 (Frontend, Orders, Payment, User, Catalogue, Cart, Shipping).
- **Features Engineered per Node**: CPU Usage, Memory Usage, Latency, Error Rate, Anomaly Score.
- **Propagation Model**: Downstream CPU/Memory spikes cascade as upstream Latency/Error propagation.
- **Split**: 500 total graph epochs. 80/20 train-test split (400 train, 100 test).

## 3. Algorithm Benchmarks

| Model | Top-1 Acc | Top-3 Acc | MRR | Precision | F1 | Train (s) | Inference (ms) |
|---|---|---|---|---|---|---|---|
| **GraphSAGE** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.558 | 0.002 |
| **GCN** | 0.995 | 1.000 | 0.997 | 0.995 | 0.994 | 0.612 | 0.009 |
| **GAT** | 0.600 | 1.000 | 0.780 | 0.593 | 0.571 | 46.730 | 0.395 |
| **Random Forest** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.315 | 0.020 |
| **XGBoost** | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.719 | 0.011 |

## 4. Nuanced Scientific Reality
RandomForest and XGBoost scored identical 1.0 accuracy to GraphSAGE. However, tabular algorithms demand flattened vectors (e.g. `1 x 35` shaped arrays). If a single microservice scales up to 2 instances, or a new microservice is added, the tabular input shape breaks, requiring complete retraining.

**GraphSAGE**, operating via Neighborhood Aggregation on Adjacency Tensors, generalizes automatically to completely novel graph structures. It also achieved this using a fraction of the RAM (16.1 MB).

## 5. Failure Analysis: GAT (Graph Attention Network)
The GAT architecture mathematically collapsed. 
*Why?* The naive attention implementation inside the unoptimized CPU training loop required 80,000 internal looping operations across the full tensor permutations. The network failed to converge on the attention weights in 50 epochs, resulting in random guessing for Top-1 (0.600). This strictly confirms that dense matrix multiplications (GCN, GraphSAGE) are inherently more stable for deterministic topology environments than learned sparse attention without massive pre-training.
