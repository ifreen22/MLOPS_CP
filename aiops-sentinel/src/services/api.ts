import { z } from 'zod';
import axios from 'axios';

export const API_BASE_URL = '/api/v1';
export const AUTH_TOKEN_KEY = 'aiops-access-token';

// Setup global axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(AUTH_TOKEN_KEY);
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      sessionStorage.removeItem(AUTH_TOKEN_KEY);
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    return Promise.reject(error);
  },
);

export const AlertSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  severity: z.enum(['sev1', 'sev2', 'sev3', 'info']),
  engine: z.string(),
  service: z.string(),
  message: z.string(),
  clusterTarget: z.string().nullable().optional(),
});

export const ChangeEventSchema = z.object({
  id: z.string(),
  timestamp: z.string(),
  service: z.string(),
  type: z.enum(['deployment', 'config', 'infra']),
  versionDelta: z.string(),
  author: z.string(),
  correlatedIncidentId: z.string().optional(),
});

export type Alert = z.infer<typeof AlertSchema>;
export type ChangeEvent = z.infer<typeof ChangeEventSchema>;

export interface ManagedUser {
  id: string;
  organizationId: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  role: 'ADMIN' | 'OPERATOR' | 'VIEWER';
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface UpdateUserRequest {
  email?: string;
  firstName?: string | null;
  lastName?: string | null;
  role?: ManagedUser['role'];
  password?: string;
}

export interface AuditLogRecord {
  id: string;
  action: string;
  resource: string;
  resourceId: string | null;
  details: string | null;
  createdAt: string;
  userId: string;
  userEmail: string | null;
}

export interface CreateUserRequest {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
  role: ManagedUser['role'];
}

export const login = async (email: string, password: string) => {
  const form = new URLSearchParams({ username: email, password });
  const { data } = await apiClient.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  sessionStorage.setItem(AUTH_TOKEN_KEY, data.access_token);
  return data as { access_token: string; token_type: 'bearer'; expires_in: number; user: ManagedUser };
};

export const logout = async (): Promise<void> => {
  try {
    await apiClient.post('/auth/logout');
  } finally {
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
  }
};

export const getAuthStatus = async (): Promise<{ configured: boolean }> => {
  const { data } = await apiClient.get('/auth/status');
  return data;
};

export const getCurrentUser = async (): Promise<ManagedUser> => {
  const { data } = await apiClient.get('/auth/me');
  return data;
};

export const fetchUsers = async (): Promise<ManagedUser[]> => {
  const { data } = await apiClient.get('/users');
  return data;
};

export const createUser = async (payload: CreateUserRequest): Promise<ManagedUser> => {
  const { data } = await apiClient.post('/users', payload);
  return data;
};

export const updateUser = async (id: string, payload: UpdateUserRequest): Promise<ManagedUser> => {
  const { data } = await apiClient.patch(`/users/${id}`, payload);
  return data;
};

export const setUserActive = async (id: string, isActive: boolean): Promise<ManagedUser> => {
  const { data } = await apiClient.patch(`/users/${id}/status`, { isActive });
  return data;
};

export const deleteUser = async (id: string): Promise<void> => {
  await apiClient.delete(`/users/${id}`);
};

export const fetchAuditLogs = async (limit = 100): Promise<AuditLogRecord[]> => {
  const { data } = await apiClient.get('/users/audit-logs', { params: { limit } });
  return data;
};

export interface SituationRecord {
  id: string;
  title: string;
  summary: string | null;
  severity: string;
  status: string;
  affectedServices: string | null;
  createdAt: string;
  updatedAt: string;
  clusters: Array<{ id: string; title: string; confidence: number; severity: string }>;
}

export interface PlaybookRecord {
  id: string;
  name: string;
  description?: string | null;
  failurePattern?: string;
  actionType?: string;
  riskClass?: string;
  successRate?: number | null;
  runs?: number;
  lastUsed?: string;
  version?: string;
}

export interface PlaybookExecutionResult {
  status: 'dry_run' | 'queued';
  actionType?: string;
  target?: number;
  process?: string;
  actionId?: string;
  message: string;
}

export interface ActionHistoryRecord {
  id: string;
  actionType: string;
  target: string | null;
  status: 'PENDING' | 'SUCCESS' | 'FAILED';
  createdAt: string;
  completedAt: string | null;
  processName: string | null;
  requestedByEmail: string | null;
  result: string | null;
}

export type SloMetric = 'cpu_usage' | 'memory_usage' | 'disk_usage';

export interface ServiceLevelObjective {
  id: string;
  name: string;
  description: string | null;
  metric: SloMetric;
  threshold: number;
  targetPercent: number;
  windowHours: number;
  sampleCount: number;
  compliancePercent: number | null;
  errorBudgetRemainingPercent: number | null;
  status: 'no_data' | 'met' | 'breached';
}

export interface CreateSloRequest {
  name: string;
  description?: string;
  metric: SloMetric;
  threshold: number;
  targetPercent: number;
  windowHours: number;
}

export const fetchAlerts = async (): Promise<Alert[]> => {
  const { data } = await apiClient.get('/alerts');
  return data;
};

export const fetchSituations = async (): Promise<SituationRecord[]> => {
  const { data } = await apiClient.get('/situations');
  return data;
};

export const fetchChangeEvents = async (): Promise<ChangeEvent[]> => {
  const { data } = await apiClient.get('/changes');
  return data;
};

export const fetchPlaybooks = async (): Promise<PlaybookRecord[]> => {
  const { data } = await apiClient.get('/playbooks');
  return data;
};

export const fetchSlos = async (): Promise<ServiceLevelObjective[]> => {
  const { data } = await apiClient.get('/slos');
  return data;
};

export const createSlo = async (payload: CreateSloRequest) => {
  const { data } = await apiClient.post('/slos', payload);
  return data;
};

export const deleteSlo = async (id: string) => {
  await apiClient.delete(`/slos/${id}`);
};

export const executePlaybook = async (id: string, params: { dryRun: boolean; pid?: number }): Promise<PlaybookExecutionResult> => {
  const { data } = await apiClient.post(`/playbooks/${id}/execute`, params);
  return data;
};

export const fetchActionHistory = async (): Promise<ActionHistoryRecord[]> => {
  const { data } = await apiClient.get('/system/actions/history');
  return data;
};

export const api = {
  getSituation: async (id: string): Promise<SituationRecord> => {
    const { data } = await apiClient.get(`/situations/${id}`);
    return data;
  },
  resolveSituation: async (id: string, data: { resolutionNote: string }) => {
    const response = await apiClient.post(`/situations/${id}/resolve`, data);
    return response.data;
  },
  getTopologyGraph: async (clusterId?: string) => {
    const { data } = await apiClient.get('/topology', { params: clusterId ? { clusterId } : undefined });
    return data;
  },
  getRootCauseHealth: async () => {
    const { data } = await apiClient.get('/ml/root-cause/health');
    return data;
  },
  trainRootCause: async () => {
    const { data } = await apiClient.post('/ml/root-cause/train');
    return data;
  },
};

export const fetchClusterHealth = async (): Promise<{ status: string }> => {
  const { data } = await apiClient.get('/ml/cluster/health');
  return data;
};

export const runAlertClustering = async (): Promise<{ status: string; message: string }> => {
  const { data } = await apiClient.post('/ml/cluster/run');
  return data;
};

export interface PolicyRecord {
  id: string;
  name: string;
  description: string | null;
  rules: string;
  isEnabled: boolean;
  createdAt: string;
  updatedAt: string;
}

export const fetchPolicies = async (): Promise<PolicyRecord[]> => {
  const { data } = await apiClient.get('/policies');
  return data;
};

export const updatePolicy = async (id: string, payload: Partial<PolicyRecord>): Promise<PolicyRecord> => {
  const { data } = await apiClient.put(`/policies/${id}`, payload);
  return data;
};

export const createPolicy = async (payload: { name: string; description?: string; rules: string; isEnabled?: boolean }): Promise<PolicyRecord> => {
  const { data } = await apiClient.post('/policies', payload);
  return data;
};

export const deletePolicy = async (id: string): Promise<{ status: string; id: string }> => {
  const { data } = await apiClient.delete(`/policies/${id}`);
  return data;
};

export const validatePolicy = async (rules: string, inputData?: Record<string, unknown>) => {
  const { data } = await apiClient.post('/policies/validate', { rules, input_data: inputData });
  return data;
};

export interface ServiceRecord {
  id: string;
  name: string;
  description: string | null;
  clusterId: string;
  createdAt?: string;
}

export const fetchServices = async (): Promise<ServiceRecord[]> => {
  const { data } = await apiClient.get('/services');
  return data;
};

export const updateServiceTier = async (id: string, tier: string): Promise<ServiceRecord> => {
  const { data } = await apiClient.patch(`/services/${id}/tier`, { tier });
  return data;
};

export interface NotificationSettingsRecord {
  webhookUrl: string;
  slackChannel: string;
  pagerDutyRoutingKey: string;
  minSeverity: string;
  enabledEvents: string[];
  updatedAt?: string;
}

export const fetchNotificationSettings = async (): Promise<NotificationSettingsRecord> => {
  const { data } = await apiClient.get('/notifications/settings');
  return data;
};

export const updateNotificationSettings = async (payload: Partial<NotificationSettingsRecord>): Promise<{ status: string; settings: NotificationSettingsRecord }> => {
  const { data } = await apiClient.post('/notifications/settings', payload);
  return data;
};

export const sendTestNotification = async (channel = 'webhook', message?: string) => {
  const { data } = await apiClient.post('/notifications/test', { channel, message });
  return data;
};

