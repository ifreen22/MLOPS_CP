import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '../../utils/cn';
import {
  getCurrentUser,
  fetchPolicies,
  updatePolicy,
  createPolicy,
  validatePolicy,
  fetchServices,
  updateServiceTier,
  fetchNotificationSettings,
  updateNotificationSettings,
  sendTestNotification,
  type ServiceRecord,
} from '../../services/api';
import { UserManagement } from './UserManagement';

export const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'policy-editor' | 'service-tiers' | 'notification-routing' | 'user-management'>('policy-editor');
  const queryClient = useQueryClient();

  const currentUserQuery = useQuery({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 30_000,
  });
  const isAdministrator = currentUserQuery.data?.role === 'ADMIN';

  // --- POLICIES TAB STATE ---
  const policiesQuery = useQuery({ queryKey: ['policies'], queryFn: fetchPolicies });
  const [selectedPolicyId, setSelectedPolicyId] = useState<string>('');
  const [policyRules, setPolicyRules] = useState<string>('');
  const [policyName, setPolicyName] = useState<string>('');
  const [policyDesc, setPolicyDesc] = useState<string>('');
  const [policyEnabled, setPolicyEnabled] = useState<boolean>(true);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [saveStatus, setSaveStatus] = useState<string | null>(null);

  const selectedPolicy = policiesQuery.data?.find((p) => p.id === selectedPolicyId) || policiesQuery.data?.[0];

  useEffect(() => {
    if (selectedPolicy) {
      setSelectedPolicyId(selectedPolicy.id);
      setPolicyName(selectedPolicy.name);
      setPolicyDesc(selectedPolicy.description || '');
      setPolicyRules(selectedPolicy.rules);
      setPolicyEnabled(selectedPolicy.isEnabled);
      setValidationResult(null);
    }
  }, [selectedPolicy?.id]);

  const savePolicyMutation = useMutation({
    mutationFn: async () => {
      if (selectedPolicyId) {
        return updatePolicy(selectedPolicyId, {
          name: policyName,
          description: policyDesc,
          rules: policyRules,
          isEnabled: policyEnabled,
        });
      }
      return createPolicy({
        name: policyName,
        description: policyDesc,
        rules: policyRules,
        isEnabled: policyEnabled,
      });
    },
    onSuccess: () => {
      setSaveStatus('Policy saved successfully!');
      setTimeout(() => setSaveStatus(null), 3000);
      void queryClient.invalidateQueries({ queryKey: ['policies'] });
    },
    onError: (err: any) => {
      setSaveStatus(`Failed to save policy: ${err.message || 'Error'}`);
    },
  });

  const validatePolicyMutation = useMutation({
    mutationFn: async () => validatePolicy(policyRules),
    onSuccess: (data) => setValidationResult(data),
    onError: (err: any) => {
      setValidationResult({
        valid: false,
        decision: 'ERROR',
        trace: [err.response?.data?.detail || err.message || 'Validation failed'],
      });
    },
  });

  // --- SERVICE TIERS TAB STATE ---
  const servicesQuery = useQuery({ queryKey: ['services'], queryFn: fetchServices });
  const [tierUpdateMsg, setTierUpdateMsg] = useState<string | null>(null);

  const updateTierMutation = useMutation({
    mutationFn: ({ id, tier }: { id: string; tier: string }) => updateServiceTier(id, tier),
    onSuccess: (updated) => {
      setTierUpdateMsg(`Updated ${updated.name} tier successfully.`);
      setTimeout(() => setTierUpdateMsg(null), 3000);
      void queryClient.invalidateQueries({ queryKey: ['services'] });
    },
  });

  const getTierFromDesc = (desc: string | null): string => {
    if (!desc) return 'Tier 3 - Standard Support';
    if (desc.includes('Tier 1')) return 'Tier 1 - Mission Critical';
    if (desc.includes('Tier 2')) return 'Tier 2 - Business Essential';
    return 'Tier 3 - Standard Support';
  };

  // --- NOTIFICATION ROUTING TAB STATE ---
  const notifQuery = useQuery({ queryKey: ['notificationSettings'], queryFn: fetchNotificationSettings });
  const [webhookUrl, setWebhookUrl] = useState('');
  const [slackChannel, setSlackChannel] = useState('');
  const [pagerDutyKey, setPagerDutyKey] = useState('');
  const [minSeverity, setMinSeverity] = useState('HIGH');
  const [notifStatusMsg, setNotifStatusMsg] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any>(null);

  useEffect(() => {
    if (notifQuery.data) {
      setWebhookUrl(notifQuery.data.webhookUrl || '');
      setSlackChannel(notifQuery.data.slackChannel || '');
      setPagerDutyKey(notifQuery.data.pagerDutyRoutingKey || '');
      setMinSeverity(notifQuery.data.minSeverity || 'HIGH');
    }
  }, [notifQuery.data]);

  const saveNotifMutation = useMutation({
    mutationFn: () =>
      updateNotificationSettings({
        webhookUrl,
        slackChannel,
        pagerDutyRoutingKey: pagerDutyKey,
        minSeverity,
      }),
    onSuccess: () => {
      setNotifStatusMsg('Notification channels updated.');
      setTimeout(() => setNotifStatusMsg(null), 3000);
      void queryClient.invalidateQueries({ queryKey: ['notificationSettings'] });
    },
  });

  const testNotifMutation = useMutation({
    mutationFn: () => sendTestNotification('webhook', `Verification test dispatched to ${slackChannel || 'default'}`),
    onSuccess: (data) => setTestResult(data),
    onError: (err: any) => {
      setTestResult({ status: 'failed', message: err.message || 'Dispatch failed' });
    },
  });

  const tabs = [
    { id: 'policy-editor', label: 'Policy Editor (Rego)', icon: 'terminal' },
    { id: 'service-tiers', label: 'Service Tiers', icon: 'layers' },
    { id: 'notification-routing', label: 'Notification Routing', icon: 'alt_route' },
    ...(isAdministrator ? [{ id: 'user-management' as const, label: 'User Management & SSO', icon: 'shield_person' }] : []),
  ] as const;

  return (
    <div className="flex flex-col w-full min-h-screen bg-surface-container-lowest text-on-surface font-body-md">
      {/* Header */}
      <div className="px-space-lg py-space-md border-b border-outline-variant bg-surface-container-low">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-space-md">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-space-sm">
              <h1 className="font-headline-md text-on-surface font-semibold tracking-tight">Settings & Policies</h1>
              <span className="px-2 py-0.5 rounded bg-primary/10 text-primary font-label-code-sm border border-primary/20 text-[0.625rem] font-semibold">Active Engine</span>
              <span className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface font-label-code-sm border border-outline-variant text-[0.625rem]">OPA Rego v1.0</span>
            </div>
            <p className="font-body-sm text-on-surface-variant max-w-3xl">
              Configure automated remediation guardrails, service criticality tiers, alert routing webhooks, and team access controls.
            </p>
          </div>
          <div className="flex items-center gap-space-md bg-surface-container-lowest px-space-md py-2 rounded border border-outline-variant/70 shrink-0">
            <div className="flex flex-col">
              <span className="font-label-code-sm text-outline text-[0.625rem] uppercase">Policy State</span>
              <span className="font-label-code-sm text-on-surface text-[0.6875rem] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
                Policy store: <span className="text-success font-medium">Enforcing ({policiesQuery.data?.length || 0} active)</span>
              </span>
            </div>
            <div className="h-6 w-px bg-outline-variant"></div>
            <div className="flex flex-col">
              <span className="font-label-code-sm text-outline text-[0.625rem] uppercase">Cluster Bound</span>
              <span className="font-label-code-sm text-primary font-medium text-[0.6875rem]">us-east-1-prod</span>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-space-lg border-b border-outline-variant bg-surface-container-lowest flex items-center justify-between overflow-x-auto">
        <nav className="flex space-x-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'px-space-md py-3 font-label-code-md text-[0.75rem] flex items-center gap-2 border-b-2 transition-all font-semibold',
                activeTab === tab.id
                  ? 'border-primary-container text-primary bg-surface-container-high/60'
                  : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              )}
            >
              <span className="material-symbols-outlined text-[16px]">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="p-space-lg">
        {/* TAB 1: POLICY EDITOR */}
        {activeTab === 'policy-editor' && (
          <div className="flex flex-col gap-space-md">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <label className="text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Select Policy:</label>
                <select
                  value={selectedPolicyId}
                  onChange={(e) => setSelectedPolicyId(e.target.value)}
                  className="rounded border border-outline-variant bg-surface-container-low px-3 py-1.5 text-xs font-mono font-medium text-on-surface focus:outline-none"
                >
                  {(policiesQuery.data || []).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} {p.isEnabled ? '(Active)' : '(Disabled)'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-on-surface">
                  <input
                    type="checkbox"
                    checked={policyEnabled}
                    onChange={(e) => setPolicyEnabled(e.target.checked)}
                    className="rounded border-outline-variant text-primary focus:ring-0"
                  />
                  <span>Policy Enforced</span>
                </label>
                <button
                  type="button"
                  onClick={() => validatePolicyMutation.mutate()}
                  disabled={validatePolicyMutation.isPending}
                  className="px-3 py-1.5 rounded bg-surface-container border border-outline-variant text-xs font-semibold text-on-surface hover:bg-surface-container-high flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px] text-tertiary">check_circle</span>
                  <span>{validatePolicyMutation.isPending ? 'Validating...' : 'Validate & Test'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => savePolicyMutation.mutate()}
                  disabled={savePolicyMutation.isPending}
                  className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]">save</span>
                  <span>{savePolicyMutation.isPending ? 'Saving...' : 'Save Policy'}</span>
                </button>
              </div>
            </div>

            {saveStatus && (
              <div className="p-2.5 rounded bg-primary/10 border border-primary/20 text-xs text-primary font-medium flex items-center gap-2">
                <span className="material-symbols-outlined text-[16px]">info</span>
                {saveStatus}
              </div>
            )}

            {/* Editor Container */}
            <div className="rounded border border-outline-variant bg-surface-container-lowest overflow-hidden flex flex-col shadow-sm">
              <div className="px-space-md py-2 bg-surface-container-low border-b border-outline-variant flex items-center justify-between text-outline font-label-code-sm text-[0.6875rem]">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px] text-primary">code</span>
                  <span className="text-on-surface font-mono font-medium">{policyName}</span>
                </div>
                <span className="text-xs text-outline">{policyDesc}</span>
              </div>
              <textarea
                value={policyRules}
                onChange={(e) => setPolicyRules(e.target.value)}
                rows={16}
                spellCheck={false}
                className="w-full bg-[#080c14] text-[#79c0ff] font-mono text-xs p-4 leading-relaxed focus:outline-none resize-y border-0"
                placeholder="package aiops..."
              />
            </div>

            {/* Validation & Test Output */}
            {validationResult && (
              <div className="rounded border border-outline-variant bg-surface-container-low p-4 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-xs text-on-surface uppercase tracking-wider">Evaluation Result:</span>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded font-label-code-sm text-[0.6875rem] font-bold',
                        validationResult.decision === 'ALLOW' ? 'bg-success/20 text-success' : 'bg-error/20 text-error'
                      )}
                    >
                      {validationResult.decision}
                    </span>
                  </div>
                  <span className="text-xs text-outline font-mono">{validationResult.syntax} · {validationResult.rules_evaluated} rules checked</span>
                </div>
                <ul className="mt-1 space-y-1 text-xs font-mono text-on-surface-variant">
                  {validationResult.trace?.map((line: string, idx: number) => (
                    <li key={idx} className="flex items-center gap-1.5">
                      <span className="text-outline">›</span>
                      <span>{line}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: SERVICE TIERS */}
        {activeTab === 'service-tiers' && (
          <div className="flex flex-col gap-space-md">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-on-surface">Service Criticality & SLA Tiers</h2>
                <p className="text-xs text-on-surface-variant mt-0.5">Define operational tier levels, automated remediation priority, and SLA budgets.</p>
              </div>
              {tierUpdateMsg && (
                <div className="px-3 py-1 rounded bg-success/15 border border-success/30 text-success text-xs font-medium">
                  {tierUpdateMsg}
                </div>
              )}
            </div>

            <div className="rounded border border-outline-variant bg-surface-container-low overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-[#0e1420] text-outline font-label-code-sm text-[0.6875rem] uppercase border-b border-outline-variant">
                    <th className="py-2.5 px-4 font-medium">Service</th>
                    <th className="py-2.5 px-4 font-medium">Description</th>
                    <th className="py-2.5 px-4 font-medium">SLA Target</th>
                    <th className="py-2.5 px-4 font-medium">Current Tier</th>
                    <th className="py-2.5 px-4 text-right font-medium">Update Tier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-outline-variant/60 font-body-sm text-xs">
                  {servicesQuery.isLoading && (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-outline">Loading services...</td>
                    </tr>
                  )}
                  {(servicesQuery.data || []).map((svc: ServiceRecord) => {
                    const currentTier = getTierFromDesc(svc.description);
                    const sla = currentTier.includes('Tier 1') ? '99.99%' : currentTier.includes('Tier 2') ? '99.90%' : '99.00%';
                    return (
                      <tr key={svc.id} className="hover:bg-surface-container transition-colors">
                        <td className="py-3 px-4 font-semibold text-on-surface flex items-center gap-2">
                          <span className="material-symbols-outlined text-primary text-[18px]">dns</span>
                          {svc.name}
                        </td>
                        <td className="py-3 px-4 text-on-surface-variant max-w-md truncate">{svc.description || 'Core microservice'}</td>
                        <td className="py-3 px-4 font-mono font-semibold text-primary">{sla}</td>
                        <td className="py-3 px-4">
                          <span
                            className={cn(
                              'px-2 py-0.5 rounded text-[0.6875rem] font-bold',
                              currentTier.includes('Tier 1')
                                ? 'bg-error/15 text-error border border-error/25'
                                : currentTier.includes('Tier 2')
                                ? 'bg-tertiary/15 text-tertiary border border-tertiary/25'
                                : 'bg-surface-container-high text-on-surface-variant border border-outline-variant'
                            )}
                          >
                            {currentTier}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <select
                            defaultValue={currentTier}
                            onChange={(e) => updateTierMutation.mutate({ id: svc.id, tier: e.target.value })}
                            className="rounded border border-outline-variant bg-surface-container-lowest px-2 py-1 text-xs text-on-surface focus:outline-none cursor-pointer"
                          >
                            <option value="Tier 1 - Mission Critical">Tier 1 - Mission Critical</option>
                            <option value="Tier 2 - Business Essential">Tier 2 - Business Essential</option>
                            <option value="Tier 3 - Standard Support">Tier 3 - Standard Support</option>
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: NOTIFICATION ROUTING */}
        {activeTab === 'notification-routing' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-lg">
            {/* Form */}
            <div className="rounded border border-outline-variant bg-surface-container-low p-space-md flex flex-col gap-4 shadow-sm">
              <div>
                <h2 className="font-headline-sm text-base text-on-surface font-semibold">Alert Routing Webhooks</h2>
                <p className="text-xs text-on-surface-variant mt-1">Configure automated dispatch channels for incident notifications, SLO breaches, and risk gates.</p>
              </div>

              <div className="flex flex-col gap-3">
                <label className="flex flex-col gap-1 text-xs text-on-surface font-medium">
                  Webhook URL (Slack / Teams / Custom)
                  <input
                    type="url"
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="w-full rounded border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-mono text-on-surface focus:outline-none"
                    placeholder="https://hooks.slack.com/services/..."
                  />
                </label>

                <div className="grid grid-cols-2 gap-3">
                  <label className="flex flex-col gap-1 text-xs text-on-surface font-medium">
                    Slack Channel
                    <input
                      type="text"
                      value={slackChannel}
                      onChange={(e) => setSlackChannel(e.target.value)}
                      className="w-full rounded border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs text-on-surface focus:outline-none"
                      placeholder="#alerts-sre"
                    />
                  </label>
                  <label className="flex flex-col gap-1 text-xs text-on-surface font-medium">
                    PagerDuty Routing Key
                    <input
                      type="text"
                      value={pagerDutyKey}
                      onChange={(e) => setPagerDutyKey(e.target.value)}
                      className="w-full rounded border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs font-mono text-on-surface focus:outline-none"
                      placeholder="pd_live_..."
                    />
                  </label>
                </div>

                <label className="flex flex-col gap-1 text-xs text-on-surface font-medium">
                  Minimum Severity Threshold
                  <select
                    value={minSeverity}
                    onChange={(e) => setMinSeverity(e.target.value)}
                    className="w-full rounded border border-outline-variant bg-surface-container-lowest px-3 py-1.5 text-xs text-on-surface focus:outline-none cursor-pointer"
                  >
                    <option value="CRITICAL">CRITICAL (SEV1 Only)</option>
                    <option value="HIGH">HIGH (SEV1 & SEV2)</option>
                    <option value="MEDIUM">MEDIUM (SEV1, SEV2, SEV3)</option>
                    <option value="ALL">ALL (Including Info/Debug)</option>
                  </select>
                </label>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-outline-variant">
                <button
                  type="button"
                  onClick={() => testNotifMutation.mutate()}
                  disabled={testNotifMutation.isPending}
                  className="px-3 py-1.5 rounded bg-surface-container border border-outline-variant text-xs font-semibold text-on-surface hover:bg-surface-container-high flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px] text-primary">send</span>
                  <span>{testNotifMutation.isPending ? 'Sending...' : 'Send Test Alert'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => saveNotifMutation.mutate()}
                  disabled={saveNotifMutation.isPending}
                  className="px-4 py-1.5 rounded bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 flex items-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  <span className="material-symbols-outlined text-[16px]">save</span>
                  <span>{saveNotifMutation.isPending ? 'Saving...' : 'Save Channels'}</span>
                </button>
              </div>

              {notifStatusMsg && (
                <div className="p-2.5 rounded bg-primary/10 border border-primary/20 text-xs text-primary font-medium flex items-center gap-2">
                  <span className="material-symbols-outlined text-[16px]">check_circle</span>
                  {notifStatusMsg}
                </div>
              )}
            </div>

            {/* Test Results Output */}
            <div className="rounded border border-outline-variant bg-surface-container-low p-space-md flex flex-col gap-3 shadow-sm">
              <h3 className="font-semibold text-xs text-on-surface uppercase tracking-wider">Delivery Dispatch Inspector</h3>
              {testResult ? (
                <div className="rounded border border-outline-variant bg-surface-container-lowest p-3 font-mono text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-outline">Delivery Status:</span>
                    <span className="font-bold text-success capitalize">{testResult.status}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-outline">Target Destination:</span>
                    <span className="text-on-surface truncate max-w-xs">{testResult.destination}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-outline">Notification ID:</span>
                    <span className="text-primary truncate">{testResult.notificationId}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-outline">Delivered At:</span>
                    <span className="text-on-surface-variant">{new Date(testResult.deliveredAt).toLocaleTimeString()}</span>
                  </div>
                  <div className="pt-2 border-t border-outline-variant text-on-surface-variant text-[0.6875rem]">
                    {testResult.message}
                  </div>
                </div>
              ) : (
                <div className="h-40 rounded border border-dashed border-outline-variant flex items-center justify-center text-outline text-xs text-center p-4">
                  Click &ldquo;Send Test Alert&rdquo; to simulate a real alert payload dispatch and verify delivery response.
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 4: USER MANAGEMENT */}
        {activeTab === 'user-management' && isAdministrator && <UserManagement />}
      </div>
    </div>
  );
};
