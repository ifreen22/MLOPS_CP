import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, 
  ResponsiveContainer 
} from 'recharts';
import { 
  Activity, AlertTriangle, ShieldCheck, Zap, 
  HeartPulse, GitMerge, Server, Clock, ServerCrash, CheckCircle2, XCircle, Play
} from 'lucide-react';
import { mlService } from '../../services/mlService';
import { useSystemTelemetry } from '../../hooks/useSystemTelemetry';
import { useSystemSettings } from '../../hooks/useSystemSettings';
import { apiClient, fetchActionHistory } from '../../services/api';

// Utility for glowing effects
const Glow = ({ color }: { color: string }) => (
  <div className={`absolute -bottom-10 -right-10 w-32 h-32 rounded-full ${color} blur-[3xl] opacity-20 group-hover:opacity-40 transition-opacity duration-700 pointer-events-none`} />
);

export const Dashboard: React.FC = () => {
  const isLoading = false;

  const { data: mlHealth, isError: mlHealthError } = useQuery({
    queryKey: ['mlHealth'],
    queryFn: mlService.getHealth,
    refetchInterval: 10000,
  });
  const {
    data: actionHistory = [],
    isError: actionHistoryError,
    isLoading: actionHistoryLoading,
  } = useQuery({
    queryKey: ['actionHistory'],
    queryFn: fetchActionHistory,
    refetchInterval: 5000,
  });

  const { settings, updateSettings, error: settingsLoadError } = useSystemSettings();
  const { data: telemetryData, history: telemetryTrend, recommendations, isDocker, error: telemetryError } = useSystemTelemetry(settings.isMonitoring ? (settings.pollingInterval * 1000) : 99999999);
  const [activeTab, setActiveTab] = useState<'telemetry' | 'network'>('telemetry');
  const [actionInProgress, setActionInProgress] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  
  // Real-time clock
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  if (isLoading) {
    return (
      <div className="flex w-full h-full p-8 items-center justify-center">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary"></div>
      </div>
    );
  }

  const isModelsReady = mlHealth?.status === 'healthy';

  const realProcesses = telemetryData?.processes || [];
  const protectedProcesses = new Set([
    'system', 'registry', 'smss.exe', 'csrss.exe', 'wininit.exe',
    'services.exe', 'lsass.exe', 'winlogon.exe',
  ]);
  const actionableProcess = realProcesses.find((proc: any) =>
    proc.pid > 4 &&
    proc.cpu_percent >= 20 &&
    !protectedProcesses.has(String(proc.name || '').toLowerCase())
  );
  const updateSystemSettings = async (change: { isMonitoring?: boolean; autoRecovery?: boolean }) => {
    setSettingsError(null);
    try {
      await updateSettings(change);
    } catch {
      setSettingsError('Could not save monitoring settings. Check the backend connection and try again.');
    }
  };

  const queueProcessTermination = async (name: string, pid: number) => {
    if (!settings.autoRecovery) {
      window.alert('Please enable the "Auto Recovery" toggle in Mission Control header before executing process actions.');
      return;
    }
    if (actionInProgress) return;
    if (!window.confirm(`Terminate ${name} (PID ${pid}) on this computer? This will close the process.`)) return;

    setActionInProgress(true);
    try {
      await apiClient.post('/system/actions', { actionType: 'TERMINATE_PROCESS', target: pid });
      window.alert(`Termination queued for ${name} (PID ${pid}).`);
    } catch (error) {
      const message = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      window.alert(message || 'Could not queue the action. Check that telemetry and the Windows agent are running.');
    } finally {
      setActionInProgress(false);
    }
  };

  const nodeHeatmap = realProcesses.slice(0, 24).map((proc: any) => {
    let status = 'healthy';
    if (proc.cpu_percent > 80 || proc.memory_percent > 80) status = 'critical';
    else if (proc.cpu_percent > 40 || proc.memory_percent > 40) status = 'warning';
    
    return {
      id: proc.name || `pid-${proc.pid}`,
      pid: proc.pid,
      status,
      load: Math.round(proc.cpu_percent || 0),
      mem: Math.round(proc.memory_percent || 0)
    };
  });
  
  return (
    <div className="flex flex-col w-full min-h-full p-6 lg:p-8 space-y-6 overflow-x-hidden">
      
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-2">
        <div>
          <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-foreground to-muted-foreground">
            Mission Control
          </h1>
          <p className="text-sm text-muted-foreground flex items-center gap-2 mt-1">
            <Clock size={14} /> {time.toUTCString()}
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 mr-4">
            <span className="text-sm font-medium text-muted-foreground">Status:</span>
            <span className="relative flex h-3 w-3 shrink-0">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${settings.isMonitoring ? 'bg-success' : 'bg-warning'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-3 w-3 ${settings.isMonitoring ? 'bg-success' : 'bg-warning'}`}></span>
            </span>
            <span className={`text-sm font-bold ${settings.isMonitoring ? 'text-success' : 'text-warning'}`}>
              {settings.isMonitoring ? 'Monitoring' : 'Idle'}
            </span>
          </div>
          
          <label className="flex items-center gap-2 cursor-pointer mr-2">
            <input 
              type="checkbox" 
              checked={settings.autoRecovery} 
              onChange={(e) => void updateSystemSettings({ autoRecovery: e.target.checked })}
              className="accent-primary w-4 h-4"
            />
            <span className="text-sm font-medium text-muted-foreground">Auto Recovery</span>
          </label>

          {!settings.isMonitoring ? (
            <motion.button 
              whileHover={{ scale: 1.02, boxShadow: '0 0 15px rgba(var(--success), 0.3)' }}
              whileTap={{ scale: 0.98 }}
              className="px-4 py-2 rounded-md bg-success text-success-foreground text-sm font-medium shadow-lg hover:bg-success/90 transition-all"
              onClick={() => void updateSystemSettings({ isMonitoring: true })}
            >
              Start Monitoring
            </motion.button>
          ) : (
            <motion.button 
              whileHover={{ scale: 1.02, boxShadow: '0 0 15px rgba(var(--destructive), 0.3)' }}
              whileTap={{ scale: 0.98 }}
              className="px-4 py-2 rounded-md bg-destructive text-destructive-foreground text-sm font-medium shadow-lg hover:bg-destructive/90 transition-all"
              onClick={() => void updateSystemSettings({ isMonitoring: false })}
            >
              Stop Monitoring
            </motion.button>
          )}
        </div>
      </div>

      {settingsError && (
        <div role="alert" className="w-full bg-destructive/10 border border-destructive/40 text-destructive p-3 rounded-md">
          {settingsError}
        </div>
      )}
      {settingsLoadError && (
        <div role="alert" className="w-full bg-destructive/10 border border-destructive/40 text-destructive p-3 rounded-md">
          {settingsLoadError}
        </div>
      )}
      {telemetryError && (
        <div role="alert" className="w-full bg-warning/10 border border-warning/40 text-warning p-3 rounded-md">
          {telemetryError}
        </div>
      )}
      {mlHealthError && (
        <div role="alert" className="w-full bg-warning/10 border border-warning/40 text-warning p-3 rounded-md">
          Could not retrieve model readiness from the backend.
        </div>
      )}

      {/* WARNINGS & ALERTS */}
      {isDocker && !telemetryData && settings.isMonitoring && (
        <div className="w-full bg-warning/20 border border-warning/50 text-warning p-4 rounded-md flex items-center justify-between">
            <div className="flex items-center gap-3">
                <AlertTriangle size={20} />
                <span className="font-semibold">Host telemetry is not reaching the backend. Start the Windows agent from the project folder.</span>
            </div>
            <code className="text-sm opacity-80">python windows_agent.py</code>
        </div>
      )}

      {settings.isMonitoring && !telemetryData && !isDocker && (
        <div className="w-full bg-muted/50 border border-border text-muted-foreground p-4 rounded-md flex items-center gap-3">
            <Clock size={20} className="animate-spin" />
            <span className="font-semibold">Waiting for live telemetry...</span>
        </div>
      )}

      {!settings.isMonitoring && (
        <div className="w-full bg-muted/50 border border-border text-muted-foreground p-4 rounded-md flex items-center justify-center">
            <span className="font-semibold">Monitoring is OFF. Click 'Start Monitoring' to begin collecting live telemetry.</span>
        </div>
      )}

      {/* AI ORCHESTRATOR STATUS BAR */}
      <motion.div 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full glass-panel flex flex-col md:flex-row md:items-center justify-between p-5 border-l-4 border-l-primary relative overflow-hidden group"
      >
        <Glow color="bg-primary" />
        <div className="flex items-center gap-4 z-10">
          <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20">
            <HeartPulse className="text-primary animate-pulse" size={24} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">AIOps Sentinel Core</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="relative flex h-3 w-3 shrink-0">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isModelsReady ? 'bg-success' : 'bg-warning'} opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-3 w-3 ${isModelsReady ? 'bg-success' : 'bg-warning'}`}></span>
              </span>
              <span className="text-lg font-bold text-foreground tracking-tight">
                {isModelsReady ? 'Required models are ready' : mlHealthError ? 'Model status unavailable' : 'Some models are unavailable'}
              </span>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-8 mt-4 md:mt-0 z-10">
          <div className="flex flex-col items-start md:items-end">
            <span className="text-xs text-muted-foreground uppercase font-semibold">GraphSAGE RCA</span>
            <div className="flex items-center gap-1.5 mt-1">
              {mlHealth?.services?.root_cause_analysis ? <CheckCircle2 size={16} className="text-success" /> : <XCircle size={16} className="text-muted-foreground" />}
              <span className={mlHealth?.services?.root_cause_analysis ? 'text-foreground font-medium' : 'text-muted-foreground'}>
                {mlHealth?.services?.root_cause_analysis ? 'Trained' : 'Training required'}
              </span>
            </div>
          </div>
          <div className="flex flex-col items-start md:items-end border-l border-border/50 pl-8">
            <span className="text-xs text-muted-foreground uppercase font-semibold">LightGBM Risk</span>
            <div className="flex items-center gap-1.5 mt-1">
              {mlHealth?.services?.risk_prediction ? <CheckCircle2 size={16} className="text-success" /> : <XCircle size={16} className="text-muted-foreground" />}
              <span className={mlHealth?.services?.risk_prediction ? 'text-foreground font-medium' : 'text-muted-foreground'}>
                {mlHealth?.services?.risk_prediction ? 'Scoring' : 'Standby'}
              </span>
            </div>
          </div>
          <div className="flex flex-col items-start md:items-end border-l border-border/50 pl-8">
            <span className="text-xs text-muted-foreground uppercase font-semibold">HDBSCAN Clustering</span>
            <div className="flex items-center gap-1.5 mt-1">
              {mlHealth?.services?.alert_clustering ? <CheckCircle2 size={16} className="text-success" /> : <XCircle size={16} className="text-muted-foreground" />}
              <span className={mlHealth?.services?.alert_clustering ? 'text-foreground font-medium' : 'text-muted-foreground'}>
                {mlHealth?.services?.alert_clustering ? 'Trained' : 'Training required'}
              </span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* HARDWARE KPI GRID */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'CPU Usage', value: telemetryData ? `${telemetryData.cpu?.usage_percent.toFixed(1)}%` : 'No live telemetry received', sub: telemetryData ? `${telemetryData.cpu?.logical_cores} Cores @ ${(telemetryData.cpu?.current_freq / 1000).toFixed(2)}GHz` : 'No live telemetry received', color: 'text-blue-500', bg: 'bg-blue-500/10' },
          { label: 'Memory Usage', value: telemetryData ? `${telemetryData.ram?.percent.toFixed(1)}%` : 'No live telemetry received', sub: telemetryData ? `${(telemetryData.ram?.used / 1024 / 1024 / 1024).toFixed(1)}GB / ${(telemetryData.ram?.total / 1024 / 1024 / 1024).toFixed(1)}GB` : 'No live telemetry received', color: 'text-purple-500', bg: 'bg-purple-500/10' },
          { label: 'Disk Usage', value: telemetryData ? `${telemetryData.disk?.percent.toFixed(1)}%` : 'No live telemetry received', sub: telemetryData ? `${(telemetryData.disk?.used / 1024 / 1024 / 1024).toFixed(1)}GB / ${(telemetryData.disk?.total / 1024 / 1024 / 1024).toFixed(1)}GB` : 'No live telemetry received', color: 'text-orange-500', bg: 'bg-orange-500/10' },
          { label: 'Network I/O', value: telemetryData ? `${(telemetryData.network?.upload_speed / 1024 / 1024).toFixed(2)} MB/s` : 'No live telemetry received', sub: telemetryData ? `↓ ${(telemetryData.network?.download_speed / 1024 / 1024).toFixed(2)} MB/s` : 'No live telemetry received', color: 'text-teal-500', bg: 'bg-teal-500/10' },
        ].map((kpi, i) => (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            key={`hw-${i}`}
            className="glass p-4 rounded-xl border border-border/50 flex flex-col justify-center relative overflow-hidden"
          >
             <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">{kpi.label}</h3>
             <div className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</div>
             <p className="text-[10px] text-muted-foreground mt-1 font-mono">{kpi.sub}</p>
             <div className={`absolute -right-4 -bottom-4 w-16 h-16 rounded-full ${kpi.bg} blur-xl`}></div>
          </motion.div>
        ))}
      </div>

      {/* MISSION KPI GRID */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'High-resource Processes', value: telemetryData ? telemetryData.processes.filter(p => p.cpu_percent > 30 || p.memory_percent > 30).length : '—', sub: 'CPU or memory above 30%', icon: AlertTriangle, color: 'text-destructive', bg: 'bg-destructive/10' },
          { label: 'Machine Load', value: telemetryData?.cpu?.load_avg?.[0] != null ? telemetryData.cpu.load_avg[0].toFixed(2) : '—', sub: '1-minute load average', icon: GitMerge, color: 'text-primary', bg: 'bg-primary/10' },
          { label: 'CPU Headroom', value: telemetryData ? `${(100 - (telemetryData.cpu?.usage_percent || 0)).toFixed(1)}%` : 'No live telemetry received', sub: 'Host CPU capacity', icon: ShieldCheck, color: 'text-success', bg: 'bg-success/10' },
          { label: 'AI Recommendations', value: recommendations.length, sub: 'Based on latest host telemetry', icon: Zap, color: 'text-warning', bg: 'bg-warning/10' },
        ].map((kpi, i) => (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            key={i}
            className="glass-panel p-6 relative overflow-hidden group hover:border-primary/40 transition-all duration-300 hover:-translate-y-1"
          >
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-sm font-semibold text-muted-foreground">{kpi.label}</h3>
              <div className={`p-2.5 rounded-lg ${kpi.bg} shadow-inner`}>
                <kpi.icon size={20} className={kpi.color} />
              </div>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold tracking-tight text-foreground">{kpi.value}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-2 font-medium">{kpi.sub}</p>
            <div className={`absolute -bottom-8 -right-8 w-24 h-24 rounded-full ${kpi.bg} blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500`}></div>
          </motion.div>
        ))}
      </div>

      {/* CHARTS & RADAR ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* TELEMETRY CHART */}
        <motion.div 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-2 glass-panel p-6 flex flex-col min-h-[400px] relative overflow-hidden"
        >
          <div className="flex items-center justify-between mb-6 z-10">
            <div>
              <h3 className="font-semibold text-lg tracking-tight flex items-center gap-2">
                <Activity size={18} className="text-primary"/> Global Telemetry Pulse
              </h3>
              <p className="text-sm text-muted-foreground mt-1">{activeTab === 'telemetry' ? 'Live host CPU and memory usage' : 'Live host network throughput'}</p>
            </div>
            <div className="flex bg-secondary/50 p-1 rounded-lg border border-border/50">
              <button 
                onClick={() => setActiveTab('telemetry')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${activeTab === 'telemetry' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Compute
              </button>
              <button 
                onClick={() => setActiveTab('network')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${activeTab === 'network' ? 'bg-background shadow text-foreground' : 'text-muted-foreground hover:text-foreground'}`}
              >
                Network
              </button>
            </div>
          </div>
          
          <div className="flex-1 w-full min-h-0 z-10 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={telemetryTrend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.4}/>
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--destructive))" stopOpacity={0.2}/>
                    <stop offset="95%" stopColor="hsl(var(--destructive))" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} opacity={0.5} />
                <XAxis dataKey="time" stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} tickLine={false} axisLine={false} />
                <RechartsTooltip 
                  contentStyle={{ backgroundColor: 'hsl(var(--card))', borderColor: 'hsl(var(--border))', borderRadius: '8px', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
                  itemStyle={{ color: 'hsl(var(--foreground))', fontWeight: 500 }}
                  labelStyle={{ color: 'hsl(var(--muted-foreground))', marginBottom: '4px' }}
                />
                {activeTab === 'telemetry' ? (
                  <>
                    <Area type="monotone" dataKey="cpu" name="CPU Usage (%)" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={3} animationDuration={300} />
                    <Area type="monotone" dataKey="memory" name="Memory Usage (%)" stroke="hsl(var(--destructive))" fillOpacity={1} fill="url(#colorLatency)" strokeWidth={2} animationDuration={300} />
                  </>
                ) : (
                  <>
                    <Area type="monotone" dataKey="upload" name="Upload (MB/s)" stroke="hsl(var(--primary))" fillOpacity={1} fill="url(#colorCpu)" strokeWidth={3} animationDuration={300} />
                    <Area type="monotone" dataKey="download" name="Download (MB/s)" stroke="hsl(var(--destructive))" fillOpacity={1} fill="url(#colorLatency)" strokeWidth={2} animationDuration={300} />
                  </>
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* AI RECOMMENDATIONS / RISK RADAR */}
        <motion.div 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="glass-panel p-6 flex flex-col relative overflow-hidden group"
        >
          <Glow color="bg-warning" />
          <h3 className="font-semibold text-lg tracking-tight mb-1 flex items-center gap-2 z-10">
            <Zap size={18} className="text-warning fill-warning/20" /> AI Action Radar
          </h3>
          <p className="text-sm text-muted-foreground mb-6 z-10">Recommendations from the latest host telemetry sample.</p>
          
          <div className="flex-1 overflow-y-auto space-y-4 pr-2 z-10 scrollbar-thin">
            {recommendations.length > 0 ? recommendations.map((rec, idx) => {
              const isProcessRecommendation = Boolean(
                actionableProcess &&
                rec.toLowerCase().startsWith('consider reviewing high-cpu process:') &&
                rec.toLowerCase().includes((actionableProcess.name || `pid-${actionableProcess.pid}`).toLowerCase()) &&
                rec.includes(`PID: ${actionableProcess.pid}`)
              );
              return (
              <div key={idx} className="p-4 rounded-xl bg-card border border-border hover:border-warning/50 transition-colors shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded-full bg-primary/20 text-primary text-xs font-bold tracking-wide">AI RECOMMENDATION</span>
                  </div>
                  <span className="text-xs text-muted-foreground">Latest sample</span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed mb-3">
                  {rec}
                </p>
                {isProcessRecommendation && (
                  <div className="flex gap-2">
                    <button
                    className="text-xs font-medium px-3 py-1.5 bg-primary text-primary-foreground rounded hover:bg-primary/90 transition-colors flex items-center justify-center gap-1 w-full disabled:opacity-50 disabled:cursor-not-allowed"
                    disabled={!actionableProcess || actionInProgress}
                    title={!settings.autoRecovery ? 'Enable Auto Recovery to execute host actions' : !actionableProcess ? 'No eligible high-CPU process is present in live telemetry' : undefined}
                    onClick={() => actionableProcess && void queueProcessTermination(actionableProcess.name || `PID ${actionableProcess.pid}`, actionableProcess.pid)}
                    >
                      <Play size={14} /> {actionInProgress ? 'Queueing...' : 'Queue process termination'}
                    </button>
                    {!settings.autoRecovery && <p className="mt-2 text-xs text-muted-foreground">Enable Auto Recovery to allow confirmed process actions.</p>}
                  </div>
                )}
              </div>
            );
            }) : (
              <div className="text-sm text-muted-foreground p-4 text-center">
                {telemetryData ? 'No immediate actions recommended. Systems normal.' : 'Start monitoring and run the Windows agent to receive live recommendations.'}
              </div>
            )}
          </div>
        </motion.div>
      </div>

      {/* BOTTOM ROW: TOPOLOGY HEATMAP & ACTIVE SITUATIONS */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        
        {/* Node Topology */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-6"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-semibold text-lg tracking-tight flex items-center gap-2">
              <Server size={18} className="text-foreground" /> Host Process Heatmap
            </h3>
            <div className="flex gap-4 text-xs font-medium text-muted-foreground">
              <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded bg-success/20 border border-success"></div> Healthy</span>
              <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded bg-warning/20 border border-warning"></div> Warning</span>
              <span className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 rounded bg-destructive/20 border border-destructive"></div> Critical</span>
            </div>
          </div>
          
          <div className="grid grid-cols-6 sm:grid-cols-8 gap-2">
            {nodeHeatmap.length === 0 && (
              <p className="col-span-full text-center text-sm text-muted-foreground">No process telemetry yet. Start monitoring and run the Windows agent.</p>
            )}
            {nodeHeatmap.map((node, i) => {
              const colors = {
                healthy: 'bg-success/10 border-success/30 hover:bg-success/20',
                warning: 'bg-warning/20 border-warning/50 hover:bg-warning/30 animate-pulse',
                critical: 'bg-destructive/20 border-destructive/50 hover:bg-destructive/30 animate-pulse'
              };
              return (
                <div
                  key={`${node.id}-${i}`}
                  title={`${node.id} - CPU: ${node.load}% | RAM: ${node.mem}%`}
                  className={`aspect-square rounded-md border ${colors[node.status as keyof typeof colors]} transition-colors flex flex-col items-center justify-center p-1 overflow-hidden`}
                >
                  <span className="text-[10px] font-mono opacity-50 truncate w-full text-center">{node.id.split('.')[0]}</span>
                  <span className="text-[9px] font-mono opacity-40">{node.load}%</span>
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* High resource processes */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-6 flex flex-col"
        >
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-semibold text-lg tracking-tight flex items-center gap-2">
              <ServerCrash size={18} className="text-destructive" /> High Resource Processes
            </h3>
          </div>
          
          <div className="space-y-3 flex-1 overflow-y-auto pr-2">
            {telemetryData && telemetryData.processes.filter(p => p.cpu_percent > 15 || p.memory_percent > 15).length > 0 ? (
              telemetryData.processes
                .filter(p => p.cpu_percent > 15 || p.memory_percent > 15)
                .map((proc, idx) => {
                  const isCritical = proc.cpu_percent > 50 || proc.memory_percent > 50;
                  return (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-card border border-border hover:border-muted-foreground/30 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className={`w-2 h-2 rounded-full ${isCritical ? 'bg-destructive shadow-[0_0_8px_rgba(var(--destructive),0.8)]' : 'bg-warning'}`} />
                        <div>
                          <h4 className="text-sm font-semibold text-foreground">{proc.name || `PID ${proc.pid}`}</h4>
                          <div className="flex gap-2 text-xs text-muted-foreground mt-1 font-mono">
                            <span>PID: {proc.pid}</span>
                            <span>•</span>
                            <span>CPU: {proc.cpu_percent}%</span>
                            <span>•</span>
                            <span>RAM: {proc.memory_percent}%</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        {proc.pid > 4 && !protectedProcesses.has(String(proc.name || '').toLowerCase()) && (
                          <button
                            type="button"
                            className="text-xs font-medium px-2.5 py-1 bg-destructive/10 text-destructive border border-destructive/20 rounded hover:bg-destructive hover:text-destructive-foreground transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                            disabled={actionInProgress}
                            title={!settings.autoRecovery ? 'Auto Recovery must be enabled to execute termination' : `Terminate ${proc.name || proc.pid}`}
                            onClick={() => void queueProcessTermination(proc.name || `PID ${proc.pid}`, proc.pid)}
                          >
                            Terminate
                          </button>
                        )}
                        <span className="text-xs font-medium text-muted-foreground">Current sample</span>
                      </div>
                    </div>
                  );
                })
            ) : (
              <div className="text-sm text-muted-foreground p-4 text-center border border-dashed border-border rounded-lg">No high-resource processes in the current telemetry sample.</div>
            )}
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-6"
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="font-semibold text-lg tracking-tight flex items-center gap-2">
            <Activity size={18} className="text-primary" /> Recent Process Actions
          </h3>
          <span className="text-xs text-muted-foreground">Refreshes every 5 seconds</span>
        </div>
        {actionHistoryLoading ? (
          <p className="text-sm text-muted-foreground">Loading action history...</p>
        ) : actionHistoryError ? (
          <p className="text-sm text-destructive">Action history is unavailable. Check the API connection.</p>
        ) : actionHistory.length === 0 ? (
          <p className="text-sm text-muted-foreground">No process actions have been requested.</p>
        ) : (
          <div className="space-y-2">
            {actionHistory.slice(0, 10).map((action) => (
              <div
                key={action.id}
                className="flex flex-col gap-2 rounded-lg border border-border bg-card p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {action.actionType.replaceAll('_', ' ')}: {action.processName || action.target || 'Unknown target'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(action.createdAt).toLocaleString()}
                    {action.requestedByEmail ? ` · requested by ${action.requestedByEmail}` : ''}
                    {action.result ? ` · ${action.result}` : ''}
                  </p>
                </div>
                <span className={`shrink-0 text-xs font-semibold ${
                  action.status === 'SUCCESS'
                    ? 'text-success'
                    : action.status === 'FAILED'
                      ? 'text-destructive'
                      : 'text-warning'
                }`}>
                  {action.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default Dashboard;
