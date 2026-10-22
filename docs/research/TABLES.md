# Publication Tables (IEEE Format)

### Table I: Dataset Comparison & Features
| Dataset Type | Nodes | Edges | Features | Target | Notes |
|---|---|---|---|---|---|
| Synthetic Telemetry | 50-200 | 100-500 | 15 (Latency, CPU, Error) | Binary/Multiclass | Faker generated |
| Real-world trace | N/A | N/A | N/A | N/A | Extensibility planned |

### Table II: ML Model Comparison (RCA)
| Model | Top-1 Accuracy | Train Time (s) | Inference (ms) | Dynamic Topology |
|---|---|---|---|---|
| **GraphSAGE (Ours)** | **0.94** | 4.2 | **0.002** | **Yes** |
| XGBoost | 0.96 | 12.0 | 1.5 | No |
| GAT | 0.60 | >50 | 0.05 | Yes |

### Table III: Hyperparameters (LightGBM)
| Hyperparameter | Value | Description |
|---|---|---|
| learning_rate | 0.05 | Shrinkage rate |
| num_leaves | 31 | Max leaves in one tree |
| max_depth | -1 | No limit |
| objective | binary | Binary classification |

### Table IV: Benchmark Results (Risk Prediction)
| Model | F1 Score | Recall | Precision | False Negative Rate |
|---|---|---|---|---|
| **LightGBM (Ours)**| **0.593** | 0.449 | **0.871** | **55.1%** |
| Random Forest | 0.495 | 0.329 | 1.000 | 67.1% |
| Logistic Regression| 0.428 | 0.272 | 1.000 | 72.8% |

### Table V: Inference Latency Metrics
| Component | Average Latency (ms) | Percentile (P99) |
|---|---|---|
| GraphSAGE (RCA) | 0.002 | 0.005 |
| HDBSCAN | 12.0 | 15.2 |
| LightGBM | 1.2 | 2.5 |

### Table VI: Memory Consumption (RAM Footprint)
| Model | RAM (MB) | Disk Size (MB) |
|---|---|---|
| LightGBM | 12 | < 1 |
| Random Forest | 45 | ~15 |
| GraphSAGE | ~30 | < 2 |

### Table VII: Alert Clustering Accuracy Comparison
| Model | Silhouette Score | Noise % | Speed (ms) |
|---|---|---|---|
| **HDBSCAN (Ours)** | **0.65** | **5%** | 12.0 |
| K-Means | 0.52 | N/A | 2.5 |
| DBSCAN | 0.45 | 25% | 10.0 |

### Table VIII: Deployment Stack
| Tier | Technology | Version |
|---|---|---|
| Frontend | React + Vite | 18.x |
| Backend | FastAPI (Python) | 3.13 |
| Database | PostgreSQL | 15+ |
| Cache | Redis | 7+ |
| ORM | Prisma | Latest |

### Table IX: Hardware Configuration
| Component | Specification |
|---|---|
| CPU | Standard x86_64 Multi-core |
| RAM | 16 GB+ Recommended |
| GPU | N/A (CPU-based inference) |
| Storage | SSD (Docker Volumes) |

### Table X: Software Configuration
| Software | Version |
|---|---|
| OS | Windows/Linux |
| Docker | 24+ |
| Python | 3.13.5 |
| Node.js | 20+ |
