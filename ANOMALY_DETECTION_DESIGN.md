# Anomaly Detection Design
**Module**: ML Pipeline (Phase 4.1)

## 1. System Architecture
The Anomaly Detection Engine operates as a continuous evaluation pipeline scoring raw infrastructure telemetry (CPU/Memory streams) using a pre-trained **LSTM Autoencoder**.

### Components
- **Data Ingestion**: FastAPI `POST /ml/anomaly/predict` routes incoming metric streams.
- **Preprocessor**: `service.py` scales the data (Z-Score) and performs cyclical encoding for timestamps.
- **Model Layer**: `models.py` defines the PyTorch LSTM-AE architecture.
- **Prediction Matrix**: Model output computes Mean Squared Error (MSE) reconstruction loss. If $MSE > \text{Threshold}_{p99}$, it flags the payload as anomalous.

## 2. Feature Engineering Logic
In `ml_pipeline.py`, we implement:
- **Missing Value Handling**: Forward filling (`ffill`) followed by backward filling (`bfill`).
- **Time Encoding**: Transforming timestamps into continuous sine/cosine waves (`sin_hour`, `cos_hour`) to capture daily cyclical patterns.
- **Rolling Statistics**: 5-minute rolling means and standard deviations (`rolling_mean_5`, `rolling_std_5`) to provide the model with a smoothed temporal context.
- **Lag Features**: Shifted values (`lag_1`) to allow the model to easily compute instantaneous delta changes.

## 3. End-to-End Integration
The frontend (React Dashboard) polls the FastAPI backend. Behind the scenes, the API invokes the `AnomalyDetectionService` singleton which holds the PyTorch model entirely in memory to achieve sub-millisecond inference latency suitable for streaming data.
