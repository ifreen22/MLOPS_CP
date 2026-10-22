import { useState, useEffect } from 'react';
import { apiClient } from '../services/api';

export interface TelemetryData {
  cpu: {
    usage_percent: number;
    logical_cores: number;
    physical_cores: number;
    current_freq: number;
    max_freq: number;
    load_avg: number[];
  };
  ram: {
    total: number;
    available: number;
    used: number;
    percent: number;
  };
  disk: {
    drives: any[];
    total: number;
    used: number;
    percent: number;
  };
  network: {
    upload_speed: number;
    download_speed: number;
    bytes_sent: number;
    bytes_recv: number;
  };
  battery: number | null;
  temperature: number | null;
  processes: any[];
  applications: string[];
  system: {
    hostname: string;
    os: string;
    version: string;
    architecture: string;
    uptime: number;
  };
  timestamp: string;
}

export function useSystemTelemetry(intervalMs = 5000) {
  const [data, setData] = useState<TelemetryData | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [isDocker, setIsDocker] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchTelemetry = async () => {
      try {
        const response = await apiClient.get('/system/live');
        const payload = response.data;
        
        if (mounted && payload.is_docker !== undefined) {
            setIsDocker(payload.is_docker);
        }

        const telemetry = payload.data;
        
        if (!telemetry) {
             setError(null);
             setRecommendations([]);
             return;
        }
        if (mounted) setError(null);

        // Also fetch ML analysis
        try {
            const mlResponse = await apiClient.post('/ml/analyze');
            if (mounted) {
                const actions = mlResponse.data?.analysis?.recommended_actions;
                setRecommendations(Array.isArray(actions) ? actions : []);
                if (mlResponse.data?.status === 'unavailable') {
                    setError(mlResponse.data.detail || 'Host telemetry is not available for analysis.');
                }
            }
        } catch (e) {
            console.error('Failed ML analyze:', e);
            if (mounted) setError('Telemetry is available, but ML analysis failed.');
        }

        if (mounted && telemetry) {
            setData(telemetry);
            setHistory(prev => {
                const now = new Date();
                const newPoint = {
                    time: `${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`,
                    cpu: telemetry.cpu?.usage_percent || 0,
                    memory: telemetry.ram?.percent || 0,
                    upload: (telemetry.network?.upload_speed || 0) / 1024 / 1024,
                    download: (telemetry.network?.download_speed || 0) / 1024 / 1024,
                };
                const newHistory = [...prev, newPoint];
                if (newHistory.length > 20) newHistory.shift();
                return newHistory;
            });
        }
      } catch (err) {
        console.error('Failed to fetch telemetry:', err);
        if (mounted) setError('Could not retrieve host telemetry from the backend.');
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, intervalMs);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [intervalMs]);

  return { data, history, recommendations, isDocker, error };
}
