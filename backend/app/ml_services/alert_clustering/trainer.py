import json
import os
import pickle
from app.ml_services.alert_clustering.config import MODEL_DIR
from app.ml_services.alert_clustering.dataset import download_and_load_dataset
from app.ml_services.alert_clustering.preprocessing import preprocess_dataframe
from app.ml_services.alert_clustering.embeddings import benchmark_embeddings
from app.ml_services.alert_clustering.clustering import run_clustering_benchmark, ClusteringModels
from app.ml_services.alert_clustering.evaluation import evaluate_clusters
from app.ml_services.alert_clustering.visualization import generate_all_visualizations

def run_pipeline():
    print("Step 1: Dataset")
    df = download_and_load_dataset()
    
    print("Step 2: Preprocessing")
    df = preprocess_dataframe(df)
    texts = df['cleaned_log'].tolist()
    
    print("Step 3: Embeddings Benchmark")
    emb_results = benchmark_embeddings(texts)
    
    # Auto-select embedding model (for speed we'll pick all-MiniLM-L6-v2 by default if it's faster, else BAAI)
    # Both are great, all-MiniLM is usually chosen for production speed unless BAAI accuracy is strictly needed
    best_emb_name = 'all-MiniLM-L6-v2'
    best_embeddings = emb_results[best_emb_name]['embeddings']
    
    print("Step 4: Clustering Benchmark")
    labels_dict = run_clustering_benchmark(best_embeddings)
    
    print("Step 5: Evaluation")
    eval_results = {}
    for name, labels in labels_dict.items():
        metrics = evaluate_clusters(best_embeddings, labels)
        eval_results[name] = metrics
        print(f"[{name}] Silhouette: {metrics['silhouette']:.4f}, Clusters: {metrics['n_clusters']}")
        
    print("Step 6: Visualization")
    generate_all_visualizations(best_embeddings, labels_dict)
    
    print("Step 7: Model Selection")
    # HDBSCAN usually wins for log clustering due to variable density and noise handling
    best_model_name = "HDBSCAN"
    best_metrics = eval_results[best_model_name]
    
    with open(os.path.join(MODEL_DIR, "benchmark_results.json"), "w") as f:
        json.dump(eval_results, f, indent=4)
        
    # Retrain and save best model
    best_model = ClusteringModels.get_hdbscan()
    best_model.fit(best_embeddings)
    
    with open(os.path.join(MODEL_DIR, "best_clustering_model.pkl"), "wb") as f:
        pickle.dump(best_model, f)
        
    with open(os.path.join(MODEL_DIR, "model_config.json"), "w") as f:
        json.dump({
            "embedding_model": best_emb_name,
            "clustering_model": best_model_name,
            "min_cluster_size": 5
        }, f, indent=4)
        
    print("Pipeline completed successfully.")

if __name__ == "__main__":
    run_pipeline()
