import json
import time
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.metrics import (precision_score, recall_score, f1_score, accuracy_score, 
                             roc_auc_score, average_precision_score, confusion_matrix)

# Load data
df = pd.read_csv("data/ec2_cpu_utilization.csv")
df['timestamp'] = pd.to_datetime(df['timestamp'])
threshold = df['value'].quantile(0.99)
df['label'] = (df['value'] > threshold).astype(int)

# Features
df['hour'] = df['timestamp'].dt.hour
df['sin_hour'] = np.sin(2 * np.pi * df['hour'] / 24)
df['cos_hour'] = np.cos(2 * np.pi * df['hour'] / 24)
df['rolling_mean_5'] = df['value'].rolling(window=5, min_periods=1).mean()
df['rolling_std_5'] = df['value'].rolling(window=5, min_periods=1).std().fillna(0)
df['lag_1'] = df['value'].shift(1).bfill()

features = ['value', 'sin_hour', 'cos_hour', 'rolling_mean_5', 'rolling_std_5', 'lag_1']
X = StandardScaler().fit_transform(df[features])
y = df['label'].values

# Splits
train_end = int(len(X) * 0.7)
val_end = int(len(X) * 0.8)
X_train, y_train = X[:train_end], y[:train_end]
X_val, y_val = X[train_end:val_end], y[train_end:val_end]
X_test, y_test = X[val_end:], y[val_end:]

results = {}

def get_metrics(y_true, y_pred, y_scores, name, train_t, inf_t):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return {
        "model": name,
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "accuracy": accuracy_score(y_true, y_pred),
        "roc_auc": roc_auc_score(y_true, y_scores),
        "pr_auc": average_precision_score(y_true, y_scores),
        "fpr": fp / (fp + tn) if (fp+tn) > 0 else 0,
        "fnr": fn / (fn + tp) if (fn+tp) > 0 else 0,
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "train_time": train_t,
        "inf_time_ms": inf_t * 1000
    }

# Isolation Forest
t0 = time.time()
iso = IsolationForest(n_estimators=100, contamination=0.01, random_state=42)
iso.fit(X_train)
t_train = time.time() - t0
t0 = time.time()
scores = -iso.score_samples(X_test)
preds = (iso.predict(X_test) == -1).astype(int)
t_inf = (time.time() - t0) / len(X_test)
results["IsolationForest"] = get_metrics(y_test, preds, scores, "IsolationForest", t_train, t_inf)

# Local Outlier Factor (LOF)
t0 = time.time()
lof = LocalOutlierFactor(n_neighbors=20, novelty=True, contamination=0.01)
lof.fit(X_train)
t_train = time.time() - t0
t0 = time.time()
scores = -lof.score_samples(X_test)
preds = (lof.predict(X_test) == -1).astype(int)
t_inf = (time.time() - t0) / len(X_test)
results["LOF"] = get_metrics(y_test, preds, scores, "LOF", t_train, t_inf)

# One-Class SVM
t0 = time.time()
ocsvm = OneClassSVM(nu=0.01, kernel='rbf', gamma='scale')
ocsvm.fit(X_train)
t_train = time.time() - t0
t0 = time.time()
scores = -ocsvm.score_samples(X_test)
preds = (ocsvm.predict(X_test) == -1).astype(int)
t_inf = (time.time() - t0) / len(X_test)
results["OCSVM"] = get_metrics(y_test, preds, scores, "OCSVM", t_train, t_inf)

# LSTM-AE
def create_seq(X, y, steps=10):
    xs, ys = [], []
    for i in range(len(X)-steps):
        xs.append(X[i:i+steps])
        ys.append(y[i+steps])
    return np.array(xs), np.array(ys)

X_tr_seq, y_tr_seq = create_seq(X_train, y_train)
X_v_seq, y_v_seq = create_seq(X_val, y_val)
X_te_seq, y_te_seq = create_seq(X_test, y_test)

class LSTMAE(nn.Module):
    def __init__(self):
        super().__init__()
        self.enc = nn.LSTM(6, 16, batch_first=True)
        self.dec = nn.LSTM(16, 6, batch_first=True)
    def forward(self, x):
        _, (h, _) = self.enc(x)
        h = h.permute(1, 0, 2)
        out, _ = self.dec(h.repeat(1, x.size(1), 1))
        return out

model = LSTMAE()
opt = torch.optim.Adam(model.parameters(), lr=0.001)
crit = nn.MSELoss()
dl = DataLoader(TensorDataset(torch.tensor(X_tr_seq, dtype=torch.float32)), batch_size=64, shuffle=True)

t0 = time.time()
best_loss = float('inf')
patience = 5
stall = 0
for ep in range(100):
    model.train()
    for batch in dl:
        opt.zero_grad()
        l = crit(model(batch[0]), batch[0])
        l.backward()
        opt.step()
    model.eval()
    with torch.no_grad():
        v_t = torch.tensor(X_v_seq, dtype=torch.float32)
        v_l = crit(model(v_t), v_t).item()
    if v_l < best_loss:
        best_loss = v_l
        stall = 0
    else:
        stall += 1
    if stall >= patience:
        break
t_train = time.time() - t0

model.eval()
with torch.no_grad():
    v_scores = torch.mean(torch.pow(torch.tensor(X_v_seq, dtype=torch.float32) - model(torch.tensor(X_v_seq, dtype=torch.float32)), 2), dim=(1,2)).numpy()
    best_thresh, best_f1 = np.percentile(v_scores, 99), 0
    for p in np.linspace(80, 99.9, 100):
        th = np.percentile(v_scores, p)
        p_val = (v_scores > th).astype(int)
        f = f1_score(y_v_seq, p_val, zero_division=0)
        if f > best_f1:
            best_f1 = f
            best_thresh = th
    
    t0 = time.time()
    te_scores = torch.mean(torch.pow(torch.tensor(X_te_seq, dtype=torch.float32) - model(torch.tensor(X_te_seq, dtype=torch.float32)), 2), dim=(1,2)).numpy()
    preds = (te_scores > best_thresh).astype(int)
    t_inf = (time.time() - t0) / len(X_te_seq)
    results["LSTM-AE"] = get_metrics(y_te_seq, preds, te_scores, "LSTM-AE", t_train, t_inf)

with open("benchmark_results.json", "w") as f:
    json.dump(results, f, indent=4)
print("Benchmark completed.")
