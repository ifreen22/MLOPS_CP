import torch
import numpy as np
import os
from app.ml_services.root_cause.models import GraphSAGE
from app.ml_services.root_cause.graph_builder import SockShopGraphBuilder

class RootCauseAnalysisService:
    def __init__(self):
        self.builder = SockShopGraphBuilder(seed=42)
        self.model = GraphSAGE(num_node_features=5, hidden_dim=16, num_nodes=self.builder.num_nodes)
        self.model_path = os.path.join(os.path.dirname(__file__), "saved_models", "graphsage_model.pt")
        self.is_loaded = False
        self.load_model()
        self.model.eval()

    def load_model(self):
        if os.path.exists(self.model_path):
            state_dict = torch.load(self.model_path, map_location="cpu", weights_only=True)
            self.model.load_state_dict(state_dict)
            self.is_loaded = True
        else:
            self.is_loaded = False
        
    def predict_root_cause(self, telemetry_batch: list[list[float]]):
        """
        Receives a telemetry batch of shape (num_nodes, 5)
        Returns the top predicted root cause node name and confidence.
        """
        if not self.is_loaded:
            raise RuntimeError("GraphSAGE model has not been trained. Run the RCA training pipeline first.")
        if len(telemetry_batch) != self.builder.num_nodes or any(len(node) != 5 for node in telemetry_batch):
            raise ValueError(f"Expected telemetry for {self.builder.num_nodes} nodes with 5 features each.")

        X = torch.FloatTensor(telemetry_batch).unsqueeze(0) # (1, num_nodes, 5)
        
        with torch.no_grad():
            logits = self.model(X, self.builder.A_tensor)
            probs = torch.softmax(logits, dim=1).squeeze(0).numpy()
            
        top_idx = int(np.argmax(probs))
        confidence = float(probs[top_idx])
        
        return {
            "root_cause_service": self.builder.idx_to_node[top_idx],
            "confidence": confidence,
            "all_probabilities": {self.builder.idx_to_node[i]: float(probs[i]) for i in range(self.builder.num_nodes)}
        }
        
    def get_health(self):
        return {
            "status": "ready" if self.is_loaded else "not_trained",
            "model": "GraphSAGE",
            "nodes": self.builder.num_nodes,
        }
