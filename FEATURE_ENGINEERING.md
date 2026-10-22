# Feature Engineering & Preprocessing
**Project**: AIOps Sentinel – Self-Healing Cloud Platform  
**Phase**: Phase 3 (ML Engineering Design)  

This document defines the input variables, target variables (labels), and the preprocessing pipelines required to transform raw telemetry into model-ready tensors.

---

## 1. Anomaly Detection (Metrics)
**Input Features (from `Metric` table)**:
- `value`: Raw metric float value.
- `timestamp`: UTC time of the metric.
- `serviceId`: Target microservice.
- `name`: Metric name (e.g., `cpu_usage_percent`, `memory_bytes`).

**Preprocessing Pipeline**:
1. **Imputation**: Forward-fill missing timestamps to maintain a strictly continuous time series.
2. **Time-based Feature Extraction**: Extract `hour_of_day`, `day_of_week` (to capture cyclical seasonality).
3. **Rolling Aggregations**: Compute `rolling_mean_5m`, `rolling_std_5m`.
4. **Scaling**: Z-Score Normalization (StandardScaler) per `serviceId` and `name` to ensure the model trains on standard deviations from the mean rather than absolute values.

**Target**: None (Unsupervised).

---

## 2. Alert Clustering
**Input Features (from `Alert` and `K8sEvent` tables)**:
- `title` & `description`: Textual payload of the alert.
- `firedAt`: Timestamp of the alert.
- `serviceId`: The affected service.
- `severity`: Alert severity level.

**Preprocessing Pipeline**:
1. **Text Cleansing**: Remove IP addresses, hex hashes, and UUIDs using Regex to prevent the model from treating unique IDs as separate words.
2. **Tokenization**: Sub-word tokenization using a pre-trained BERT tokenizer.
3. **Temporal Distance**: Calculate $\Delta t$ (time difference) between consecutive alerts.
4. **Embedding**: Pass cleansed text through a pre-trained sentence transformer to generate 384-dimensional dense vectors.

**Target**: None (Unsupervised clustering).

---

## 3. Root Cause Analysis
**Input Features (from `Topology`, `Metric`, and `Alert` tables)**:
- **Graph Structure**: Adjacency matrix of `Service` dependencies.
- **Node Features**: Concatenation of the anomaly score (from Module 1) and alert severity count per service node.

**Preprocessing Pipeline**:
1. **Graph Construction**: Convert database relational topology (Edges: upstream/downstream relationships) into a PyTorch Geometric `Data` object.
2. **Feature Normalization**: MinMax scale the node features [0, 1].

**Target**: `rootCauseServiceId` (Supervised, derived from historical `Incident` resolutions).

---

## 4. Risk Prediction (Deployments)
**Input Features (from `Deployment`, `Service`, `User` tables)**:
- `commit_size`: Lines of code changed (simulated external metadata).
- `author_experience`: Number of previous successful deployments by the user.
- `time_of_day`: Deployment hour.
- `service_criticality`: Tier 1, 2, or 3.
- `recent_incidents_count`: Number of incidents in the service over the last 7 days.

**Preprocessing Pipeline**:
1. **Categorical Encoding**: One-Hot Encode `service_criticality`.
2. **Cyclical Encoding**: Apply sine/cosine transformations to `time_of_day` (e.g., $sin(2\pi \cdot \frac{hour}{24})$) to preserve the continuous loop of time.
3. **Scaling**: RobustScaler on continuous variables (`commit_size`) to handle outliers.

**Target (from `DeploymentStatus`)**: `1` (ROLLED_BACK / FAILED), `0` (SUCCESS).

---

## 5. Recommendation Engine
**Input Features**:
- **Query (Incident Context)**: `Incident.title`, `Incident.severity`, `root_cause_service`.
- **Item (Playbook Context)**: `Playbook.name`, `Playbook.description`, `Playbook.tags`.

**Preprocessing Pipeline**:
1. **TF-IDF or Embeddings**: Vectorize both the incident text and the playbook text.
2. **Implicit Feedback Matrix**: Construct a user-item interaction matrix where `1` indicates a playbook was executed during a specific incident type, and `0` indicates it was ignored.

**Target**: `was_successful` (Binary indicator of whether the playbook resolved the incident, pulled from `PlaybookExecution` status).
