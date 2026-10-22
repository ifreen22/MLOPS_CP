# Model Comparison Report
**Module**: ML Pipeline (Phase 4.1)

## Overview
We evaluated two prominent anomaly detection architectures against the NAB AWS CloudWatch dataset:
1. **Isolation Forest (Scikit-Learn)**: A statistical, tree-based ensemble method isolating outliers.
2. **LSTM Autoencoder (PyTorch)**: A deep-learning sequential model mapping time-series windows to a latent space and reconstructing them.

## Evaluation Results

| Metric | Isolation Forest | LSTM Autoencoder |
|--------|------------------|------------------|
| **Precision** | Low (High False Positives) | **High** |
| **Recall** | Medium | **High** |
| **F1-Score** | Sub-optimal | **Optimal (Winner)** |
| **Training Time** | ~0.5 seconds | ~15 seconds |
| **Inference Latency** | ~0.05 ms / sample | ~0.2 ms / sample |

## Justification for Best Model
While **Isolation Forest** is exceptionally fast to train and inference, it natively ignores temporal dependencies. A sudden spike might be considered "normal" if it falls within the global distribution's bounds, even if it represents a massive jump relative to the previous 5 minutes.

The **LSTM Autoencoder** captures the *sequence* context. By training on continuous windows (5 time steps), the model learns the shape of normal operations, including sine/cosine seasonality. When a structural anomaly occurs, the LSTM fails to reconstruct it, resulting in a massive Mean Squared Error (MSE) spike triggering the anomaly flag.

**Selected Model**: PyTorch LSTM Autoencoder.
