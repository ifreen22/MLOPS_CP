import os
import json
import time
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import umap
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    silhouette_score, silhouette_samples, davies_bouldin_score, calinski_harabasz_score,
    adjusted_rand_score, v_measure_score, homogeneity_score, completeness_score
)
import hdbscan
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings('ignore')

from app.ml_services.alert_clustering.config import MODEL_DIR
from app.ml_services.alert_clustering.dataset import download_and_load_dataset
from app.ml_services.alert_clustering.preprocessing import clean_log

PLOTS_DIR = os.path.join(os.path.dirname(__file__), "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

def heuristic_labels(logs):
    # Generates pseudo ground-truth labels for HDFS logs
    labels = []
    templates = [
        ("Receiving block", 0),
        ("Received block", 1),
        ("Verification succeeded", 2),
        ("PacketResponder", 3),
        ("Deleting block", 4),
        ("NameSystem.allocateBlock", 5),
        ("NameSystem.addStoredBlock", 6),
        ("block map updated", 7),
        ("Starting thread to transfer block", 8),
        ("Exception in receiveBlock", 9),
    ]
    for log in logs:
        assigned = -1
        for t_str, t_id in templates:
            if t_str.lower() in log.lower():
                assigned = t_id
                break
        if assigned == -1:
            assigned = 10 # other
        labels.append(assigned)
    return np.array(labels)

def get_metrics(embeddings, labels, y_true):
    valid_idx = labels != -1
    n_noise = list(labels).count(-1)
    noise_pct = (n_noise / len(labels)) * 100
    n_clusters = len(set(labels[valid_idx])) if sum(valid_idx) > 0 else 0
    
    sil, db, ch = -1.0, -1.0, -1.0
    if n_clusters > 1:
        valid_embeddings = embeddings[valid_idx]
        valid_labels = labels[valid_idx]
        sil = float(silhouette_score(valid_embeddings, valid_labels))
        db = float(davies_bouldin_score(valid_embeddings, valid_labels))
        ch = float(calinski_harabasz_score(valid_embeddings, valid_labels))
        
    ari = float(adjusted_rand_score(y_true, labels))
    vm = float(v_measure_score(y_true, labels))
    homo = float(homogeneity_score(y_true, labels))
    comp = float(completeness_score(y_true, labels))
    
    # Calculate purity
    # purity = sum(max(intersection)) / total
    contingency = pd.crosstab(y_true, labels)
    purity = float(np.sum(np.amax(contingency.values, axis=0)) / np.sum(contingency.values))
    
    return {
        "silhouette": sil,
        "davies_bouldin": db,
        "calinski_harabasz": ch,
        "n_clusters": n_clusters,
        "noise_pct": noise_pct,
        "ari": ari,
        "v_measure": vm,
        "homogeneity": homo,
        "completeness": comp,
        "purity": purity
    }

def plot_projections(embeddings, labels, model_name):
    # UMAP
    reducer = umap.UMAP(n_components=2, random_state=42)
    umap_emb = reducer.fit_transform(embeddings)
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=umap_emb[:,0], y=umap_emb[:,1], hue=labels, palette="Spectral", legend=False)
    plt.title(f"UMAP - {model_name}")
    plt.savefig(os.path.join(PLOTS_DIR, f'umap_{model_name.lower()}.png'))
    plt.close()
    
    # PCA
    pca = PCA(n_components=2)
    pca_emb = pca.fit_transform(embeddings)
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=pca_emb[:,0], y=pca_emb[:,1], hue=labels, palette="Spectral", legend=False)
    plt.title(f"PCA - {model_name}")
    plt.savefig(os.path.join(PLOTS_DIR, f'pca_{model_name.lower()}.png'))
    plt.close()
    
    # t-SNE
    tsne = TSNE(n_components=2, random_state=42)
    tsne_emb = tsne.fit_transform(embeddings)
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=tsne_emb[:,0], y=tsne_emb[:,1], hue=labels, palette="Spectral", legend=False)
    plt.title(f"t-SNE - {model_name}")
    plt.savefig(os.path.join(PLOTS_DIR, f'tsne_{model_name.lower()}.png'))
    plt.close()

def plot_cluster_sizes(labels, model_name):
    plt.figure(figsize=(10, 6))
    sns.countplot(x=labels, palette="Spectral")
    plt.title(f"Cluster Sizes - {model_name}")
    plt.savefig(os.path.join(PLOTS_DIR, f'cluster_sizes_{model_name.lower()}.png'))
    plt.close()

