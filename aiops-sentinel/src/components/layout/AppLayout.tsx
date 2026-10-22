import React, { useState } from 'react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ThemeToggle } from '../ThemeToggle';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Activity, 
  AlertTriangle, 
  GitMerge, 
  BookOpen, 
  Settings, 
  Bell,
  ClipboardList,
  Menu,
  ChevronLeft,
  LogOut,
} from 'lucide-react';
import { useLocation } from 'react-router-dom';
import { useSystemSettings } from '../../hooks/useSystemSettings';
import { getCurrentUser, logout } from '../../services/api';

const navItems = [
  { path: '/', label: 'Mission Control', icon: Activity },
  { path: '/situations', label: 'Situation Room', icon: AlertTriangle },
  { path: '/alert-clustering', label: 'Alert Clustering', icon: Bell },
  { path: '/root-cause-graph', label: 'Root Cause Graph', icon: GitMerge },
  { path: '/change-intelligence', label: 'Change Intelligence', icon: GitMerge },
  { path: '/remediation-playbooks', label: 'Playbooks', icon: BookOpen },
  { path: '/slo-dashboard', label: 'SLO Dashboard', icon: Activity },
  { path: '/audit-logs', label: 'Audit Logs', icon: ClipboardList },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export const AppLayout: React.FC = () => {
  const [isSidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { settings, error: settingsError } = useSystemSettings();
  const currentUserQuery = useQuery({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 30_000,
  });
  const visibleNavItems = navItems.filter(
    (item) => item.path !== '/audit-logs' || currentUserQuery.data?.role === 'ADMIN',
  );

  const getPageTitle = () => {
    const item = navItems.find(i => i.path === location.pathname);
    return item ? item.label : 'AIOps Sentinel';
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      
      {/* SIDEBAR */}
      <motion.aside
        initial={{ width: 260 }}
        animate={{ width: isSidebarOpen ? 260 : 72 }}
        className="flex flex-col h-full border-r border-border bg-card/40 backdrop-blur-xl z-20 flex-shrink-0"
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-border/50">
          <AnimatePresence mode="wait">
            {isSidebarOpen && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="flex items-center gap-2 overflow-hidden"
              >
                <div className="w-8 h-8 rounded bg-primary flex items-center justify-center">
                  <Activity size={20} className="text-primary-foreground" />
                </div>
                <span className="font-bold text-lg tracking-tight whitespace-nowrap">AIOps Sentinel</span>
              </motion.div>
            )}
          </AnimatePresence>
          <button
            onClick={() => setSidebarOpen(!isSidebarOpen)}
            aria-label={isSidebarOpen ? 'Collapse navigation' : 'Expand navigation'}
            className="p-1.5 rounded-md hover:bg-accent text-muted-foreground transition-colors"
          >
            {isSidebarOpen ? <ChevronLeft size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {visibleNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => `
                flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group
                ${isActive 
                  ? 'bg-primary text-primary-foreground font-medium shadow-sm' 
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'}
              `}
            >
              <item.icon size={20} className="flex-shrink-0" />
              <AnimatePresence>
                {isSidebarOpen && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="whitespace-nowrap overflow-hidden text-sm"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </NavLink>
          ))}
        </nav>
      </motion.aside>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        
        {/* TOP NAVBAR */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-background/80 backdrop-blur-md z-10">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold tracking-tight">{getPageTitle()}</h1>
            <div className="h-5 w-px bg-border mx-2"></div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              {!settingsError && <span className={`relative inline-flex h-2.5 w-2.5 shrink-0 rounded-full ${settings.isMonitoring ? 'bg-success' : 'bg-muted-foreground'}`} />}
              {settingsError ? 'Backend status unavailable' : settings.isMonitoring ? 'Host monitoring enabled' : 'Host monitoring idle'}
            </div>
          </div>

          <div className="flex items-center gap-4">
            <NavLink to="/situations" aria-label="Open Situation Room" title="Open Situation Room" className="relative p-2 rounded-full hover:bg-accent text-muted-foreground transition-colors">
              <Bell size={20} />
            </NavLink>
            <ThemeToggle />
            <button
              type="button"
              aria-label="Sign out"
              title="Sign out"
              onClick={async () => {
                try {
                  await logout();
                } catch {
                  window.alert('Server logout could not be confirmed. This browser session has been cleared.');
                } finally {
                  queryClient.clear();
                  navigate('/login', { replace: true });
                }
              }}
              className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <LogOut size={20} />
            </button>
          </div>
        </header>

        {/* PAGE CONTENT */}
        <main className="flex-1 overflow-auto bg-muted/20 relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>

      </div>
    </div>
  );
};
