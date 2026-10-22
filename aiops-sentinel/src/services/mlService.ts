import { apiClient } from './api';

export interface TelemetryPayload {
  cpu_usage?: number;
  sin_hour?: number;
  cos_hour?: number;
  rolling_mean?: number;
  rolling_std?: number;
  lag_1?: number;
  log_text?: string;
  topology_batch?: number[][];
  deployment_size?: number;
  files_changed?: number;
  code_churn?: number;
  developer_experience?: number;
  deployment_time?: number;
  day_of_week?: number;
  rollback_count?: number;
  previous_incident_count?: number;
  cpu_increase?: number;
  memory_increase?: number;
  network_latency?: number;
  disk_io?: number;
  service_dependency_count?: number;
}

export interface MLAnalysisResult {
  status: string;
  analysis: {
    anomaly_detection?: any;
    alert_clustering?: any;
    root_cause_analysis?: any;
    risk_prediction?: any;
    recommended_actions: string[];
  };
}

export const mlService = {
  getHealth: async () => {
    const { data } = await apiClient.get('/ml/analyze/health');
    return data;
  },

  analyzeTelemetry: async (payload: TelemetryPayload): Promise<MLAnalysisResult> => {
    const { data } = await apiClient.post('/ml/analyze', payload);
    return data;
  }
};
