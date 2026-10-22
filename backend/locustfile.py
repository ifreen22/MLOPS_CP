from locust import HttpUser, task, between
import random

class AIOpsUser(HttpUser):
    wait_time = between(1, 5)

    @task(1)
    def health_check(self):
        self.client.get("/api/v1/health")
        self.client.get("/api/v1/ml/analyze/health")

    @task(3)
    def analyze_telemetry(self):
        payload = {
            "cpu_usage": random.uniform(0.1, 0.99),
            "sin_hour": random.uniform(-1, 1),
            "cos_hour": random.uniform(-1, 1),
            "rolling_mean": random.uniform(0.1, 0.9),
            "rolling_std": random.uniform(0.01, 0.3),
            "lag_1": random.uniform(0.1, 0.9),
            "log_text": "Random simulated log line for load testing",
            "deployment_size": random.uniform(1.0, 100.0),
            "files_changed": random.uniform(1.0, 50.0),
            "code_churn": random.uniform(10.0, 500.0),
            "developer_experience": random.uniform(1.0, 5.0),
            "deployment_time": random.uniform(1.0, 10.0),
            "day_of_week": float(random.randint(0, 6)),
            "rollback_count": float(random.randint(0, 3)),
            "previous_incident_count": float(random.randint(0, 5)),
            "cpu_increase": random.uniform(0.0, 0.8),
            "memory_increase": random.uniform(0.0, 0.8),
            "network_latency": random.uniform(50.0, 500.0),
            "disk_io": random.uniform(10.0, 200.0),
            "service_dependency_count": random.uniform(1.0, 20.0)
        }
        
        # Load test the heavy ML Orchestrator pipeline
        self.client.post("/api/v1/ml/analyze", json=payload, headers={"X-Correlation-ID": "load-test"})
