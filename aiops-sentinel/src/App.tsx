import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from './components/layout/AppLayout';
import { AUTH_TOKEN_KEY } from './services/api';

// Lazy loading heavy pages for performance and bundle splitting
const Dashboard = lazy(() => import('./features/mission-control/Dashboard').then(m => ({ default: m.Dashboard })));
const SituationRoom = lazy(() => import('./features/situations/SituationRoom'));
const AlertClustering = lazy(() => import('./features/alert-clustering/AlertClustering').then(m => ({ default: m.AlertClustering })));
const RootCauseGraph = lazy(() => import('./features/root-cause/RootCauseGraph'));
const ChangeIntelligence = lazy(() => import('./features/change-intelligence/ChangeIntelligence').then(m => ({ default: m.ChangeIntelligence })));
const RemediationPlaybooks = lazy(() => import('./features/playbooks/RemediationPlaybooks').then(m => ({ default: m.RemediationPlaybooks })));
const SloDashboard = lazy(() => import('./features/slo/SloDashboard').then(m => ({ default: m.SloDashboard })));
const Settings = lazy(() => import('./features/settings/Settings').then(m => ({ default: m.Settings })));
const AuditLogs = lazy(() => import('./features/settings/AuditLogs').then(m => ({ default: m.AuditLogs })));
const LoginPage = lazy(() => import('./features/auth/LoginPage'));

const queryClient = new QueryClient();

import { ThemeProvider } from './components/ThemeProvider';

// Suspense fallback
const LoadingFallback = () => (
  <div className="flex w-full h-full items-center justify-center min-h-[50vh] bg-background">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
  </div>
);

const RequireAuth: React.FC = () => (
  sessionStorage.getItem(AUTH_TOKEN_KEY) ? <Outlet /> : <Navigate to="/login" replace />
);

export const App: React.FC = () => {
  return (
    <ThemeProvider defaultTheme="system" storageKey="aiops-theme">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Suspense fallback={<LoadingFallback />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<RequireAuth />}>
                <Route path="/" element={<AppLayout />}>
                  <Route index element={<Dashboard />} />
                  <Route path="situations" element={<SituationRoom />} />
                  <Route path="alert-clustering" element={<AlertClustering />} />
                  <Route path="root-cause-graph" element={<RootCauseGraph />} />
                  <Route path="change-intelligence" element={<ChangeIntelligence />} />
                  <Route path="remediation-playbooks" element={<RemediationPlaybooks />} />
                  <Route path="slo-dashboard" element={<SloDashboard />} />
                  <Route path="settings" element={<Settings />} />
                  <Route path="audit-logs" element={<AuditLogs />} />
                </Route>
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
};

export default App;
