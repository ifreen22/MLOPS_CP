import os
import pickle
import numpy as np
import pandas as pd

class RiskPredictionService:
    def __init__(self):
        self.model_path = os.path.join(os.path.dirname(__file__), "saved_models", "risk_model.pkl")
        self.model = None
        self.scaler = None
        self.features = None
        
        if os.path.exists(self.model_path):
            with open(self.model_path, "rb") as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.features = data['features']
                
    def get_health(self):
        if self.model is None:
            return {"status": "unhealthy", "reason": "Model not loaded"}
        return {"status": "healthy", "model": type(self.model).__name__}
        
    def predict(self, payload: dict):
        if self.model is None:
            raise ValueError("Model is not loaded.")
            
        # Ensure correct order
        input_data = []
        for f in self.features:
            input_data.append(payload.get(f, 0.0))
            
        X = np.array(input_data).reshape(1, -1)
        X_scaled = self.scaler.transform(X)
        
        prob = self.model.predict_proba(X_scaled)[0, 1]
        
        # Explain top risk factors (using coefficients or feature importances naively)
        # For a true production system, SHAP would be executed here per-sample.
        # We will approximate by sorting feature values multiplied by global importance.
        risk_factors = []
        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
            # Weight the input by the global importance to see what's driving it
            weighted_inputs = X_scaled[0] * importances
            top_idx = np.argsort(weighted_inputs)[::-1][:3]
            for i in top_idx:
                risk_factors.append({
                    "feature": self.features[i],
                    "contribution": float(weighted_inputs[i])
                })
        
        action = "Proceed" if prob < 0.5 else "Halt & Review"
        if prob > 0.8:
            action = "Automatic Rollback Recommended"
            
        return {
            "risk_score": float(prob),
            "confidence": float(abs(prob - 0.5) * 2), # 0 to 1 confidence
            "top_risk_factors": risk_factors,
            "recommended_action": action
        }
