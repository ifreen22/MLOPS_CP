import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
  createSlo,
  deleteSlo,
  fetchSlos,
  type CreateSloRequest,
  type SloMetric,
} from '../../services/api';

const metricLabels: Record<SloMetric, string> = {
  cpu_usage: 'CPU usage',
  memory_usage: 'Memory usage',
  disk_usage: 'Disk usage',
};
const sloMetrics: SloMetric[] = ['cpu_usage', 'memory_usage', 'disk_usage'];

const initialForm: CreateSloRequest = {
  name: '',
  description: '',
  metric: 'cpu_usage',
  threshold: 80,
  targetPercent: 99,
  windowHours: 24,
};

export const SloDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initialForm);
  const slosQuery = useQuery({
    queryKey: ['slos'],
    queryFn: fetchSlos,
    refetchInterval: 5000,
  });
  const createMutation = useMutation({
    mutationFn: createSlo,
    onSuccess: async () => {
      setForm(initialForm);
      await queryClient.invalidateQueries({ queryKey: ['slos'] });
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteSlo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['slos'] }),
  });

  const mutationError = createMutation.error || deleteMutation.error;
  const errorDetail = axios.isAxiosError<{ detail?: string }>(mutationError)
    ? mutationError.response?.data?.detail
    : undefined;

  const submit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate({
      ...form,
      name: form.name.trim(),
      description: form.description?.trim() || undefined,
    });
  };

  return (
    <div className="flex flex-col w-full px-space-lg py-space-md gap-space-lg min-h-screen bg-surface-container-lowest text-on-surface font-body-md">
      <header>
        <h1 className="font-headline-lg text-on-surface">Service Level Objectives (SLOs)</h1>
        <p className="font-body-md text-on-surface-variant mt-1">
          Objectives are evaluated from persisted host telemetry; no synthetic SLI values are used.
        </p>
      </header>

      <section className="rounded border border-outline-variant bg-surface-container-low p-space-lg">
        <h2 className="font-semibold">Create a host resource objective</h2>
        <form onSubmit={submit} className="mt-4 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
          <label className="flex flex-col gap-1 text-sm">
            Name
            <input
              required
              maxLength={100}
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              className="rounded border border-outline-variant bg-surface-container-lowest px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Metric
            <select
              value={form.metric}
              onChange={(event) => {
                const metric = sloMetrics.find((value) => value === event.target.value);
                if (metric) setForm({ ...form, metric });
              }}
              className="rounded border border-outline-variant bg-surface-container-lowest px-3 py-2"
            >
              {sloMetrics.map((value) => (
                <option key={value} value={value}>{metricLabels[value]}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Maximum threshold (%)
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              required
              value={form.threshold}
              onChange={(event) => setForm({ ...form, threshold: Number(event.target.value) })}
              className="rounded border border-outline-variant bg-surface-container-lowest px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Target compliance (%)
            <input
              type="number"
              min="0.1"
              max="100"
              step="0.1"
              required
              value={form.targetPercent}
              onChange={(event) => setForm({ ...form, targetPercent: Number(event.target.value) })}
              className="rounded border border-outline-variant bg-surface-container-lowest px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Evaluation window (hours)
            <input
              type="number"
              min="1"
              max="720"
              step="1"
              required
              value={form.windowHours}
              onChange={(event) => setForm({ ...form, windowHours: Number(event.target.value) })}
              className="rounded border border-outline-variant bg-surface-container-lowest px-3 py-2"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm md:col-span-2 xl:col-span-4">
            Description (optional)
            <input
              maxLength={500}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              className="rounded border border-outline-variant bg-surface-container-lowest px-3 py-2"
            />
          </label>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={createMutation.isPending || !form.name.trim()}
              className="w-full rounded bg-primary-container px-3 py-2 text-sm font-semibold text-on-primary-container disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating…' : 'Create SLO'}
            </button>
          </div>
        </form>
      </section>

      {(slosQuery.isError || mutationError) && (
        <p role="alert" className="rounded border border-error/40 bg-error-container/30 p-3 text-sm text-error">
          {errorDetail || 'Could not complete the SLO request. Check the backend and try again.'}
        </p>
      )}

      <section className="space-y-3">
        <h2 className="font-semibold">Configured objectives</h2>
        {slosQuery.isLoading && <p role="status" className="text-sm text-on-surface-variant">Loading SLOs…</p>}
        {!slosQuery.isLoading && !slosQuery.isError && (slosQuery.data?.length ?? 0) === 0 && (
          <p className="rounded border border-outline-variant bg-surface-container-low p-5 text-sm text-on-surface-variant">
            No SLOs are configured. Create an objective above to evaluate real host telemetry.
          </p>
        )}
        {slosQuery.data?.map((slo) => (
          <article key={slo.id} className="rounded border border-outline-variant bg-surface-container-low p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold">{slo.name}</h3>
                {slo.description && <p className="text-sm text-on-surface-variant mt-1">{slo.description}</p>}
              </div>
              <span className={`rounded px-2 py-1 text-xs font-semibold ${
                slo.status === 'met' ? 'bg-secondary/15 text-secondary' :
                slo.status === 'breached' ? 'bg-error-container/40 text-error' :
                'bg-surface-container-high text-on-surface-variant'
              }`}>
                {slo.status === 'no_data' ? 'Waiting for telemetry' : slo.status === 'met' ? 'Objective met' : 'Objective breached'}
              </span>
            </div>
            <p className="mt-3 text-sm">
              {metricLabels[slo.metric]} ≤ {slo.threshold}% · target {slo.targetPercent}% · last {slo.windowHours}h
            </p>
            <div className="mt-2 flex flex-wrap gap-x-6 gap-y-1 text-sm text-on-surface-variant">
              <span>Observed compliance: {slo.compliancePercent === null ? 'No data' : `${slo.compliancePercent}%`}</span>
              <span>Error budget remaining: {slo.errorBudgetRemainingPercent === null ? 'No data' : `${slo.errorBudgetRemainingPercent}%`}</span>
              <span>Samples: {slo.sampleCount}</span>
            </div>
            <button
              type="button"
              onClick={() => deleteMutation.mutate(slo.id)}
              disabled={deleteMutation.isPending}
              className="mt-3 rounded border border-outline-variant px-3 py-1.5 text-xs disabled:opacity-50"
            >
              Delete SLO
            </button>
          </article>
        ))}
      </section>
    </div>
  );
};
