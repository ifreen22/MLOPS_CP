# Model Card: AIOps Sentinel Deployment Risk Predictor

## Model Details
- **Architecture**: LightGBM (Gradient Boosting Decision Tree)
- **Version**: 1.0.0
- **Type**: Supervised Binary Classification
- **Input**: 15 float features (Code churn, developer experience, telemetry offsets, topological density, upstream anomaly signals).
- **Output**: Binary Int (0 = Safe, 1 = Risky) + Softmax Probability Score.

## Intended Use
- **Primary Use Case**: Acting as a CI/CD pipeline gatekeeper. If a developer attempts to push code, the model predicts the likelihood of it triggering a production outage based on historical data and current cluster state.
- **Out of Scope**: Not intended to automatically alter code or directly block critical emergency hotfixes (P0). It serves as an advisory system with a "Risk Factor" confidence score.

## Training Data
- **Dataset**: 5,000 synthetically modeled deployments mirroring realistic Git/K8s telemetry intersections. Engineered with a baseline 20% failure probability to mimic real enterprise rollout statistics.

## Evaluation Data & Metrics
- **Validation Protocol**: 60/20/20 Train/Validation/Test splits. Grid Search executed entirely on the training block to prevent hyperparameter leakage into the test score.
- **Primary Metrics**:
  - ROC AUC: 0.881
  - F1 Score: 0.593
  - Brier Calibration Error: 0.104
  - False Negative Rate: 0.49

## Ethical Considerations & Limitations
- **Developer Bias**: The model utilizes `developer_experience` (years or tenure) as a feature. This could inadvertently flag junior developers' PRs as "High Risk" perpetually, leading to pipeline gatekeeping bias. In a true enterprise setting, this feature should be scrubbed or replaced with an objective `repository_familiarity_score` (commits to the specific microservice repo) to prevent HR/bias issues.
- **Class Imbalance**: Failing deployments are rare. The model relies heavily on the `code_churn` and `anomaly_score` interactions to find the needle in the haystack.
