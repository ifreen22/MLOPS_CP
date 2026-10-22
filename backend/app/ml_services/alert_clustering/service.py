import os
import json
import pickle
from app.ml_services.alert_clustering.config import MODEL_DIR
from app.ml_services.alert_clustering.embeddings import EmbeddingGenerator

class AlertClusteringService:
    def __init__(self):
        self.clustering_model = None
        self.embedding_generator = None
        self.config = {}
        self.is_loaded = False
        self.load_model()

    def load_model(self):
        config_path = os.path.join(MODEL_DIR, "model_config.json")
        model_path = os.path.join(MODEL_DIR, "best_clustering_model.pkl")
        legacy_model_path = os.path.join(MODEL_DIR, "alert_clustering_pipeline.pkl")

        if not os.path.exists(model_path) and os.path.exists(legacy_model_path):
            model_path = legacy_model_path
        if not os.path.exists(model_path):
            return # Not trained yet

        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = {
                "embedding_model": "all-MiniLM-L6-v2",
                "clustering_model": "HDBSCAN",
                "min_cluster_size": 5,
            }
            
        with open(model_path, "rb") as f:
            self.clustering_model = pickle.load(f)
            
        self.embedding_generator = EmbeddingGenerator(self.config.get("embedding_model", "all-MiniLM-L6-v2"))
        self.is_loaded = True

    def train(self):
        # Calls the orchestrator
        from app.ml_services.alert_clustering.trainer import run_pipeline
        run_pipeline()
        self.load_model()

    def _get_embeddings(self, texts: list):
        # In a real pipeline, preprocessing runs here too
        from app.ml_services.alert_clustering.preprocessing import clean_log
        cleaned = [clean_log(t) for t in texts]
        return self.embedding_generator.generate(cleaned)

    def predict(self, log_text: str):
        if not self.is_loaded:
            raise ValueError("Model is not loaded.")
            
        # hdbscan.approximate_predict allows online prediction if trained with prediction_data=True
        # For simplicity, if approximate_predict isn't available, we fallback or retrain.
        # However, HDBSCAN supports approximate_predict!
        import hdbscan
        emb = self._get_embeddings([log_text])
        labels, probabilities = hdbscan.approximate_predict(self.clustering_model, emb)
        return {"cluster_id": int(labels[0]), "confidence": float(probabilities[0])}

    def batch_predict(self, log_texts: list):
        if not self.is_loaded:
            raise ValueError("Model is not loaded.")
            
        import hdbscan
        emb = self._get_embeddings(log_texts)
        labels, probabilities = hdbscan.approximate_predict(self.clustering_model, emb)
        
        results = []
        for l, p in zip(labels, probabilities):
            results.append({"cluster_id": int(l), "confidence": float(p)})
        return results

    def health(self):
        return {
            "status": "ready" if self.is_loaded else "not_trained",
            "model_config": self.config
        }

alert_clustering_service = AlertClusteringService()