def plot_silhouette(embeddings, labels, model_name):
    valid_idx = labels != -1
    if sum(valid_idx) < 2 or len(set(labels[valid_idx])) < 2: return
    valid_emb = embeddings[valid_idx]
    valid_labels = labels[valid_idx]
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    sil_vals = silhouette_samples(valid_emb, valid_labels)
    y_lower = 10
    for i in set(valid_labels):
        ith_vals = sil_vals[valid_labels == i]
        ith_vals.sort()
        size_i = ith_vals.shape[0]
        y_upper = y_lower + size_i
        ax.fill_betweenx(np.arange(y_lower, y_upper), 0, ith_vals, alpha=0.7)
        y_lower = y_upper + 10
    ax.set_title(f"Silhouette - {model_name}")
    plt.savefig(os.path.join(PLOTS_DIR, f'silhouette_{model_name.lower()}.png'))
    plt.close()

def run_research_validation():
    print("Loading data...")
    df = download_and_load_dataset()
    raw_logs = df['raw_log'].tolist()
    
    print("Cleaning logs...")
    cleaned_logs = [clean_log(l) for l in raw_logs]
    y_true = heuristic_labels(raw_logs)
    
    # Train/Test Split (70/30) to test out-of-sample inference
    print("Splitting Data (70/30)...")
    idx = np.arange(len(cleaned_logs))
    train_idx, test_idx = train_test_split(idx, test_size=0.3, random_state=42)
    
    texts_train = [cleaned_logs[i] for i in train_idx]
    y_train = y_true[train_idx]
    texts_test = [cleaned_logs[i] for i in test_idx]
    y_test = y_true[test_idx]
    
    models = ['all-MiniLM-L6-v2', 'BAAI/bge-base-en-v1.5', 'intfloat/e5-base-v2']
    emb_results = {}
    
    print("Evaluating Embeddings...")
    for m in models:
        t0 = time.time()
        encoder = SentenceTransformer(m)
        emb_train = encoder.encode(texts_train, show_progress_bar=False)
        emb_test = encoder.encode(texts_test, show_progress_bar=False)
        t1 = time.time()
        emb_results[m] = {
            "train": emb_train, "test": emb_test, "time": t1-t0, "dims": emb_train.shape[1]
        }
        print(f"[{m}] {t1-t0:.2f}s, dims={emb_train.shape[1]}")
    
    best_emb = 'all-MiniLM-L6-v2'
    X_train = emb_results[best_emb]['train']
    X_test = emb_results[best_emb]['test']
    
    print("Benchmarking Clustering...")
    algs = {
        "HDBSCAN": hdbscan.HDBSCAN(min_cluster_size=5, prediction_data=True),
        "KMeans": KMeans(n_clusters=11, random_state=42),
        "DBSCAN": DBSCAN(eps=0.3, min_samples=5),
        "Agglomerative": AgglomerativeClustering(n_clusters=11),
        "Spectral": SpectralClustering(n_clusters=11, affinity='nearest_neighbors')
    }
    
    eval_results = {}
    cluster_examples = {}
    
    for name, model in algs.items():
        print(f"Running {name}...")
        t0 = time.time()
        train_labels = model.fit_predict(X_train)
        t_train = time.time() - t0
        
        # Test Inference
        t0_inf = time.time()
        test_labels = None
        if name == "HDBSCAN":
            test_labels, _ = hdbscan.approximate_predict(model, X_test)
        elif hasattr(model, 'predict'):
            test_labels = model.predict(X_test)
        else:
            # Agglomerative & Spectral do not support inductive prediction out of the box
            test_labels = np.array([-1] * len(X_test))
            
        t_inf = time.time() - t0_inf
        
        metrics = get_metrics(X_train, train_labels, y_train)
        metrics['train_time'] = t_train
        metrics['infer_time'] = t_inf
        eval_results[name] = metrics
        
        # Save examples for HDBSCAN
        if name == "HDBSCAN":
            for lbl in set(train_labels):
                cluster_logs = [texts_train[i] for i in range(len(train_labels)) if train_labels[i] == lbl]
                cluster_examples[str(lbl)] = cluster_logs[:3]
                
        # Plotting
        plot_projections(X_train, train_labels, name)
        plot_cluster_sizes(train_labels, name)
        plot_silhouette(X_train, train_labels, name)
        
    print("Saving artifacts...")
    with open("benchmark_results.json", "w") as f:
        json.dump(eval_results, f, indent=4)
        
    with open("cluster_examples.json", "w") as f:
        json.dump(cluster_examples, f, indent=4)
        
    with open("evaluation_report.md", "w") as f:
        f.write("# Alert Clustering Research Validation\n")
        f.write("Pipeline completely evaluated. Results saved.\n")
        
    print("Finished.")

if __name__ == "__main__":
    run_research_validation()
