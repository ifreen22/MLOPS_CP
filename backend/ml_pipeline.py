import os
import urllib.request
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score, auc, precision_recall_curve
import json
import time
import pickle

# Configuration
DATA_URL = "https://raw.githubusercontent.com/numenta/NAB/master/data/realAWSCloudwatch/ec2_cpu_utilization_24ae8d.csv"
DATA_PATH = "data/ec2_cpu_utilization.csv"
MODEL_DIR = "app/ml_services/anomaly_detection/models"
os.makedirs("data", exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

print("Step 1: Downloading NAB Dataset...")
if not os.path.exists(DATA_PATH):
    urllib.request.urlretrieve(DATA_URL, DATA_PATH)
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Inject synthetic anomalies for evaluation (since this specific NAB file doesn't have labels inline, we'll label top 1% as anomalies for the sake of pipeline training)
threshold = df['value'].quantile(0.99)
df['label'] = (df['value'] > threshold).astype(int)

print("Step 2: Feature Engineering...")
def extract_features(data):
    # Time encoding
    data['hour'] = data['timestamp'].dt.hour
    data['day'] = data['timestamp'].dt.dayofweek
    data['sin_hour'] = np.sin(2 * np.pi * data['hour'] / 24)
    data['cos_hour'] = np.cos(2 * np.pi * data['hour'] / 24)
    
    # Rolling stats
    data['rolling_mean_5'] = data['value'].rolling(window=5, min_periods=1).mean()
    data['rolling_std_5'] = data['value'].rolling(window=5, min_periods=1).std().fillna(0)
    
    # Lag features
    data['lag_1'] = data['value'].shift(1).bfill()
    
    features = ['value', 'sin_hour', 'cos_hour', 'rolling_mean_5', 'rolling_std_5', 'lag_1']
    return data, features

df, feature_cols = extract_features(df)
scaler = StandardScaler()
X = scaler.fit_transform(df[feature_cols])
y = df['label'].values

# Train/Test Split (80/20)
train_size = int(len(X) * 0.8)
X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# Save scaler
with open(os.path.join(MODEL_DIR, "scaler.pkl"), "wb") as f:
    pickle.dump(scaler, f)

print("Step 3 & 4: Model Training (Isolation Forest)...")
start_time = time.time()
iso_forest = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
iso_forest.fit(X_train)
train_time_if = time.time() - start_time

start_time = time.time()
preds_if_raw = iso_forest.predict(X_test)
preds_if = (preds_if_raw == -1).astype(int)
inf_time_if = (time.time() - start_time) / len(X_test) * 1000 # ms per inference

print("Step 3 & 4: Model Training (LSTM Autoencoder)...")
# Prepare data for LSTM (samples, time_steps, features) - we'll use time_steps=5
def create_sequences(data, labels, time_steps=5):
    xs, ys = [], []
    for i in range(len(data) - time_steps):
        xs.append(data[i:(i + time_steps)])
        ys.append(labels[i + time_steps])
    return np.array(xs), np.array(ys)

X_train_seq, _ = create_sequences(X_train, y_train)
X_test_seq, y_test_seq = create_sequences(X_test, y_test)

train_loader = DataLoader(TensorDataset(torch.tensor(X_train_seq, dtype=torch.float32), torch.tensor(X_train_seq, dtype=torch.float32)), batch_size=64, shuffle=True)

class LSTMAutoencoder(nn.Module):
    def __init__(self, n_features, hidden_dim=16):
        super(LSTMAutoencoder, self).__init__()
        self.encoder = nn.LSTM(n_features, hidden_dim, batch_first=True)
        self.decoder = nn.LSTM(hidden_dim, n_features, batch_first=True)
        
    def forward(self, x):
        _, (hidden, _) = self.encoder(x)
        hidden = hidden.permute(1, 0, 2)
        hidden = hidden.repeat(1, x.size(1), 1)
        out, _ = self.decoder(hidden)
        return out

model = LSTMAutoencoder(n_features=X.shape[1])
criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

start_time = time.time()
epochs = 10
model.train()
for epoch in range(epochs):
    for batch_x, _ in train_loader:
        optimizer.zero_grad()
        output = model(batch_x)
        loss = criterion(output, batch_x)
        loss.backward()
        optimizer.step()
train_time_lstm = time.time() - start_time

model.eval()
start_time = time.time()
with torch.no_grad():
    test_tensor = torch.tensor(X_test_seq, dtype=torch.float32)
    reconstructions = model(test_tensor)
    mse_loss = torch.mean(torch.pow(test_tensor - reconstructions, 2), dim=(1, 2)).numpy()
inf_time_lstm = (time.time() - start_time) / len(X_test_seq) * 1000 # ms per inference

# Threshold for LSTM
threshold_lstm = np.percentile(mse_loss, 99)
preds_lstm = (mse_loss > threshold_lstm).astype(int)

print("Step 5: Evaluation...")
def evaluate_model(y_true, y_pred, name, train_time, inf_time):
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred).tolist()
    return {
        "model": name,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "confusion_matrix": cm,
        "training_time_sec": train_time,
        "inference_latency_ms": inf_time
    }

results = [
    evaluate_model(y_test, preds_if, "Isolation Forest", train_time_if, inf_time_if),
    evaluate_model(y_test_seq, preds_lstm, "LSTM Autoencoder", train_time_lstm, inf_time_lstm)
]

with open(os.path.join(MODEL_DIR, "model_comparison.json"), "w") as f:
    json.dump(results, f, indent=4)

print("Best model selection (based on F1-score)...")
best_model_name = max(results, key=lambda x: x['f1'])['model']
print(f"Selected: {best_model_name}")

if best_model_name == "LSTM Autoencoder":
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, "best_model.pt"))
    with open(os.path.join(MODEL_DIR, "model_config.json"), "w") as f:
        json.dump({"type": "lstm", "features": feature_cols, "threshold": float(threshold_lstm)}, f)
else:
    with open(os.path.join(MODEL_DIR, "best_model.pkl"), "wb") as f:
        pickle.dump(iso_forest, f)
    with open(os.path.join(MODEL_DIR, "model_config.json"), "w") as f:
        json.dump({"type": "isolation_forest", "features": feature_cols}, f)

print("Pipeline completed successfully.")
