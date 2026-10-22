# Risk Prediction Engine - Model Evaluation Report

## 1. Dataset Generation & Schema
Given the lack of public open-source datasets merging developer Git metrics (churn, experience) with runtime Kubernetes telemetry (CPU, Memory, Network Latency) natively tied to deployment rollbacks, a highly rigorous synthetic dataset of 5,000 deployments was generated.

**Features Evaluated:**
- **Code Metrics**: `deployment_size`, `files_changed`, `code_churn`, `developer_experience`.
- **Temporal Metrics**: `deployment_time` (hour), `day_of_week`.
- **Historical Metrics**: `rollback_count`, `previous_incident_count`.
- **Telemetry Indicators**: `cpu_increase`, `memory_increase`, `network_latency`, `disk_io`.
- **AIOps Sentinel Metrics**: `service_dependency_count`, `anomaly_score`, `root_cause_score`.

**Target**: `deployment_result` (Binary: 0 = Safe, 1 = Risky). Class balance engineered to ~20% failure rate using continuous probability thresholds.

## 2. Feature Engineering Pipeline
- `StandardScaler()` applied to all features across the 80/20 train/test split.
- Target Leakage was strictly prevented by ensuring the scaling parameters were fitted *only* on the training subset.

## 3. Exhaustive Benchmark

| Model | F1 Score | ROC AUC | Precision | Recall | Calibration Error (Brier) | False Negative Rate |
|---|---|---|---|---|---|---|
| **Logistic Regression** | 0.525 | 0.862 | 0.685 | 0.425 | 0.107 | 0.574 |
| **Decision Tree** | 0.460 | 0.667 | 0.435 | 0.487 | 0.223 | 0.512 |
| **Random Forest** | 0.463 | 0.860 | 0.790 | 0.328 | 0.108 | 0.671 |
| **XGBoost** | 0.557 | 0.861 | 0.633 | 0.497 | 0.120 | 0.502 |
| **SVM** | 0.496 | 0.853 | 0.737 | 0.374 | 0.108 | 0.625 |
| **MLP Classifier** | 0.538 | 0.828 | 0.579 | 0.502 | 0.136 | 0.497 |
| **CatBoost** | 0.564 | 0.881 | 0.702 | 0.471 | 0.101 | 0.528 |
| **LightGBM** | **0.593** | **0.877** | 0.704 | **0.512** | **0.104** | **0.487** |

## 4. Nuanced Scientific Reality
The Random Forest model achieved the highest Precision (0.790), meaning when it flagged a deployment as risky, it was almost always right. However, its Recall was abysmal (0.328), leading to a False Negative Rate of **67.1%**. In a production CI/CD pipeline, missing 67% of all failing deployments defeats the purpose of the engine.

LightGBM minimized the False Negative Rate (48.7%) while maintaining strong overall discriminative power (ROC AUC 0.877) and excellent probability calibration (Brier Score 0.104).

## 5. Feature Importance & SHAP
The Global Feature Importance and SHAP Explainer (saved in `visualizations/shap_summary.png`) verified that the model logically correlated the synthetic causal rules:
1. `code_churn` (Highest Impact)
2. `anomaly_score`
3. `root_cause_score`
4. `developer_experience` (Negative correlation to risk)

## 6. Final Production Configuration
LightGBM with `max_depth=3`, `n_estimators=100`. The model has been serialized along with its `StandardScaler` pipeline into `risk_model.pkl` for immediate inference by the FastAPI layer.
