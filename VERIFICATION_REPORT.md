# Verification Report

| Metric | Value | Verification Status | Evidence | Reproducible |
|---|---|---|---|---|
| F1 Score (Risk Prediction) | 0.593 | Existing Only | `backend/app/ml_services/risk_prediction/MODEL_SELECTION.md` | Yes |
| Precision (Risk Prediction) | 0.871 | Existing Only | `backend/app/ml_services/risk_prediction/MODEL_SELECTION.md` | Yes |
| F1 Score (Root Cause - GraphSAGE) | 1.000 | Existing Only | `backend/app/ml_services/root_cause/MODEL_SELECTION.md` | Yes |
| Latency `/api/v1/system` | 12ms | Unverified | None | No |
| Latency `/api/v1/cpu` | 8ms | Unverified | None | No |
| API Quality Score | 94/100 | Unverified | None | No |
| Maintainability Score | 92/100 | Unverified | None | No |
| Scalability Score | 85/100 | Unverified | None | No |
