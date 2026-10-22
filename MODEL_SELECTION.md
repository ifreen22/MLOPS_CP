# ML Model Selection & Strategy
**Project**: AIOps Sentinel – Self-Healing Cloud Platform  
**Phase**: Phase 3 (ML Engineering Design)  

This document defines the business problem, ML problem type, algorithmic recommendations, and evaluation metrics for each intelligence module.

---

## 1. Anomaly Detection
- **Business Problem**: Operators suffer from alert fatigue setting static thresholds for metrics (CPU, Memory). We need dynamic baselining to only trigger alerts on statistically significant, abnormal behavior.
- **ML Problem Type**: Unsupervised Time-Series Anomaly Detection.
- **Algorithm Recommendation**: **Isolation Forest** or **Autoencoders (LSTM-AE)**.
  - *Justification*: Isolation Forest is highly computationally efficient for univariate time series. For multivariate correlation (e.g., CPU spiking while Network IO drops), LSTM-Autoencoders capture non-linear temporal dependencies and reconstruct normal states, flagging high-reconstruction-error vectors as anomalies.
- **Evaluation Metrics**: F1-Score (Anomaly class), Area Under the Precision-Recall Curve (PR-AUC). False Positive Rate (FPR) must be minimized.

## 2. Alert Clustering
- **Business Problem**: A single database failure can trigger 500 alerts across dependent microservices. These need to be grouped into a single "Situation".
- **ML Problem Type**: Unsupervised Text & Temporal Clustering.
- **Algorithm Recommendation**: **HDBSCAN** combined with **SBERT (Sentence-BERT)** embeddings.
  - *Justification*: SBERT generates dense vector representations of log/alert messages. HDBSCAN clusters these vectors without requiring a predefined number of clusters ($k$), handling varying density and filtering out noise (unrelated alerts) perfectly.
- **Evaluation Metrics**: Silhouette Score, V-Measure, Compression Ratio (Total Alerts / Resulting Situations).

## 3. Root Cause Analysis (RCA)
- **Business Problem**: Once an incident is identified, SREs spend 80% of their time finding the origin node in a complex microservice mesh.
- **ML Problem Type**: Graph Machine Learning / Causal Inference.
- **Algorithm Recommendation**: **Graph Convolutional Networks (GCN)** or **PC Algorithm (Causal Discovery)**.
  - *Justification*: AIOps topology is naturally a graph. GCNs can pass messages (anomaly scores) along the edges of the service mesh to classify the "faulty" node. Alternatively, Causal Discovery algorithms can build Directed Acyclic Graphs (DAGs) to trace the exact chain of failure.
- **Evaluation Metrics**: Top-K Accuracy (Is the true root cause in the top 3 recommendations?), Mean Reciprocal Rank (MRR).

## 4. Risk Prediction
- **Business Problem**: 70% of outages are caused by bad deployments. We need to block risky code deployments before they hit production.
- **ML Problem Type**: Supervised Binary Classification.
- **Algorithm Recommendation**: **XGBoost** or **LightGBM**.
  - *Justification*: Deployment risk involves tabular data (commit size, time of day, historical failure rate). Gradient Boosting Trees consistently outperform Deep Learning on structured tabular data, require less tuning, and offer high interpretability (SHAP values) to explain *why* a deployment is blocked.
- **Evaluation Metrics**: ROC-AUC, Precision, Recall. (High recall is preferred to catch all risky deployments, even at the cost of some false positives).

## 5. Recommendation Engine (Remediation)
- **Business Problem**: When a specific issue occurs, junior engineers don't know which runbook or playbook to execute.
- **ML Problem Type**: Contextual Bandits or Item-Based Collaborative Filtering.
- **Algorithm Recommendation**: **Two-Tower Neural Network** (Query-Item Matching).
  - *Justification*: Encodes the "Incident Context" in one tower and the "Playbook Steps" in another, calculating cosine similarity. Easily updated as new playbooks are added.
- **Evaluation Metrics**: Click-Through Rate (CTR) - do users click the recommended playbook?, Execution Success Rate.

## 6. RAG Search (Playbooks & Logs)
- **Business Problem**: Engineers need to query past incidents and documentation via natural language (e.g., "How did we fix the Redis OOM last week?").
- **ML Problem Type**: Information Retrieval / Generative AI.
- **Algorithm Recommendation**: **Vector Database (Qdrant/Milvus) + Embedding Model (e.g., BAAI/bge-large) + LLM (Llama 3 / Mistral)**.
  - *Justification*: Retrieval-Augmented Generation (RAG) prevents LLM hallucinations by forcing the model to cite specific historical incident logs or playbooks retrieved via dense vector similarity.
- **Evaluation Metrics**: Mean Average Precision (MAP) for retrieval, ROUGE-L / BLEU for generation quality, Faithfulness score.
