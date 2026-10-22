import numpy as np
import pandas as pd

def generate_risk_dataset(n_samples=5000, seed=42):
    np.random.seed(seed)
    
    # Generate Synthetic Features
    deployment_size = np.random.randint(1, 100, n_samples)
    files_changed = deployment_size * np.random.randint(1, 5, n_samples)
    code_churn = files_changed * np.random.randint(10, 50, n_samples)
    developer_experience = np.random.randint(1, 15, n_samples) # years
    deployment_time = np.random.randint(0, 24, n_samples) # hour of day
    day_of_week = np.random.randint(0, 7, n_samples) # 0 = Monday, 6 = Sunday
    rollback_count = np.random.randint(0, 5, n_samples)
    previous_incident_count = np.random.randint(0, 10, n_samples)
    
    # Telemetry Simulation
    cpu_increase = np.random.uniform(0.0, 1.0, n_samples)
    memory_increase = np.random.uniform(0.0, 1.0, n_samples)
    network_latency = np.random.uniform(10.0, 500.0, n_samples)
    disk_io = np.random.uniform(0.0, 100.0, n_samples)
    
    service_dependency_count = np.random.randint(1, 20, n_samples)
    anomaly_score = np.random.uniform(0.0, 1.0, n_samples)
    root_cause_score = np.random.uniform(0.0, 1.0, n_samples)
    
    # Target Generation logic (Inject realistic causality)
    # High churn, low experience, late night deploy, high anomaly score -> RISKY (1)
    risk_prob = (
        (code_churn / np.max(code_churn)) * 0.2 + 
        ((15 - developer_experience) / 15) * 0.15 + 
        (np.where((deployment_time >= 18) | (deployment_time <= 4), 1.0, 0.0)) * 0.1 + 
        (np.where(day_of_week >= 4, 1.0, 0.0)) * 0.05 + # Friday/Weekend deploys
        anomaly_score * 0.3 + 
        root_cause_score * 0.2
    )
    
    # Add random noise to make it realistic
    risk_prob += np.random.normal(0, 0.1, n_samples)
    
    # Binarize with threshold
    threshold = np.percentile(risk_prob, 80) # 20% of deployments fail
    deployment_result = (risk_prob > threshold).astype(int)
    
    df = pd.DataFrame({
        'deployment_size': deployment_size,
        'files_changed': files_changed,
        'code_churn': code_churn,
        'developer_experience': developer_experience,
        'deployment_time': deployment_time,
        'day_of_week': day_of_week,
        'rollback_count': rollback_count,
        'previous_incident_count': previous_incident_count,
        'cpu_increase': cpu_increase,
        'memory_increase': memory_increase,
        'network_latency': network_latency,
        'disk_io': disk_io,
        'service_dependency_count': service_dependency_count,
        'anomaly_score': anomaly_score,
        'root_cause_score': root_cause_score,
        'deployment_result': deployment_result
    })
    
    return df

if __name__ == "__main__":
    df = generate_risk_dataset()
    print(df.head())
    print("Class distribution:\n", df['deployment_result'].value_counts(normalize=True))
