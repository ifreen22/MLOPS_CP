import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { expect, test, vi } from 'vitest';
import { Dashboard } from './Dashboard';

const updateSettings = vi.fn().mockResolvedValue(undefined);

vi.mock('../../hooks/useSystemSettings', () => ({
  useSystemSettings: () => ({
    settings: { isMonitoring: true, autoRecovery: false, pollingInterval: 2 },
    updateSettings,
    error: null,
  }),
}));

vi.mock('../../hooks/useSystemTelemetry', () => ({
  useSystemTelemetry: () => ({
    data: {
      timestamp: '2026-10-22T00:00:00+00:00',
      cpu: { usage_percent: 42.5, logical_cores: 8, physical_cores: 4, current_freq: 3200, max_freq: 4500, load_avg: [0, 0, 0] },
      ram: { total: 16000000000, available: 8000000000, used: 8000000000, percent: 50 },
      disk: { drives: [], total: 500000000000, used: 250000000000, percent: 50 },
      network: { upload_speed: 1048576, download_speed: 2097152, bytes_sent: 1, bytes_recv: 1 },
      battery: null,
      temperature: null,
      processes: [],
      applications: [],
      system: { hostname: 'test-host', os: 'Windows', version: 'test', architecture: 'x64', uptime: 1 },
    },
    history: [],
    recommendations: [],
    isDocker: false,
    error: null,
  }),
}));

vi.mock('../../services/mlService', () => ({
  mlService: {
    getHealth: vi.fn().mockResolvedValue({
      status: 'healthy',
      services: { root_cause_analysis: true, risk_prediction: true, alert_clustering: true },
    }),
  },
}));

vi.mock('../../services/api', () => ({
  apiClient: { post: vi.fn() },
  fetchActionHistory: vi.fn().mockResolvedValue([]),
}));

test('renders live telemetry and persists a Stop Monitoring click', async () => {
  const user = userEvent.setup();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={client}>
      <Dashboard />
    </QueryClientProvider>,
  );

  expect(await screen.findByText('42.5%')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Stop Monitoring' }));

  await waitFor(() => expect(updateSettings).toHaveBeenCalledWith({ isMonitoring: false }));
});
