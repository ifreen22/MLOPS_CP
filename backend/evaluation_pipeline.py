import os
import json
import time
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import umap
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, silhouette_samples, davies_bouldin_score, calinski_harabasz_score
import hdbscan
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
from sentence_transformers import SentenceTransformer
import warnings
warnings.filterwarnings('ignore')

from app.ml_services.alert_clustering.config import MODEL_DIR, VIS_DIR
from app.ml_services.alert_clustering.dataset import download_and_load_dataset
from app.ml_services.alert_clustering.preprocessing import preprocess_dataframe

def get_metrics(embeddings, labels, t_train, t_infer):
    valid_idx = labels != -1
    n_noise = list(labels).count(-1)
    noise_pct = (n_noise / len(labels)) * 100
    n_clusters = len(set(labels[valid_idx])) if sum(valid_idx) > 0 else 0
    
    if n_clusters > 1:
        valid_embeddings = embeddings[valid_idx]
        valid_labels = labels[valid_idx]
        sil = float(silhouette_score(valid_embeddings, valid_labels))
        db = float(davies_bouldin_score(valid_embeddings, valid_labels))
        ch = float(calinski_harabasz_score(valid_embeddings, valid_labels))
    else:
        sil, db, ch = -1.0, -1.0, -1.0
        
    return {
        "silhouette": sil,
        "davies_bouldin": db,
        "calinski_harabasz": ch,
        "n_clusters": n_clusters,
        "noise_pct": noise_pct,
        "train_time": t_train,
        "infer_time": t_infer
    }

def plot_silhouette(embeddings, labels, model_name):
    valid_idx = labels != -1
    if sum(valid_idx) < 2 or len(set(labels[valid_idx])) < 2:
        return
        
    valid_embeddings = embeddings[valid_idx]
    valid_labels = labels[valid_idx]
    n_clusters = len(set(valid_labels))
    
    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    silhouette_vals = silhouette_samples(valid_embeddings, valid_labels)
    y_lower, y_upper = 10, 0
    
    for i in set(valid_labels):
        ith_vals = silhouette_vals[valid_labels == i]
        ith_vals.sort()
        size_i = ith_vals.shape[0]
        y_upper = y_lower + size_i
        ax.fill_betweenx(np.arange(y_lower, y_upper), 0, ith_vals, alpha=0.7)
        y_lower = y_upper + 10
        
    ax.set_title(f"Silhouette Plot - {model_name}")
    ax.set_xlabel("Silhouette Coefficient Values")
    ax.set_ylabel("Cluster Label")
    plt.savefig(os.path.join(VIS_DIR, f'silhouette_{model_name.lower()}.png'))
    plt.close()

def plot_projections(embeddings, labels, model_name):
    # UMAP
    reducer = umap.UMAP(n_components=2, random_state=42)
    umap_emb = reducer.fit_transform(embeddings)
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=umap_emb[:,0], y=umap_emb[:,1], hue=labels, palette="Spectral", s=30, legend=False)
    plt.title(f"UMAP Projection - {model_name}")
    plt.savefig(os.path.join(VIS_DIR, f'umap_{model_name.lower()}.png'))
    plt.close()
    
    # PCA
    pca = PCA(n_components=2)
    pca_emb = pca.fit_transform(embeddings)
    plt.figure(figsize=(10, 8))
    sns.scatterplot(x=pca_emb[:,0], y=pca_emb[:,1], hue=labels, palette="Spectral", s=30, legend=False)
    plt.title(f"PCA Projection - {model_name}")
    plt.savefig(os.path.join(VIS_DIR, f'pca_{model_name.lower()}.png'))
    plt.close()

def plot_cluster_sizes(labels, model_name):
    valid_labels = [l for l in labels if l != -1]
    if not valid_labels: return
    plt.figure(figsize=(10, 6))
    sns.countplot(x=valid_labels, palette="Spectral")
    plt.title(f"Cluster Size Distribution - {model_name}")
    plt.savefig(os.path.join(VIS_DIR, f'cluster_sizes_{model_name.lower()}.png'))
    plt.close()

def run_evaluation():
    print("Loading data...")
    df = download_and_load_dataset()
    df = preprocess_dataframe(df)
    texts = df['cleaned_log'].tolist()
    
    # Step 1: Embeddings Benchmark
    print("Benchmarking Embeddings...")
    models = ['all-MiniLM-L6-v2']
    emb_results = {}
    
    # Check if we can just load BAAI or if it takes too long.
    for m in models:
        t0 = time.time()
        encoder = SentenceTransformer(m)
        emb = encoder.encode(texts, show_progress_bar=False)
        t1 = time.time()
        emb_results[m] = {"embeddings": emb, "time": t1-t0, "dims": emb.shape[1]}
        print(f"[{m}] {t1-t0:.2f}s, dims={emb.shape[1]}")
        
    best_emb_name = 'all-MiniLM-L6-v2' # Pre-decided based on typical AIOps speed reqs
    best_emb = emb_results[best_emb_name]['embeddings']
    
    # Step 2: Clustering Benchmark
    print("Benchmarking Clustering Algorithms...")
    algs = {
        "HDBSCAN": hdbscan.HDBSCAN(min_cluster_size=3, prediction_data=True),
        "KMeans": KMeans(n_clusters=15, random_state=42),
        "DBSCAN": DBSCAN(eps=0.5, min_samples=3),
        "Agglomerative": AgglomerativeClustering(n_clusters=15),
        "Spectral": SpectralClustering(n_clusters=15, affinity='nearest_neighbors')
    }
    
    results = {}
    for name, model in algs.items():
        t0 = time.time()
        labels = model.fit_predict(best_emb)
        t_train = time.time() - t0
        
        # Approximate Inference Time
        t0_inf = time.time()
        if name == "HDBSCAN":
            hdbscan.approximate_predict(model, best_emb[:10])
        else:
            if hasattr(model, 'predict'):
                model.predict(best_emb[:10])
        t_inf = (time.time() - t0_inf) / 10.0
        
        metrics = get_metrics(best_emb, labels, t_train, t_inf)
        results[name] = metrics
        
        print(f"[{name}] Sil: {metrics['silhouette']:.3f}, Clusters: {metrics['n_clusters']}, Noise: {metrics['noise_pct']:.1f}%")
        
        # Plots
        plot_silhouette(best_emb, labels, name)
        plot_projections(best_emb, labels, name)
        plot_cluster_sizes(labels, name)
        
    # Save Benchmark
    with open(os.path.join(MODEL_DIR, "benchmark_results.json"), "w") as f:
        json.dump(results, f, indent=4)
        
    # Save Pipeline
    best_clusterer = algs["HDBSCAN"]
    with open(os.path.join(MODEL_DIR, "alert_clustering_pipeline.pkl"), "wb") as f:
        pickle.dump(best_clusterer, f)
        
    print("Done!")

if __name__ == "__main__":
    run_evaluation()
