import { z } from 'zod';
import { apiClient } from './api';

export const KPISchema = z.object({
  activeSituations: z.object({ value: z.number(), change: z.string(), label: z.string() }),
  mttr: z.object({ value: z.string(), change: z.string(), label: z.string(), trend: z.array(z.number()) }),
  alertCompression: z.object({ value: z.string(), ratio: z.string(), target: z.string(), label: z.string() }),
  failureRiskServices: z.object({ 
    value: z.number(), 
    label: z.string(), 
    riskThreshold: z.string(), 
    topService: z.string(), 
    topServiceRisk: z.number(), 
    heatmap: z.array(z.number()) 
  })
});

export const DashboardDataSchema = z.object({
  kpis: KPISchema,
  situations: z.array(z.any()),
  heatmap: z.array(z.any()),
  recentChanges: z.array(z.any())
});

export type DashboardData = z.infer<typeof DashboardDataSchema>;

export const fetchDashboardData = async (): Promise<DashboardData> => {
  const { data } = await apiClient.get('/dashboard');
  return DashboardDataSchema.parse(data);
};
