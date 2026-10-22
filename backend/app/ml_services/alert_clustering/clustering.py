from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering, SpectralClustering
import hdbscan

class ClusteringModels:
    @staticmethod
    def get_hdbscan(min_cluster_size=5):
        return hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean', cluster_selection_method='eom', prediction_data=True)

    @staticmethod
    def get_kmeans(n_clusters=10):
        return KMeans(n_clusters=n_clusters, random_state=42)

    @staticmethod
    def get_dbscan(eps=0.5, min_samples=5):
        return DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')

    @staticmethod
    def get_agglomerative(n_clusters=10):
        return AgglomerativeClustering(n_clusters=n_clusters)

    @staticmethod
    def get_spectral(n_clusters=10):
        return SpectralClustering(n_clusters=n_clusters, affinity='nearest_neighbors', random_state=42)

def run_clustering_benchmark(embeddings):
    models = {
        "HDBSCAN": ClusteringModels.get_hdbscan(),
        "KMeans": ClusteringModels.get_kmeans(n_clusters=15),
        "DBSCAN": ClusteringModels.get_dbscan(eps=0.3),
        "Agglomerative": ClusteringModels.get_agglomerative(n_clusters=15),
        "Spectral": ClusteringModels.get_spectral(n_clusters=15)
    }
    
    labels_dict = {}
    for name, model in models.items():
        if name == "HDBSCAN":
            labels = model.fit_predict(embeddings)
        else:
            labels = model.fit_predict(embeddings)
        labels_dict[name] = labels
        
    return labels_dict
