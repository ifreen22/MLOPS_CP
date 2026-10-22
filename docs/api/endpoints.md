# API Documentation (OpenAPI Spec Equivalent)

## `POST /api/v1/ml/analyze`
Executes the full AI Orchestration pipeline.

**Request Body (`application/json`)**:
```json
{
  "cpu_usage": 0.85,
  "sin_hour": 0.5,
  "cos_hour": 0.5,
  "rolling_mean": 0.6,
  "rolling_std": 0.1,
  "lag_1": 0.8,
  "log_text": "CPU overload on frontend service connected to cart database.",
  "deployment_size": 25.0,
  "files_changed": 5.0,
  "code_churn": 120.0
}
```

**Response (`200 OK`)**:
```json
{
  "status": "success",
  "analysis": {
    "anomaly_detection": { "is_anomaly": true, "anomaly_score": 0.92 },
    "alert_clustering": { "cluster_id": 4, "confidence": 0.88 },
    "root_cause_analysis": { "root_cause_node": "cart-db", "confidence": 0.94 },
    "risk_prediction": { "risk_probability": 0.89, "risk_level": "High" },
    "recommended_actions": [
      "Investigate active telemetry anomaly on cart-db.",
      "Deployment blocked: Automatic Rollback Recommended."
    ]
  }
}
```
