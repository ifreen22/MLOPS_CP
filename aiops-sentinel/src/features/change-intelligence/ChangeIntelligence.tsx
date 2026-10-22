import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { fetchChangeEvents } from '../../services/api';
import type { ChangeEvent } from '../../services/api';

const EMPTY_CHANGES: ChangeEvent[] = [];

export const ChangeIntelligence: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['changes'],
    queryFn: fetchChangeEvents,
    refetchInterval: 5000,
  });
  const changes = data ?? EMPTY_CHANGES;

  const [inspectedEventId, setInspectedEventId] = useState<string | null>(null);

  const inspectedEvent = useMemo(
    () => changes.find((event) => event.id === inspectedEventId) || changes[0],
    [changes, inspectedEventId]
  );
  const exportChanges = () => {
    const columns = ['timestamp', 'service', 'type', 'versionDelta', 'author'] as const;
    const escape = (value: string) => `"${value.replaceAll('"', '""')}"`;
    const csv = [columns.join(','), ...changes.map((change) => columns.map((column) => escape(change[column])).join(','))].join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'aiops-change-events.csv';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col w-full p-margin gap-space-lg min-h-screen bg-surface-container-lowest text-on-surface font-body-md">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-space-md">
        <div className="flex flex-col min-w-0">
          <div className="flex items-center gap-space-sm">
            <h1 className="font-headline-lg text-on-surface tracking-tight">Change Intelligence</h1>
            <span className="px-space-xs py-0.5 rounded bg-primary/10 text-primary font-label-code-sm uppercase tracking-wider font-semibold">Kubernetes Events</span>
          </div>
          <p className="font-body-md text-on-surface-variant mt-0.5">Recorded Kubernetes events from the configured backend cluster.</p>
        </div>
        <div className="flex items-center gap-space-sm shrink-0">
          <div className="flex items-center gap-1.5 px-space-sm py-1.5 rounded bg-surface-container-high text-on-surface-variant font-label-code-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
            <span>Refresh: <strong className="text-on-surface font-semibold">5s</strong></span>
          </div>
          <button type="button" onClick={exportChanges} disabled={changes.length === 0} className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-surface-container text-on-surface hover:bg-surface-container-high text-label-code-md font-label-code-md transition-colors disabled:opacity-50">
            <span className="material-symbols-outlined text-[16px] text-primary">download</span>
            <span>Export Change Log</span>
          </button>
        </div>
      </div>

      {isError && <p role="alert" className="text-sm text-error">Could not load Kubernetes events from the backend.</p>}

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-space-md items-start">
        <section className="xl:col-span-8 flex flex-col rounded bg-surface-container-low p-space-md shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-sm pb-space-sm">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary text-[20px]">timeline</span>
              <span className="font-headline-sm text-on-surface font-semibold text-[0.9375rem]">Service Change Topology</span>
            </div>
          </div>
          <div className="relative w-full overflow-x-auto select-none pt-2 h-[300px] bg-surface-container-lowest/50 border border-outline-variant/30 flex items-center justify-center">
            {isLoading ? <span className="text-outline font-label-code-md">Loading events...</span> : changes.length === 0 ? (
              <span className="text-outline font-label-code-md">No Kubernetes events have been recorded.</span>
            ) : (
              <ol className="flex items-center gap-3 p-4 min-w-max">
                {changes.map((change) => (
                  <li key={change.id} className="w-56 rounded border border-outline-variant bg-surface-container p-3">
                    <time className="text-xs text-outline">{new Date(change.timestamp).toLocaleString()}</time>
                    <p className="font-semibold mt-1 truncate">{change.service}</p>
                    <p className="text-xs text-primary mt-1 capitalize">{change.type}</p>
                    <p className="text-xs text-on-surface-variant mt-1 line-clamp-2">{change.versionDelta}</p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </section>

        <aside className="xl:col-span-4 flex flex-col rounded bg-surface-container p-space-md shadow-md gap-space-md">
          <div className="flex items-center justify-between pb-space-xs">
            <div className="flex items-center gap-space-xs">
              <span className="material-symbols-outlined text-primary-container text-[20px]">troubleshoot</span>
              <span className="font-headline-sm text-on-surface font-semibold text-[0.9375rem]">Telemetry Inspector</span>
            </div>
          </div>
          
          {isLoading && <div className="text-outline text-center">Loading...</div>}
          {(!isLoading && changes.length === 0) && <div className="text-outline text-center">No event selected.</div>}
          {(!isLoading && !inspectedEvent) && <div className="text-outline text-center">No events found.</div>}
          
          {inspectedEvent && (
            <div className="flex flex-col gap-space-sm bg-surface-container-low p-space-sm rounded">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-xs">
                  <span className="material-symbols-outlined text-primary-container text-[18px]">inventory_2</span>
                  <span className="font-label-code-md text-on-surface font-semibold capitalize">{inspectedEvent.type} Event</span>
                </div>
                <span className="font-label-code-sm text-outline font-medium">id: {inspectedEvent.id.substring(0, 7)}</span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="font-label-code-sm text-outline uppercase tracking-wider text-[0.625rem]">Target Microservice</span>
                <span className="font-metric-display text-primary text-[1.25rem] leading-none">{inspectedEvent.service}</span>
              </div>
              <div className="grid grid-cols-2 gap-space-xs pt-1">
                <div className="flex flex-col bg-surface-container p-space-xs rounded">
                  <span className="font-label-code-sm text-outline text-[0.625rem]">Transition</span>
                  <span className="font-label-code-md text-on-surface font-bold text-[0.75rem]">{inspectedEvent.versionDelta}</span>
                </div>
                <div className="flex flex-col bg-surface-container p-space-xs rounded">
                  <span className="font-label-code-sm text-outline text-[0.625rem]">Triggered By</span>
                  <span className="font-label-code-md text-secondary font-medium text-[0.75rem]">{inspectedEvent.author}</span>
                </div>
              </div>
            </div>
          )}
          
          <Link to="/situations" className="w-full py-2 px-space-md rounded border border-outline-variant text-primary font-label-code-md font-bold text-[0.8125rem] text-center">
            Open Situation Room
          </Link>
        </aside>
      </div>

      <section className="flex flex-col rounded bg-surface-container-low shadow-sm overflow-hidden mt-space-lg">
        <div className="p-space-md flex flex-col md:flex-row md:items-center justify-between gap-space-sm bg-surface-container">
          <div className="flex items-center gap-space-sm">
            <span className="material-symbols-outlined text-secondary text-[20px]">dataset</span>
            <h2 className="font-headline-sm text-on-surface font-semibold text-[0.9375rem]">Recent Cluster Changes</h2>
          </div>
        </div>
        <div className="w-full overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-lowest text-outline font-label-code-sm text-[0.6875rem] tracking-wider uppercase select-none">
                <th className="py-2.5 px-space-md font-medium">Timestamp (UTC)</th>
                <th className="py-2.5 px-space-md font-medium">Service / Target</th>
                <th className="py-2.5 px-space-md font-medium">Change Type</th>
                <th className="py-2.5 px-space-md font-medium">Version / Delta</th>
                <th className="py-2.5 px-space-md font-medium">Author / Origin</th>
              </tr>
            </thead>
            <tbody className="font-label-code-md text-[0.75rem] divide-y divide-outline-variant/10">
              {isLoading && <tr><td colSpan={5} className="py-4 text-center text-outline">Loading...</td></tr>}
              {!isLoading && changes.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-outline">No recorded Kubernetes events.</td></tr>}
              {changes.map(change => (
                <tr key={change.id} onClick={() => setInspectedEventId(change.id)} className="bg-surface-container-low hover:bg-surface-container-high cursor-pointer transition-colors">
                  <td className="py-2.5 px-space-md text-on-surface-variant whitespace-nowrap">{change.timestamp}</td>
                  <td className="py-2.5 px-space-md text-on-surface font-semibold">{change.service}</td>
                  <td className="py-2.5 px-space-md whitespace-nowrap capitalize text-primary">{change.type}</td>
                  <td className="py-2.5 px-space-md text-on-surface">{change.versionDelta}</td>
                  <td className="py-2.5 px-space-md text-on-surface-variant">{change.author}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
};
