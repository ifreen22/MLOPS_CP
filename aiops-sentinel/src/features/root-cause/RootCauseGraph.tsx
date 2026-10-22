import { useMemo } from 'react';
import { ReactFlow, Controls, Background, MiniMap } from '@xyflow/react';
import type { Edge, Node } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { api } from '../../services/api';
import { AlertCircle, CheckCircle2, RefreshCw, Server } from 'lucide-react';

interface TopologyItem {
  id: string;
  name: string;
  status?: string;
  pods?: Array<{ id: string; name: string; status: string }>;
}

function TopologyNode({ data }: { data: { label: string; status?: string; kind: string } }) {
  const healthy = data.status?.toLowerCase() === 'running' || data.status?.toLowerCase() === 'ready';
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3 shadow-lg">
      <div className="flex items-center gap-2">
        {healthy ? <CheckCircle2 className="text-success" size={16} /> : <AlertCircle className="text-muted-foreground" size={16} />}
        <Server className="text-primary" size={18} />
        <span className="font-semibold text-sm">{data.label}</span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{data.kind}{data.status ? ` · ${data.status}` : ''}</p>
    </div>
  );
}

const nodeTypes = { topology: TopologyNode };

export default function RootCauseGraph() {
  const queryClient = useQueryClient();
  const topologyQuery = useQuery({
    queryKey: ['topology'],
    queryFn: () => api.getTopologyGraph(),
    refetchInterval: 10000,
  });
  const healthQuery = useQuery({
    queryKey: ['rootCauseHealth'],
    queryFn: api.getRootCauseHealth,
    refetchInterval: (query) => query.state.data?.training ? 3000 : 15000,
  });
  const trainMutation = useMutation({
    mutationFn: api.trainRootCause,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rootCauseHealth'] }),
  });

  const graph = useMemo(() => {
    const services = (topologyQuery.data?.services || []) as TopologyItem[];
    const backendNodes = (topologyQuery.data?.nodes || []) as TopologyItem[];
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    services.forEach((service, index) => {
      nodes.push({
        id: `service-${service.id}`,
        type: 'topology',
        position: { x: index * 250, y: 30 },
        data: { label: service.name, kind: 'Service', status: service.status },
      });
      (service.pods || []).forEach((pod, podIndex) => {
        const podId = `pod-${pod.id}`;
        nodes.push({
          id: podId,
          type: 'topology',
          position: { x: index * 250 + podIndex * 30, y: 190 + podIndex * 120 },
          data: { label: pod.name, kind: 'Pod', status: pod.status },
        });
        edges.push({ id: `service-pod-${service.id}-${pod.id}`, source: `service-${service.id}`, target: podId });
      });
    });

    backendNodes.forEach((node, index) => {
      nodes.push({
        id: `node-${node.id}`,
        type: 'topology',
        position: { x: index * 250, y: 410 },
        data: { label: node.name, kind: 'Node', status: node.status },
      });
    });
    return { nodes, edges };
  }, [topologyQuery.data]);

  const rootCauseHealth = healthQuery.data as {
    status?: string;
    training?: boolean;
    training_error?: string | null;
    training_available?: boolean;
    training_blocked_reason?: string | null;
  } | undefined;
  const isTraining = Boolean(rootCauseHealth?.training || trainMutation.isPending);
  const trainingError = axios.isAxiosError<{ detail?: string }>(trainMutation.error)
    ? trainMutation.error.response?.data?.detail
    : undefined;

  return (
    <div className="flex flex-col w-full h-full min-h-[70vh] p-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Root Cause Topology</h2>
          <p className="text-muted-foreground mt-1 text-sm">
            Discovered services, pods, and nodes. The trainer uses synthetic Sock Shop fault data; predictions require compatible live topology telemetry.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            RCA model: {rootCauseHealth?.status === 'ready' ? 'trained' : rootCauseHealth?.training ? 'training' : 'not trained'}
          </span>
          {rootCauseHealth?.status !== 'ready' && (
            <button
              onClick={() => trainMutation.mutate()}
              disabled={isTraining || rootCauseHealth?.training_available !== true}
              className="rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground disabled:opacity-50"
            >
              {isTraining ? 'Training benchmarks...' : rootCauseHealth?.training_available ? 'Train RCA model' : 'Training unavailable'}
            </button>
          )}
          <button onClick={() => void topologyQuery.refetch()} className="rounded-md border border-border p-2" aria-label="Refresh topology">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {topologyQuery.isError && <p role="alert" className="text-destructive mb-3">Could not load topology data.</p>}
      {healthQuery.isError && <p role="alert" className="text-destructive mb-3">Could not load RCA model status.</p>}
      {trainMutation.isError && <p role="alert" className="text-destructive mb-3">{trainingError || 'Could not start RCA training.'}</p>}
      {rootCauseHealth?.training_error && <p role="alert" className="text-destructive mb-3">RCA training failed: {rootCauseHealth.training_error}</p>}
      {rootCauseHealth?.training_blocked_reason && (
        <p className="text-sm text-muted-foreground">{rootCauseHealth.training_blocked_reason}</p>
      )}

      {graph.nodes.length === 0 ? (
        <div className="glass-panel flex flex-1 items-center justify-center p-8 text-center text-muted-foreground">
          No cluster topology has been ingested yet. Add cluster, service, node, and pod data to visualize real dependencies.
        </div>
      ) : (
        <div className="flex-1 glass-panel overflow-hidden border border-border/50 relative">
          <ReactFlow nodes={graph.nodes} edges={graph.edges} nodeTypes={nodeTypes} fitView>
            <Background color="hsl(var(--muted-foreground))" gap={16} size={1} />
            <Controls className="bg-card border-border fill-foreground" />
            <MiniMap className="bg-card border border-border rounded-lg overflow-hidden" />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}
