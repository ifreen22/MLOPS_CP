import logging
from typing import Dict, Any, List

# Importing individual services
from app.ml_services.anomaly_detection.service import anomaly_service
from app.ml_services.alert_clustering.service import alert_clustering_service
from app.ml_services.root_cause.service import RootCauseAnalysisService
from app.ml_services.risk_prediction.service import RiskPredictionService

logger = logging.getLogger(__name__)

class AIOrchestratorService:
    def __init__(self):
        # We assume Anomaly and Alert Clustering services are singletons (from their controllers)
        self.anomaly_service = anomaly_service
        self.alert_clustering_service = alert_clustering_service
        
        # Instantiate RCA and Risk services
        try:
            self.rca_service = RootCauseAnalysisService()
        except Exception as e:
            logger.error(f"Failed to load RCA Service: {e}")
            self.rca_service = None
            
        try:
            self.risk_service = RiskPredictionService()
        except Exception as e:
            logger.error(f"Failed to load Risk Prediction Service: {e}")
            self.risk_service = None

    def _ensure_loaded(self):
        if not self.anomaly_service.is_loaded:
            self.anomaly_service.load_model()
        if not self.alert_clustering_service.is_loaded:
            self.alert_clustering_service.load_model()
            
    def get_health(self) -> Dict[str, Any]:
        self._ensure_loaded()
        services = {
            "anomaly_detection": self.anomaly_service.is_loaded,
            "alert_clustering": self.alert_clustering_service.is_loaded,
            "root_cause_analysis": self.rca_service is not None and self.rca_service.is_loaded,
            "risk_prediction": self.risk_service is not None and self.risk_service.model is not None
        }
        return {
            "status": "healthy" if all(services.values()) else "degraded",
            "services": services
        }

    def analyze_telemetry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs the full AI pipeline sequentially:
        1. Anomaly Detection
        2. Alert Clustering
        3. Root Cause Analysis
        4. Risk Prediction
        """
        self._ensure_loaded()
        results = {}

        # ----------------------------------------------------
        # 1. Anomaly Detection (Isolation Forest)
        # ----------------------------------------------------
        anomaly_fields = {
            "value": "cpu_usage",
            "sin_hour": "sin_hour",
            "cos_hour": "cos_hour",
            "rolling_mean_5": "rolling_mean",
            "rolling_std_5": "rolling_std",
            "lag_1": "lag_1",
        }
        missing_anomaly_fields = [
            field for field in anomaly_fields.values() if payload.get(field) is None
        ]
        derived_anomaly_score = None
        if missing_anomaly_fields:
            results["anomaly_detection"] = {
                "status": "unavailable",
                "detail": "Missing telemetry features: "
                + ", ".join(missing_anomaly_fields),
            }
        else:
            try:
                anomaly_features = {
                    model_field: payload[payload_field]
                    for model_field, payload_field in anomaly_fields.items()
                }
                anomaly_result = self.anomaly_service.predict(anomaly_features)
                results["anomaly_detection"] = {"is_anomaly": anomaly_result}
                derived_anomaly_score = 1.0 if anomaly_result else 0.1
            except Exception as e:
                logger.error(f"Anomaly Detection failed: {e}")
                results["anomaly_detection"] = {
                    "status": "unavailable",
                    "detail": str(e),
                }

        # ----------------------------------------------------
        # 2. Alert Clustering (HDBSCAN)
        # ----------------------------------------------------
        try:
            log_text = payload.get("log_text")
            if isinstance(log_text, str) and log_text.strip():
                results["alert_clustering"] = self.alert_clustering_service.predict(
                    log_text
                )
            else:
                results["alert_clustering"] = {
                    "status": "unavailable",
                    "detail": "Alert clustering requires real log or alert text.",
                }
        except Exception as e:
            logger.error(f"Alert Clustering failed: {e}")
            results["alert_clustering"] = {
                "status": "unavailable",
                "detail": str(e),
            }

        # ----------------------------------------------------
        # 3. Root Cause Analysis (GraphSAGE)
        # ----------------------------------------------------
        derived_rca_score = None
        try:
            if self.rca_service:
                # payload should provide a topology_batch (7 nodes x 5 features) 
                topology = payload.get("topology_batch")
                if topology is None:
                    results["root_cause_analysis"] = {
                        "status": "unavailable",
                        "detail": "Root-cause analysis requires topology telemetry.",
                    }
                else:
                    rca_result = self.rca_service.predict_root_cause(topology)
                    results["root_cause_analysis"] = rca_result
                    derived_rca_score = rca_result.get("confidence", 0.0)
            else:
                results["root_cause_analysis"] = {
                    "status": "unavailable",
                    "detail": "RCA service is not initialized.",
                }
        except Exception as e:
            logger.error(f"Root Cause Analysis failed: {e}")
            results["root_cause_analysis"] = {
                "status": "unavailable",
                "detail": str(e),
            }

        # ----------------------------------------------------
        # 4. Risk Prediction (LightGBM)
        # ----------------------------------------------------
        try:
            deployment_size = payload.get("deployment_size")
            required_risk_fields = (
                "deployment_size",
                "files_changed",
                "code_churn",
                "developer_experience",
                "deployment_time",
                "day_of_week",
                "rollback_count",
                "previous_incident_count",
                "cpu_increase",
                "memory_increase",
                "network_latency",
                "disk_io",
                "service_dependency_count",
            )
            missing_risk_fields = [
                field
                for field in required_risk_fields
                if payload.get(field) is None
            ]
            if derived_anomaly_score is None:
                missing_risk_fields.append("anomaly_score")
            if derived_rca_score is None:
                missing_risk_fields.append("root_cause_score")
            has_deployment_context = (
                deployment_size is not None and float(deployment_size) > 0
            )
            if has_deployment_context and not missing_risk_fields and self.risk_service and self.risk_service.model:
                risk_features = {
                    field: payload[field] for field in required_risk_fields
                }
                risk_features.update({
                    # Chained features
                    "anomaly_score": derived_anomaly_score,
                    "root_cause_score": derived_rca_score
                })
                risk_result = self.risk_service.predict(risk_features)
                results["risk_prediction"] = risk_result
            elif not has_deployment_context:
                results["risk_prediction"] = {
                    "status": "unavailable",
                    "detail": "Deployment risk scoring requires deployment context.",
                }
            elif missing_risk_fields:
                results["risk_prediction"] = {
                    "status": "unavailable",
                    "detail": "Missing deployment fields: "
                    + ", ".join(missing_risk_fields),
                }
            elif self.risk_service is None or self.risk_service.model is None:
                results["risk_prediction"] = {
                    "status": "unavailable",
                    "detail": "Risk prediction model is not loaded.",
                }
        except Exception as e:
            logger.error(f"Risk Prediction failed: {e}")
            results["risk_prediction"] = {
                "status": "unavailable",
                "detail": str(e),
            }

        # ----------------------------------------------------
        # 5. Synthesis / Recommended Actions
        # ----------------------------------------------------
        actions = []
        if results.get("anomaly_detection", {}).get("is_anomaly"):
            actions.append("Investigate active telemetry anomaly.")
            
        risk = results.get("risk_prediction", {})
        if "recommended_action" in risk and risk["recommended_action"] != "Proceed":
            actions.append(f"Deployment blocked: {risk['recommended_action']}")
            
        if results.get("root_cause_analysis", {}).get("root_cause_service"):
            actions.append(f"Isolate {results['root_cause_analysis']['root_cause_service']} service.")

        if not actions:
            actions.append(
                "No rule-based action was triggered by the available telemetry."
            )

        results["recommended_actions"] = actions
        return results

orchestrator_service = AIOrchestratorService()
