import re
import os

report_path = "FINAL_ENGINEERING_REPORT.md"

with open(report_path, "r", encoding="utf-8") as f:
    content = f.read()

# Remove the specific unverified API execution times
content = re.sub(r'\| `/api/v1/system` \| GET \| 200 \| 12ms \|', r'| `/api/v1/system` | GET | 200 | UNVERIFIED |', content)
content = re.sub(r'\| `/api/v1/cpu` \| GET \| 200 \| 8ms \|', r'| `/api/v1/cpu` | GET | 200 | UNVERIFIED |', content)

# Remove API Quality Score if it was hallucinated
content = re.sub(r'\*\*API Quality Score:\*\* 94/100', r'**API Quality Score:** UNVERIFIED', content)

# The F1 score of 0.593 and Precision of 0.871 are from LightGBM risk_model_evaluation
# Accuracy of 94.2%? Need to check if that's in the report.

with open(report_path, "w", encoding="utf-8") as f:
    f.write(content)

table_content = """# Verification Report

| Metric | Value | Verification Status | Evidence | Reproducible |
|---|---|---|---|---|
| F1 Score (Risk Prediction) | 0.593 | Existing Only | `backend/app/ml_services/risk_prediction/MODEL_SELECTION.md` | Yes |
| Precision (Risk Prediction) | 0.871 | Existing Only | `backend/app/ml_services/risk_prediction/MODEL_SELECTION.md` | Yes |
| F1 Score (Root Cause) | 0.593 | Existing Only | `backend/app/ml_services/root_cause/MODEL_SELECTION.md` | Yes |
| Latency `/api/v1/system` | 12ms | Unverified | None | No |
| Latency `/api/v1/cpu` | 8ms | Unverified | None | No |
| API Quality Score | 94/100 | Unverified | None | No |
| Maintainability Score | 92/100 | Unverified | None | No |
| Scalability Score | 85/100 | Unverified | None | No |
"""

with open("VERIFICATION_REPORT.md", "w", encoding="utf-8") as f:
    f.write(table_content)

print("Report updated and table created.")
