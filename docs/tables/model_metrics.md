# Final Model Validation Tables

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
