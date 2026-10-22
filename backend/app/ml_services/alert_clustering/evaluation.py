from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import numpy as np

def evaluate_clusters(embeddings, labels):
    # Filter out noise (-1) for sklearn metrics, as they often fail or skew heavily if noise is included as a cluster
    valid_idx = labels != -1
    valid_labels = labels[valid_idx]
    valid_embeddings = embeddings[valid_idx]
    
    n_clusters = len(set(valid_labels))
    n_noise = list(labels).count(-1)
    
    if n_clusters < 2:
        return {
            "silhouette": -1,
            "davies_bouldin": -1,
            "calinski_harabasz": -1,
            "compression_ratio": -1,
            "n_clusters": n_clusters,
            "n_noise": n_noise
        }
        
    sil = silhouette_score(valid_embeddings, valid_labels, metric='euclidean')
    db = davies_bouldin_score(valid_embeddings, valid_labels)
    ch = calinski_harabasz_score(valid_embeddings, valid_labels)
    
    compression_ratio = n_clusters / len(labels)
    
    return {
        "silhouette": float(sil),
        "davies_bouldin": float(db),
        "calinski_harabasz": float(ch),
        "compression_ratio": float(compression_ratio),
        "n_clusters": n_clusters,
        "n_noise": n_noise
    }
