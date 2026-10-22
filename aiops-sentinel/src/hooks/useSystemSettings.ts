import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/api';

interface SystemSettings {
  isMonitoring: boolean;
  autoRecovery: boolean;
  pollingInterval: number;
}

const DEFAULT_SETTINGS: SystemSettings = {
  isMonitoring: false,
  autoRecovery: false,
  pollingInterval: 2,
};

export function useSystemSettings() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery({
    queryKey: ['systemSettings'],
    queryFn: async () => {
      const response = await apiClient.get<SystemSettings>('/system/settings');
      return response.data;
    },
    refetchInterval: 5000,
  });

  const updateSettings = async (newSettings: Partial<SystemSettings>) => {
    try {
      const response = await apiClient.post<SystemSettings>('/system/settings', newSettings);
      queryClient.setQueryData(['systemSettings'], response.data);
      return response.data;
    } catch (error) {
      console.error('Could not update system settings.', error);
      throw error;
    }
  };

  return {
    settings: settingsQuery.data ?? DEFAULT_SETTINGS,
    updateSettings,
    error: settingsQuery.isError ? 'Could not load system settings from the backend.' : null,
  };
}
