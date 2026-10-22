import os
import json
import time
import pickle
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (precision_score, recall_score, f1_score, accuracy_score,
                             roc_auc_score, average_precision_score, confusion_matrix,
                             roc_curve, precision_recall_curve)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# Paths
DATA_PATH = "data/ec2_cpu_utilization.csv"
MODEL_DIR = "app/ml_services/anomaly_detection/models"
VIS_DIR = "app/ml_services/anomaly_detection/visualizations"
os.makedirs(VIS_DIR, exist_ok=True)

report_data = {}

# 1. Dataset
df = pd.read_csv(DATA_PATH)
df['timestamp'] = pd.to_datetime(df['timestamp'])
threshold = df['value'].quantile(0.99)
df['label'] = (df['value'] > threshold).astype(int)

total_samples = len(df)
num_anomalies = int(df['label'].sum())
num_normal = total_samples - num_anomalies
train_size = int(total_samples * 0.8)
test_size = total_samples - train_size

report_data['dataset'] = {
    'name': 'NAB AWS CloudWatch ec2_cpu_utilization',
    'total_samples': total_samples,
    'train_samples': train_size,
    'test_samples': test_size,
    'num_anomalies': num_anomalies,
    'num_normal': num_normal
}

# 2. Features
df['hour'] = df['timestamp'].dt.hour
df['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24)
df['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24)
df['rolling_mean_5'] = df['value'].rolling(window=5, min_periods=1).mean()
df['rolling_std_5'] = df['value'].rolling(window=5, min_periods=1).std().fillna(0)
df['lag_1'] = df['value'].shift(1).bfill()

feature_cols = ['value', 'sin_hour', 'cos_hour', 'rolling_mean_5', 'rolling_std_5', 'lag_1']

scaler = StandardScaler()
X = scaler.fit_transform(df[feature_cols])
y = df['label'].values

X_train, X_test = X[:train_size], X[train_size:]
y_train, y_test = y[:train_size], y[train_size:]

# 3 & 4. Models
# Isolation Forest
start = time.time()
iso = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
iso.fit(X_train)
train_time_iso = time.time() - start

start = time.time()
scores_iso = -iso.score_samples(X_test) # Higher score = more anomalous
preds_iso = (iso.predict(X_test) == -1).astype(int)
inf_time_iso = (time.time() - start) / len(X_test) * 1000

# LSTM
def create_sequences(data, labels, time_steps=5):
    xs, ys = [], []
    for i in range(len(data) - time_steps):
        xs.append(data[i:(i + time_steps)])
        ys.append(labels[i + time_steps])
    return np.array(xs), np.array(ys)

X_train_seq, _ = create_sequences(X_train, y_train)
X_test_seq, y_test_seq = create_sequences(X_test, y_test)

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

train_loader = DataLoader(TensorDataset(torch.tensor(X_train_seq, dtype=torch.float32), torch.tensor(X_train_seq, dtype=torch.float32)), batch_size=64, shuffle=True)

train_losses = []
start = time.time()
epochs = 10
model.train()
for epoch in range(epochs):
    epoch_loss = 0
    for batch_x, _ in train_loader:
        optimizer.zero_grad()
        output = model(batch_x)
        loss = criterion(output, batch_x)
        loss.backward()
        optimizer.step()
        epoch_loss += loss.item()
    train_losses.append(epoch_loss / len(train_loader))
train_time_lstm = time.time() - start

model.eval()
start = time.time()
with torch.no_grad():
    test_tensor = torch.tensor(X_test_seq, dtype=torch.float32)
    reconstructions = model(test_tensor)
    scores_lstm = torch.mean(torch.pow(test_tensor - reconstructions, 2), dim=(1, 2)).numpy()
inf_time_lstm = (time.time() - start) / len(X_test_seq) * 1000

thresh_lstm = np.percentile(scores_lstm, 99)
preds_lstm = (scores_lstm > thresh_lstm).astype(int)

# Evaluation Helper
def eval_metrics(y_true, y_pred, y_scores):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0
    return {
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_scores)),
        "pr_auc": float(average_precision_score(y_true, y_scores)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "fpr": float(fpr),
        "fnr": float(fnr)
    }

report_data['models'] = {
    "IsolationForest": {
        "training_time": train_time_iso,
        "inference_latency_ms": inf_time_iso,
        "hyperparameters": {"n_estimators": 100, "contamination": 0.01},
        "metrics": eval_metrics(y_test, preds_iso, scores_iso)
    },
    "LSTMAutoencoder": {
        "training_time": train_time_lstm,
        "inference_latency_ms": inf_time_lstm,
        "hyperparameters": {"hidden_dim": 16, "epochs": 10, "batch_size": 64, "learning_rate": 0.001, "optimizer": "Adam", "loss": "MSE"},
        "metrics": eval_metrics(y_test_seq, preds_lstm, scores_lstm)
    }
}

# 6. Visualizations
# Loss Curve
plt.figure()
plt.plot(range(1, epochs+1), train_losses, label='Train Loss')
plt.title('LSTM Training Loss')
plt.xlabel('Epoch')
plt.ylabel('MSE Loss')
plt.legend()
plt.savefig(f"{VIS_DIR}/loss_curve.png")

# ROC Curve
fpr_iso, tpr_iso, _ = roc_curve(y_test, scores_iso)
fpr_lstm, tpr_lstm, _ = roc_curve(y_test_seq, scores_lstm)
plt.figure()
plt.plot(fpr_iso, tpr_iso, label='Isolation Forest')
plt.plot(fpr_lstm, tpr_lstm, label='LSTM Autoencoder')
plt.title('ROC Curve')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.legend()
plt.savefig(f"{VIS_DIR}/roc_curve.png")

# PR Curve
prec_iso, rec_iso, _ = precision_recall_curve(y_test, scores_iso)
prec_lstm, rec_lstm, _ = precision_recall_curve(y_test_seq, scores_lstm)
plt.figure()
plt.plot(rec_iso, prec_iso, label='Isolation Forest')
plt.plot(rec_lstm, prec_lstm, label='LSTM Autoencoder')
plt.title('Precision-Recall Curve')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.legend()
plt.savefig(f"{VIS_DIR}/pr_curve.png")

# Anomaly Scores Distribution
plt.figure()
plt.hist(scores_iso, bins=50, alpha=0.5, label='Isolation Forest')
plt.hist(scores_lstm, bins=50, alpha=0.5, label='LSTM Autoencoder')
plt.title('Anomaly Score Distribution')
plt.xlabel('Score')
plt.ylabel('Frequency')
plt.legend()
plt.savefig(f"{VIS_DIR}/anomaly_scores.png")

# Confusion Matrices
fig, ax = plt.subplots(1, 2, figsize=(10, 4))
ax[0].matshow([[report_data['models']['IsolationForest']['metrics']['confusion_matrix']['tn'], report_data['models']['IsolationForest']['metrics']['confusion_matrix']['fp']],
               [report_data['models']['IsolationForest']['metrics']['confusion_matrix']['fn'], report_data['models']['IsolationForest']['metrics']['confusion_matrix']['tp']]], cmap='Blues')
ax[0].set_title('Isolation Forest')
ax[0].set_ylabel('True')
ax[0].set_xlabel('Predicted')

ax[1].matshow([[report_data['models']['LSTMAutoencoder']['metrics']['confusion_matrix']['tn'], report_data['models']['LSTMAutoencoder']['metrics']['confusion_matrix']['fp']],
               [report_data['models']['LSTMAutoencoder']['metrics']['confusion_matrix']['fn'], report_data['models']['LSTMAutoencoder']['metrics']['confusion_matrix']['tp']]], cmap='Blues')
ax[1].set_title('LSTM Autoencoder')
ax[1].set_ylabel('True')
ax[1].set_xlabel('Predicted')
plt.savefig(f"{VIS_DIR}/confusion_matrix.png")

# Feature Importance Surrogate (Random Forest)
rf = RandomForestClassifier(n_estimators=50, random_state=42)
rf.fit(X_test, preds_iso) # Predict feature importance based on IF anomalies
plt.figure()
plt.barh(feature_cols, rf.feature_importances_)
plt.title('Feature Importance (Surrogate)')
plt.savefig(f"{VIS_DIR}/feature_importance.png")

with open(f"{VIS_DIR}/report_data.json", "w") as f:
    json.dump(report_data, f, indent=4)
print("Report data generated.")
