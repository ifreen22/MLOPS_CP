import React, { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Link } from 'react-router-dom';
import { fetchAlerts, fetchClusterHealth, fetchSituations, runAlertClustering } from '../../services/api';
import type { Alert } from '../../services/api';

type ViewMode = 'split' | 'raw' | 'cluster';
const EMPTY_ALERTS: Alert[] = [];

function downloadCsv(alerts: Alert[]) {
  const columns = ['timestamp', 'severity', 'engine', 'service', 'message', 'clusterTarget'] as const;
  const escape = (value: string | null | undefined) => `"${(value ?? '').replaceAll('"', '""')}"`;
  const csv = [
    columns.join(','),
    ...alerts.map((alert) => columns.map((column) => escape(alert[column])).join(',')),
  ].join('\r\n');
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'aiops-alerts.csv';
  link.click();
  URL.revokeObjectURL(url);
}

export const AlertClustering: React.FC = () => {
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [isPaused, setIsPaused] = useState(false);
  const [filter, setFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('all');

  const alertsQuery = useQuery({
    queryKey: ['alerts'],
    queryFn: fetchAlerts,
    refetchInterval: isPaused ? false : 5000,
  });
  const situationsQuery = useQuery({
    queryKey: ['situations'],
    queryFn: fetchSituations,
    refetchInterval: isPaused ? false : 5000,
  });
  const clusterHealthQuery = useQuery({
    queryKey: ['clusterHealth'],
    queryFn: fetchClusterHealth,
    refetchInterval: 30000,
    retry: false,
  });
  const clusterMutation = useMutation({
    mutationFn: runAlertClustering,
    onSuccess: () => {
      window.alert('Alert clustering started. Recorded situations will refresh automatically.');
      window.setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: ['situations'] });
      }, 3000);
    },
    onError: (error: unknown) => {
      const detail = axios.isAxiosError<{ detail?: string }>(error) ? error.response?.data?.detail : undefined;
      window.alert(detail || 'Could not start alert clustering.');
    },
  });

  const alerts = alertsQuery.data ?? EMPTY_ALERTS;
  const situations = situationsQuery.data ?? [];
  const visibleAlerts = useMemo(() => {
    const needle = filter.trim().toLowerCase();
    return alerts.filter((alert) =>
      (severityFilter === 'all' || alert.severity === severityFilter) &&
      (!needle || `${alert.service} ${alert.message} ${alert.engine}`.toLowerCase().includes(needle))
    );
  }, [alerts, filter, severityFilter]);

  const countBySeverity = (severity: string) => alerts.filter((alert) => alert.severity === severity).length;
  const queryError = alertsQuery.isError || situationsQuery.isError;

  return (
    <div className="flex flex-col w-full px-space-lg py-space-md gap-space-md min-h-screen bg-surface-container-lowest text-on-surface font-body-md">
      <header className="flex flex-col xl:flex-row xl:items-center justify-between gap-space-md">
        <div>
          <h1 className="font-headline-md text-on-surface tracking-tight">Alert Intelligence & Clustering</h1>
          <p className="font-body-sm text-outline mt-1">Alerts and situations persisted by the backend. No sample telemetry is shown.</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center p-0.5 rounded bg-surface-container-high border border-outline-variant/60">
            {(['split', 'raw', 'cluster'] as const).map((mode) => (
              <button
                key={mode}
                type="button"
                aria-pressed={viewMode === mode}
                className={`px-3 py-1 rounded font-label-code-sm text-[0.6875rem] transition-colors ${viewMode === mode ? 'bg-surface-container text-primary shadow-sm font-semibold' : 'text-outline hover:text-on-surface'}`}
                onClick={() => setViewMode(mode)}
              >
                {mode === 'split' ? 'Split Mode' : mode === 'raw' ? 'Alerts Only' : 'Situations Only'}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => downloadCsv(visibleAlerts)}
            disabled={visibleAlerts.length === 0}
            className="px-3 py-1.5 rounded border border-outline-variant text-on-surface text-xs disabled:opacity-50"
          >
            Export visible alerts (CSV)
          </button>
        </div>
      </header>

      {queryError && (
        <p role="alert" className="rounded border border-error/40 bg-error-container/30 p-3 text-sm text-error">
          Could not load alerts or situations. Check the backend connection and retry.
        </p>
      )}

      <section className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="rounded bg-surface-container p-3"><span className="text-xs text-outline">Recorded alerts</span><div className="text-xl font-bold">{alerts.length}</div></div>
        <div className="rounded bg-surface-container p-3"><span className="text-xs text-outline">Open situations</span><div className="text-xl font-bold">{situations.filter((item) => item.status === 'OPEN').length}</div></div>
        <div className="rounded bg-surface-container p-3"><span className="text-xs text-outline">Critical</span><div className="text-xl font-bold">{countBySeverity('sev1')}</div></div>
        <div className="rounded bg-surface-container p-3"><span className="text-xs text-outline">High</span><div className="text-xl font-bold">{countBySeverity('sev2')}</div></div>
        <div className="rounded bg-surface-container p-3">
          <span className="text-xs text-outline">Clustering model</span>
          <div className="text-sm font-semibold">{clusterHealthQuery.data?.status ?? (clusterHealthQuery.isError ? 'unavailable' : 'checking')}</div>
        </div>
      </section>

      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 rounded bg-surface-container p-3">
        <div className="flex items-center gap-2">
          <input
            type="search"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            className="bg-surface-container-lowest border border-outline-variant rounded px-3 py-1.5 text-sm"
            placeholder="Filter by service, message, or engine"
          />
          <select
            value={severityFilter}
            onChange={(event) => setSeverityFilter(event.target.value)}
            className="bg-surface-container-lowest border border-outline-variant rounded px-2 py-1.5 text-sm"
            aria-label="Filter by severity"
          >
            <option value="all">All severities</option>
            <option value="sev1">Critical</option>
            <option value="sev2">High</option>
            <option value="sev3">Medium</option>
            <option value="info">Info</option>
          </select>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-outline">Model: {clusterHealthQuery.data?.status ?? 'unavailable'}</span>
          <button
            type="button"
            onClick={() => clusterMutation.mutate()}
            disabled={clusterMutation.isPending || clusterHealthQuery.data?.status !== 'ready'}
            title={clusterHealthQuery.data?.status !== 'ready' ? 'A trained clustering model is required' : undefined}
            className="rounded bg-primary-container px-3 py-1.5 text-xs font-semibold text-on-primary-container disabled:opacity-50"
          >
            {clusterMutation.isPending ? 'Starting...' : 'Cluster open alerts'}
          </button>
          <button type="button" onClick={() => setIsPaused((paused) => !paused)} className="rounded border border-outline-variant px-3 py-1.5 text-xs">
            {isPaused ? 'Resume refresh' : 'Pause refresh'}
          </button>
        </div>
      </div>

      <div className={`grid grid-cols-1 gap-4 ${viewMode === 'split' ? 'xl:grid-cols-2' : ''}`}>
        {(viewMode === 'split' || viewMode === 'raw') && (
          <section className="rounded-xl border border-outline-variant bg-surface-container overflow-hidden">
            <h2 className="p-3 font-semibold border-b border-outline-variant">Recorded alerts ({visibleAlerts.length})</h2>
            {alertsQuery.isLoading ? <p className="p-4 text-sm text-outline">Loading alerts...</p> : visibleAlerts.length === 0 ? (
              <p className="p-4 text-sm text-outline">No matching alerts have been recorded.</p>
            ) : (
              <div className="overflow-auto max-h-[620px]">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-surface-container-low">
                    <tr>{['Time', 'Severity', 'Service', 'Message'].map((header) => <th key={header} className="p-2">{header}</th>)}</tr>
                  </thead>
                  <tbody>
                    {visibleAlerts.map((alert) => (
                      <tr key={alert.id} className="border-t border-outline-variant/40">
                        <td className="p-2 whitespace-nowrap">{new Date(alert.timestamp).toLocaleString()}</td>
                        <td className="p-2">{alert.severity}</td>
                        <td className="p-2">{alert.service}</td>
                        <td className="p-2">{alert.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        {(viewMode === 'split' || viewMode === 'cluster') && (
          <section className="rounded-xl border border-outline-variant bg-surface-container p-3">
            <h2 className="font-semibold mb-3">Recorded situations ({situations.length})</h2>
            {situationsQuery.isLoading ? <p className="text-sm text-outline">Loading situations...</p> : situations.length === 0 ? (
              <div className="py-6 text-center text-sm text-outline">
                No situations recorded. Cluster persisted open alerts when a trained model is available.
              </div>
            ) : (
              <div className="space-y-3">
                {situations.map((situation) => (
                  <article key={situation.id} className="rounded border border-outline-variant/60 bg-surface-container-low p-3">
                    <div className="flex justify-between gap-3">
                      <h3 className="font-semibold">{situation.title}</h3>
                      <span className="text-xs uppercase">{situation.severity} · {situation.status}</span>
                    </div>
                    <p className="text-sm text-on-surface-variant mt-1">{situation.summary || 'No summary recorded.'}</p>
                    <p className="text-xs text-outline mt-2">
                      {situation.clusters?.length ?? 0} cluster(s) · Updated {new Date(situation.updatedAt).toLocaleString()}
                    </p>
                  </article>
                ))}
              </div>
            )}
            <Link to="/situations" className="inline-block mt-3 text-sm text-primary hover:underline">Open Situation Room</Link>
          </section>
        )}
      </div>
    </div>
  );
};
