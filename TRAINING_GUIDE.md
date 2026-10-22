# Training Guide
**Module**: ML Pipeline (Phase 4.1)

## 1. Environment Setup
To reproduce the anomaly detection model training, ensure you have the dependencies installed:
```bash
pip install torch torchvision scikit-learn pandas numpy
```

## 2. Dataset Sourcing
The pipeline automatically downloads the **Numenta Anomaly Benchmark (NAB)** AWS CloudWatch EC2 dataset using `urllib`. It simulates enterprise infrastructure load, providing realistic CPU utilization metrics containing natural seasonal cycles and sudden anomalous spikes.

## 3. Running the Training Pipeline
Simply execute the monolithic pipeline script from the `backend` directory:
```bash
python ml_pipeline.py
```
### Pipeline Steps Executed:
1. **Download & Load**: Pulls data into memory.
2. **Feature Extraction**: Generates rolling windows, sine/cosine encodings, and normalizes the dataset using `StandardScaler`.
3. **Isolation Forest Training**: Fits a scikit-learn Isolation Forest model (100 estimators, 1% contamination) as a robust baseline.
4. **PyTorch LSTM-AE Training**: Constructs sequences (window size = 5) and trains a bidirectional LSTM Autoencoder for 10 epochs using MSE loss and Adam optimizer (`lr=0.001`).
5. **Evaluation**: Both models predict on the 20% hold-out test set. 
6. **Serialization**: The pipeline dynamically identifies the best model via the highest F1-Score and exports `.pt` (PyTorch state dictionary), `scaler.pkl`, and `model_config.json` to the `models/` directory.

## 4. Retraining on Custom Data
To retrain on your own AIOps Sentinel PostgreSQL metrics, modify the `DATA_URL` in `ml_pipeline.py` to query your database (e.g., using Prisma client to fetch the `Metric` table where `name="cpu_usage_percent"`).
