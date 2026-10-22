# Model Card: AIOps Sentinel Alert Clustering Engine

## Model Details
- **Architecture**: `all-MiniLM-L6-v2` (Transformer Encoder) + `HDBSCAN` (Hierarchical Density-Based Spatial Clustering of Applications with Noise)
- **Version**: 1.0.0
- **Type**: Unsupervised Topological Log Clustering
- **Input**: Raw text (AIOps telemetry logs, K8s events, application traces).
- **Output**: Int `cluster_id` (-1 if anomaly/noise)

## Intended Use
- **Primary Use Case**: Aggregating hundreds of disparate raw application and infrastructure logs into macro "Situations" or incidents to reduce operator fatigue.
- **Out of Scope**: Not intended for log parsing (extracting parameters into JSON), nor sequential anomaly detection (which is handled by the upstream OCSVM/LSTM module).

## Training Data
- **Dataset**: LogHub HDFS Subset (2,000 raw production K8s/Hadoop system logs).
- **Preprocessing**: Strict RegEx masking removes IP addresses, Hex codes, UUIDs, datetimes, and specific block identifiers. This prevents the model from trivially grouping logs by timestamp or machine ID, forcing it to cluster based purely on semantic structural state.

## Evaluation Data & Metrics
- **Validation Protocol**: 70/30 train/test split. Out-of-sample scaling verified using HDBSCAN's `approximate_predict()`.
- **Primary Metrics**:
  - Purity: 99.1%
  - Adjusted Rand Index (ARI): 0.704
  - V-Measure: 0.814
  - Silhouette Score (Deduplicated): 0.618

## Ethical Considerations & Limitations
- **False Splitting**: Logs with dramatically different string lengths (e.g., traces) might map to distant points in the manifold, causing HDBSCAN to split a single logical incident into two.
- **Latency**: While inference is fast (<1ms), batch recalculating the MST (Minimum Spanning Tree) for HDBSCAN on >1M embeddings is O(N log N) and computationally heavy.

## Production Config
- `min_cluster_size`: 5
- `metric`: euclidean
- `prediction_data`: True
