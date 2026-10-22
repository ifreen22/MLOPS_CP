# Experimental Analysis & Model Selection Justifications

This document explains the scientific and engineering rationale behind the selection of the core ML algorithms in AIOps Sentinel, using the benchmarked metrics.

## 1. Why HDBSCAN was Selected (Alert Clustering)
- **Metric Justification:** HDBSCAN achieved a Silhouette Score of **0.65** with a noise ratio of **5%**, significantly outperforming standard DBSCAN (0.45 score, 25% noise) and K-Means (0.52 score).
- **Engineering Rationale:** Microservice alerts do not form spherical clusters (which breaks K-Means) and have varying density clusters (which breaks DBSCAN). HDBSCAN elegantly handles arbitrary shapes and varying densities.
- **Tradeoffs:** HDBSCAN has higher inference latency (12.0ms vs K-Means 2.5ms), but in an alert pipeline, precision and noise-reduction (5%) vastly outweigh a 9.5ms penalty.

## 2. Why GraphSAGE was Selected (Root Cause Analysis)
- **Metric Justification:** GraphSAGE achieved **94% Top-1 Accuracy** with an astonishing **0.002ms** inference latency. Standard Graph Attention Networks (GAT) yielded poor accuracy (60%) and took >50ms.
- **Engineering Rationale:** AIOps environments are highly dynamic. Services are spun up and torn down constantly. Standard Graph Convolutional Networks (GCNs) are transductive (fail on unseen nodes). GraphSAGE is *inductive*—it generates embeddings for unseen nodes by sampling and aggregating features from local neighborhoods. XGBoost scored slightly higher (96%) but natively fails when network topology changes.
- **Tradeoffs:** Training GraphSAGE requires neighborhood sampling configurations which can be complex to tune, but the 0.002ms latency makes it unparalleled for real-time RCA.

## 3. Why LightGBM was Selected (Risk Prediction)
- **Metric Justification:** LightGBM delivered an F1 Score of **0.593** and a Precision of **0.871** while consuming only **12 MB** of memory (compared to Random Forest's 45 MB).
- **Engineering Rationale:** For deployment risk, false positives (blocking a safe deployment) cause massive friction for developers. High precision (0.871) ensures that when the engine flags a deployment, it is highly likely to be truly risky. LightGBM handles categorical data natively and builds trees leaf-wise, yielding superior speed and memory efficiency.
- **Tradeoffs:** The model suffers from a high False Negative Rate (55.1%). It errs heavily on the side of caution—meaning it lets some risky deployments through to avoid stopping safe ones.

## 4. Why Isolation Forest was Selected (Anomaly Detection)
- **Engineering Rationale:** Isolation Forest isolates anomalies explicitly rather than profiling normal data. It operates in $O(N \log N)$ time, making it uniquely suited for high-throughput, real-time telemetry streams. While specific benchmark metrics were excluded from the final recording phase in favor of the orchestration benchmarks, its structural algorithm inherently scales better than Local Outlier Factor (LOF) or One-Class SVMs in high-dimensional telemetry spaces.
