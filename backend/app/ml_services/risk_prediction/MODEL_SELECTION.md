# Risk Prediction Engine - Model Selection

## 1. Benchmarking Matrix (Validation Set)

| Model | Accuracy | Precision | Recall | F1 Score | ROC AUC | PR AUC | MCC | Train Time (s) |
|---|---|---|---|---|---|---|---|---|
| **Logistic Regression** | 0.850 | 0.685 | 0.425 | 0.525 | 0.862 | 0.649 | 0.459 | 0.125 |
| **Decision Tree** | 0.777 | 0.435 | 0.487 | 0.460 | 0.667 | 0.312 | 0.320 | 0.073 |
| **Random Forest** | 0.852 | 0.790 | 0.328 | 0.463 | 0.860 | 0.639 | 0.445 | 1.371 |
| **XGBoost** | 0.846 | 0.633 | 0.497 | 0.557 | 0.861 | 0.626 | 0.470 | 0.606 |
| **SVM** | 0.852 | 0.737 | 0.374 | 0.496 | 0.853 | 0.635 | 0.453 | 2.294 |
| **MLP Classifier** | 0.832 | 0.579 | 0.502 | 0.538 | 0.828 | 0.578 | 0.438 | 28.475 |
| **CatBoost** | 0.858 | 0.702 | 0.471 | 0.564 | 0.881 | 0.671 | 0.497 | 6.313 |
| **LightGBM** | 0.863 | 0.704 | 0.512 | **0.593** | 0.877 | 0.661 | 0.522 | 0.185 |

## 2. Selection Rationale
**Winner:** LightGBM

**Why it won:**
1. **Asymmetric Risk Importance**: In deployment risk prediction, predicting a safe deployment as risky (False Positive) just delays a rollout, but predicting a risky deployment as safe (False Negative) causes a production outage. Therefore, we prioritize F1 and Recall over standard Accuracy.
2. **Superior Generalization**: LightGBM achieved the highest F1 Score (0.593) outperforming XGBoost and Random Forest, which struggled significantly with Recall (0.497 and 0.328 respectively).
3. **Training Efficiency**: LightGBM compiled the gradient boosting trees in 0.185s, which is ~34x faster than CatBoost (6.3s) and ~7x faster than Random Forest (1.37s) while maintaining a virtually identical ROC AUC to CatBoost (0.877 vs 0.881).

## 3. Hyperparameter Tuning
A Grid Search was executed on LightGBM.
- `max_depth`: 3
- `n_estimators`: 100

## 4. Final Holdout Test Performance (LightGBM)
- **F1 Score**: 0.578
- **ROC AUC**: 0.877
- **MCC**: 0.499
