import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';

export const useSituation = (id: string) => {
  return useQuery({
    queryKey: ['situation', id],
    queryFn: () => api.getSituation(id),
    enabled: !!id,
    refetchInterval: 5000, // auto-refresh every 5s
  });
};

export const useResolveSituation = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, note }: { id: string, note: string }) => api.resolveSituation(id, { resolutionNote: note }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['situation', variables.id] });
    }
  });
};

export const useTopologyGraph = (env: string) => {
  return useQuery({
    queryKey: ['topology', env],
    queryFn: () => api.getTopologyGraph(env),
    enabled: !!env,
    refetchInterval: 5000,
  });
};
