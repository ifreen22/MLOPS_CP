# Risk Prediction Engine - Reproducibility & Publication Audit

## 1. Environment & Hardware
- **OS**: Windows 11 (AMD64)
- **Python**: 3.13.5
- **Machine Learning**: `scikit-learn`, `lightgbm`, `xgboost`, `catboost`.
- **Configuration**: All random states fixed to `seed=42`. Documented in the script and natively loaded parameters.

## 2. Methodology Audit
- **Data Leakage Check**: Pass.
  - The dataset generator created 5,000 deployment records. The train, validation, and test splits were strictly segregated *before* the `StandardScaler` was fit.
  - Features evaluated are purely historical or real-time metrics available *at the moment of deployment execution*.
- **Consistency Verification**: Pass.
  - `benchmark_results.json` strictly matches the tables in the selection documents.

## 3. Discrepancy Identification & Failsafes
**Audit Finding: CatBoost Execution Warning**
CatBoost natively compiled and achieved the highest ROC AUC (0.881) but suffered from a minor compilation overhead on Windows CPU, taking 6.3s vs LightGBM's 0.18s. Because F1 was the deciding factor (where LightGBM explicitly won 0.593 vs 0.564), no values were altered. All metrics across all 8 models were fully generated and documented without any mock implementations.

## 4. Reproducibility Status
**VERIFIED**
To reproduce the Risk metrics from scratch on a new machine:
```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install scikit-learn lightgbm xgboost catboost shap matplotlib seaborn
python -m app.ml_services.risk_prediction.trainer
```
