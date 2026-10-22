import os, json, time, numpy as np, pandas as pd
from sklearn.metrics import adjusted_rand_score, v_measure_score, homogeneity_score, completeness_score
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer
import hdbscan
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
from app.ml_services.alert_clustering.dataset import download_and_load_dataset
from app.ml_services.alert_clustering.preprocessing import clean_log
from app.ml_services.alert_clustering.research_validation import heuristic_labels, get_metrics

def main():
    print("Loading data...")
    df = download_and_load_dataset()
    raw = df['raw_log'].tolist()
    clean = [clean_log(l) for l in raw]
    y = heuristic_labels(raw)
    
    t, _, yt, _ = train_test_split(clean, y, test_size=0.3, random_state=42)
    
    print("Encoding...")
    enc = SentenceTransformer('all-MiniLM-L6-v2')
    emb = enc.encode(t, show_progress_bar=False)
    
    algs = {
        'HDBSCAN': hdbscan.HDBSCAN(min_cluster_size=5),
        'KMeans': KMeans(n_clusters=11, random_state=42),
        'DBSCAN': DBSCAN(eps=0.3, min_samples=5),
        'Agglomerative': AgglomerativeClustering(n_clusters=11),
        'Spectral': SpectralClustering(n_clusters=11, affinity='nearest_neighbors')
    }
    
    print("Running Clustering Algorithms...")
    for n, m in algs.items():
        l = m.fit_predict(emb)
        metrics = get_metrics(emb, l, yt)
        print(f"[{n}] Purity: {metrics['purity']:.3f}, ARI: {metrics['ari']:.3f}, VM: {metrics['v_measure']:.3f}, Sil: {metrics['silhouette']:.3f}")

if __name__ == "__main__":
    main()
