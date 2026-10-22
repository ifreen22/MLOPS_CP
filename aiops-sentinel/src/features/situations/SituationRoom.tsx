import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Clock, ExternalLink, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchSituations, api } from '../../services/api';

interface SituationRecord {
  id: string;
  title: string;
  summary: string | null;
  severity: string;
  status: string;
  affectedServices: string | null;
  createdAt: string;
  updatedAt: string;
  clusters: Array<{ title: string; confidence: number; severity: string }>;
}

export default function SituationRoom() {
  const queryClient = useQueryClient();
  const { data = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['situations'],
    queryFn: fetchSituations,
    refetchInterval: 5000,
  });
  const situations = data as SituationRecord[];
  const resolveMutation = useMutation({
    mutationFn: (id: string) => api.resolveSituation(id, { resolutionNote: 'Acknowledged and resolved from Situation Room.' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['situations'] }),
  });

  const exportReport = () => {
    const report = new Blob([JSON.stringify(situations, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(report);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'aiops-situations.json';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col w-full min-h-full p-6 lg:p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-3">
            Situation Room
            <span className="px-2.5 py-0.5 rounded-full bg-muted text-muted-foreground text-sm font-semibold">
              {situations.filter((situation) => situation.status === 'OPEN').length} open
            </span>
          </h2>
          <p className="text-muted-foreground mt-1">Live incidents and alert clusters recorded by the backend.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => void refetch()} className="px-3 py-2 border border-border rounded-md text-sm flex items-center gap-2">
            <RefreshCw size={16} /> Refresh
          </button>
          <button onClick={exportReport} disabled={situations.length === 0} className="px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm disabled:opacity-50">
            Export Report
          </button>
        </div>
      </div>

      {isLoading && <p role="status" className="text-muted-foreground">Loading recorded situations...</p>}
      {isError && <p role="alert" className="text-destructive">Could not load situations. Check the backend and retry.</p>}
      {!isLoading && !isError && situations.length === 0 && (
        <div className="glass-panel p-8 text-center space-y-3">
          <CheckCircle2 className="mx-auto text-success" size={32} />
          <h3 className="font-semibold text-lg">No recorded situations</h3>
          <p className="text-sm text-muted-foreground">Situations will appear here after alerts are clustered by the backend.</p>
          <Link to="/alert-clustering" className="inline-flex items-center gap-2 text-primary hover:underline">
            Open alert clustering <ExternalLink size={14} />
          </Link>
        </div>
      )}

      <div className="space-y-4">
        {situations.map((situation) => (
          <article key={situation.id} className="glass-panel p-5 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h3 className="font-semibold text-lg flex items-center gap-2">
                  <AlertTriangle size={18} className="text-warning" /> {situation.title}
                </h3>
                <p className="text-sm text-muted-foreground mt-1">{situation.summary || 'No incident summary was recorded.'}</p>
              </div>
              <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold">
                {situation.severity} · {situation.status}
              </span>
            </div>

            <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><Clock size={14} /> Updated {new Date(situation.updatedAt).toLocaleString()}</span>
              {situation.affectedServices && <span>Affected services: {situation.affectedServices}</span>}
              {situation.clusters?.length > 0 && <span>{situation.clusters.length} alert cluster(s)</span>}
            </div>

            <div className="flex flex-wrap gap-2">
              {situation.status === 'OPEN' && (
                <button
                  onClick={() => resolveMutation.mutate(situation.id)}
                  disabled={resolveMutation.isPending}
                  className="px-3 py-2 rounded-md bg-primary text-primary-foreground text-sm disabled:opacity-50"
                >
                  {resolveMutation.isPending ? 'Resolving...' : 'Acknowledge & Resolve'}
                </button>
              )}
              <Link to="/remediation-playbooks" className="px-3 py-2 rounded-md border border-border text-sm hover:bg-accent">
                View Playbooks
              </Link>
            </div>
          </article>
        ))}
      </div>

      {resolveMutation.isError && (
        <p role="alert" className="text-destructive text-sm">Could not resolve the situation. Refresh and try again.</p>
      )}
    </div>
  );
}
