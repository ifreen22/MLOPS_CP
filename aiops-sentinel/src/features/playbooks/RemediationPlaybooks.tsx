import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import { useSystemSettings } from '../../hooks/useSystemSettings';
import { fetchPlaybooks, executePlaybook } from '../../services/api';
import type { PlaybookRecord } from '../../services/api';
import { cn } from '../../utils/cn';

export const RemediationPlaybooks: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['playbooks'],
    queryFn: fetchPlaybooks,
  });
  const { settings } = useSystemSettings();

  const playbooks: PlaybookRecord[] = data ?? [];
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [filter, setFilter] = useState('');
  const visiblePlaybooks = playbooks.filter((playbook) =>
    `${playbook.name} ${playbook.description ?? ''} ${playbook.failurePattern ?? ''}`.toLowerCase().includes(filter.toLowerCase())
  );

  const toggleRow = (id: string) => {
    setExpandedRows(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const execMutation = useMutation({
    mutationFn: ({ id, dryRun }: { id: string; dryRun: boolean }) => executePlaybook(id, { dryRun }),
    onSuccess: (result) => {
      window.alert(result.message || (result.status === 'queued' ? `Action queued for PID ${result.target}.` : 'Playbook preview completed.'));
    },
    onError: (error: unknown) => {
      const detail = axios.isAxiosError<{ detail?: string }>(error) ? error.response?.data?.detail : undefined;
      window.alert(detail || 'Failed to run playbook.');
    }
  });

  return (
    <div className="flex flex-col w-full min-h-screen bg-surface-container-lowest text-on-surface font-body-md">
      <div className="w-full bg-surface-container-low px-space-lg py-space-md flex flex-col gap-space-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-space-md">
          <div className="flex flex-col gap-1 min-w-0">
            <div className="flex items-center gap-space-sm flex-wrap">
              <h1 className="font-headline-md text-on-surface tracking-tight font-bold">Remediation Playbooks</h1>
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-secondary/10 text-secondary font-label-code-sm text-[0.625rem] font-bold tracking-wider uppercase">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
                Actions require Auto Recovery
              </span>
            </div>
            <p className="font-body-md text-on-surface-variant text-[0.8125rem] max-w-4xl">
              The built-in host-process playbook is executable. Saved playbooks without an execution handler remain preview-unavailable.
            </p>
          </div>
        </div>
      </div>

      <div className="px-space-lg py-2.5 bg-surface-container flex flex-col md:flex-row items-stretch md:items-center justify-between gap-space-sm">
        <div className="flex-1 flex items-center gap-space-sm">
          <div className="relative flex-1 max-w-xl">
            <span className="material-symbols-outlined absolute inset-y-0 left-2.5 flex items-center text-outline text-[16px] pointer-events-none">search</span>
            <input type="text" value={filter} onChange={(event) => setFilter(event.target.value)} className="w-full bg-surface-container-lowest text-on-surface placeholder:text-outline font-label-code-sm text-[0.6875rem] pl-8 pr-8 py-1.5 rounded focus:outline-none" placeholder="Filter playbooks..." />
          </div>
        </div>
      </div>

      <div className="px-space-lg py-space-md flex flex-col gap-space-lg">
        {isError && <p role="alert" className="text-sm text-error">Could not load playbooks. Check the backend connection and retry.</p>}
        <div className="w-full bg-surface-container-low rounded overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-lowest text-outline font-label-code-sm text-[0.6875rem] uppercase tracking-wider">
                  <th className="py-2.5 px-3 w-8"></th>
                  <th className="py-2.5 px-4 font-medium">Playbook Name</th>
                  <th className="py-2.5 px-4 font-medium">Failure Pattern</th>
                  <th className="py-2.5 px-4 font-medium">Action Type</th>
                  <th className="py-2.5 px-4 font-medium">Risk Class</th>
                  <th className="py-2.5 px-4 font-medium">Success Rate</th>
                  <th className="py-2.5 px-4 font-medium">Last Used</th>
                  <th className="py-2.5 px-4 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="font-body-sm text-[0.75rem] divide-y divide-transparent">
                {isLoading && <tr><td colSpan={8} className="py-4 text-center text-outline">Loading...</td></tr>}
                {!isLoading && visiblePlaybooks.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-outline">No remediation playbooks are available.</td>
                  </tr>
                )}
                {visiblePlaybooks.map((pb) => (
                  <React.Fragment key={pb.id}>
                    <tr className="bg-surface-container-low hover:bg-surface-container transition-colors group cursor-pointer" onClick={() => toggleRow(pb.id)}>
                      <td className="py-3 px-3 text-center">
                        <span className={cn("material-symbols-outlined text-outline text-[18px] transition-transform duration-200", expandedRows[pb.id] ? "rotate-90" : "")}>expand_more</span>
                      </td>
                      <td className="py-3 px-4 min-w-[240px]">
                        <div className="flex flex-col">
                          <span className="font-body-md text-on-surface font-semibold text-[0.8125rem] flex items-center gap-1.5">
                            {pb.name}
                            <span className="px-1.5 py-0.2 rounded bg-primary-container/10 text-primary-container font-label-code-sm text-[0.5625rem]">{pb.version || 'saved'}</span>
                          </span>
                          <span className="font-body-sm text-on-surface-variant text-[0.6875rem] line-clamp-1">{pb.description}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="font-label-code-sm text-[0.6875rem] px-2 py-0.5 rounded bg-surface-container text-on-surface font-medium">{pb.failurePattern || 'Not specified'}</span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className="font-label-code-sm text-[0.6875rem] px-2 py-0.5 rounded bg-on-primary-container/40 text-primary font-semibold">{pb.actionType || 'Not executable'}</span>
                      </td>
                      <td className="py-3 px-4 whitespace-nowrap">
                        <span className={cn("font-label-code-sm text-[0.6875rem] px-2 py-0.5 rounded font-bold", pb.riskClass === 'high' ? 'bg-error-container/20 text-error' : pb.riskClass === 'medium' ? 'bg-tertiary-container/15 text-tertiary' : 'bg-secondary/15 text-secondary')}>
                          {pb.riskClass || 'unknown'}
                        </span>
                      </td>
                      <td className="py-3 px-4 min-w-[170px]">
                        {typeof pb.successRate === 'number'
                          ? <span className="text-secondary font-bold">{pb.successRate}% · {pb.runs ?? 0} runs</span>
                          : <span className="text-outline">No execution data</span>}
                      </td>
                      <td className="py-3 px-4 font-label-code-sm text-outline whitespace-nowrap text-[0.6875rem]">{pb.lastUsed || 'Not recorded'}</td>
                      <td className="py-3 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            disabled={pb.id !== 'terminate-high-cpu-process' || execMutation.isPending}
                            title={pb.id !== 'terminate-high-cpu-process' ? 'This saved playbook has no execution handler' : undefined}
                            onClick={() => execMutation.mutate({ id: pb.id, dryRun: true })}
                            className="flex items-center gap-1 px-2 py-1 rounded bg-surface-container hover:bg-surface-container-high text-on-surface font-label-code-sm text-[0.625rem] transition-colors disabled:opacity-50"
                          >
                            <span className="material-symbols-outlined text-[13px] text-tertiary">science</span>
                            <span>Test Dry-Run</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedRows[pb.id] && (
                      <tr className="bg-surface-container-lowest">
                        <td colSpan={8} className="p-0">
                          <div className="px-space-lg py-space-md bg-surface-container-lowest/90 flex flex-col gap-space-md">
                            <div className="flex items-center justify-between">
                              <span className="text-outline font-label-code-sm">ID: {pb.id}</span>
                              <button
                                onClick={() => {
                                  if (!settings.autoRecovery) {
                                    window.alert('Enable Auto Recovery on Mission Control before executing a runbook.');
                                    return;
                                  }
                                  if (window.confirm('Execute this runbook on the selected high-CPU process?')) {
                                    execMutation.mutate({ id: pb.id, dryRun: false });
                                  }
                                }}
                                disabled={!settings.autoRecovery || pb.id !== 'terminate-high-cpu-process' || execMutation.isPending}
                                title={!settings.autoRecovery ? 'Enable Auto Recovery on Mission Control first' : undefined}
                                className="px-2.5 py-1 rounded bg-primary-container text-surface-container-lowest font-body-sm text-[0.6875rem] font-bold hover:bg-surface-tint transition-colors flex items-center gap-1 disabled:opacity-50"
                              >
                                <span className="material-symbols-outlined text-[14px]">play_arrow</span>
                                <span>Execute Runbook</span>
                              </button>
                            </div>
                            <p className="text-on-surface-variant font-label-code-sm">{pb.description}</p>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
