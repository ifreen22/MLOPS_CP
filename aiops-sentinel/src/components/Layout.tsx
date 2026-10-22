import { NavLink, Outlet } from 'react-router-dom';
import { useGlobalStore } from '../store/useGlobalStore';

export default function Layout() {
  const activeSituationId = useGlobalStore((state) => state.activeSituationId);

  return (
    <div className="bg-surface-container-lowest font-body-md text-on-surface antialiased flex h-screen overflow-hidden">
      {/* SIDEBAR */}
      <aside className="w-[240px] bg-surface-container-low border-r border-outline-variant z-50 flex flex-col justify-between select-none shrink-0">
        <div className="flex flex-col">
          <div className="h-16 px-space-md border-b border-outline-variant flex items-center justify-between bg-surface-container-lowest">
            <div className="flex items-center gap-space-sm min-w-0">
              <img alt="AIOps Sentinel Logo" className="h-8 w-auto object-contain" src="https://lh3.googleusercontent.com/aida/AEtjO1XDGmcy3WtIcLAx1AD5IllaWrF7gwSsES262mLaLbgGeLbq09tI83Duka1mCCUws63xA0bg-B19npezPq4ykdy2n8cyngnPmINQ0oCA-KXlV8ZAnCoF8wgGXNqjfvNSAvo8BZTinR-g5528hpsA7vGsfpb4BOpGWMEwL-nxXg-lK4tDAnzVTxVOJCchzWjmtoM7jHibFLqsgW11PxyxBT1Ee-mvcGcPMVTHZDSgErTrsRtXMFFgciGa" />
              <div className="flex flex-col min-w-0">
                <span className="font-headline-sm text-on-surface font-semibold tracking-wider uppercase truncate text-[0.8125rem] leading-tight">Sentinel</span>
                <span className="font-label-code-sm text-outline tracking-wider uppercase text-[0.625rem]">AIOps Core</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-space-xs py-0.5 rounded-DEFAULT bg-secondary/10 border border-secondary/20">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>
              <span className="font-label-code-sm text-secondary uppercase text-[0.5625rem] tracking-wider font-bold">LOCAL</span>
            </div>
          </div>
          <div className="px-space-md py-space-xs border-b border-outline-variant/40 bg-surface-container-low/50">
            <span className="font-label-code-sm text-outline uppercase tracking-wider text-[0.625rem]">Mission Topology</span>
          </div>
          <nav className="flex flex-col py-space-xs px-space-xs gap-0.5">
            <NavLink to="/" className={({ isActive }) => `flex items-center justify-between px-space-sm py-2 rounded-DEFAULT transition-colors ${isActive ? 'bg-surface-container-high text-primary border-l-2 border-primary-container font-medium' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}`}>
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[18px]">dashboard</span>
                <span className="font-body-md text-[0.8125rem]">Mission Control</span>
              </div>
            </NavLink>
            <NavLink to="/situation-room" className={({ isActive }) => `flex items-center justify-between px-space-sm py-2 rounded-DEFAULT transition-colors ${isActive ? 'bg-surface-container-high text-primary border-l-2 border-primary-container font-medium' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}`}>
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[18px]">radar</span>
                <span className="font-body-md text-[0.8125rem]">Situation Room</span>
              </div>
              {activeSituationId && (
                <span className="px-1.5 py-0.5 rounded-DEFAULT bg-error-container text-on-error-container font-label-code-sm text-[0.625rem] font-bold border border-error/30">1 Sev1</span>
              )}
            </NavLink>
            <NavLink to="/graph-explorer" className={({ isActive }) => `flex items-center justify-between px-space-sm py-2 rounded-DEFAULT transition-colors ${isActive ? 'bg-surface-container-high text-primary border-l-2 border-primary-container font-medium' : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'}`}>
              <div className="flex items-center gap-space-sm">
                <span className="material-symbols-outlined text-[18px]">hub</span>
                <span className="font-body-md text-[0.8125rem]">Graph Explorer</span>
              </div>
            </NavLink>
          </nav>
        </div>
        <div className="p-space-sm border-t border-outline-variant bg-surface-container-lowest/80 flex flex-col gap-space-xs">
          <div className="p-space-xs rounded-DEFAULT bg-surface-container border border-outline-variant/60 flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="font-label-code-sm text-outline text-[0.625rem] uppercase">Target Cluster</span>
              <span className="font-label-code-sm text-secondary text-[0.6875rem] font-bold flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>18ms
              </span>
            </div>
            <div className="font-label-code-md text-on-surface text-[0.6875rem] truncate">prod-us-east-k8s</div>
          </div>
          <div className="pt-space-xs border-t border-outline-variant/40 flex items-center justify-between">
            <div className="flex items-center gap-space-xs min-w-0">
              <div className="w-7 h-7 rounded-full bg-primary-container text-on-primary-container flex items-center justify-center font-label-code-sm font-bold text-[0.6875rem] shrink-0">SC</div>
              <div className="flex flex-col min-w-0">
                <span className="font-body-sm text-on-surface text-[0.6875rem] font-medium truncate">sarah.chen</span>
                <span className="font-label-code-sm text-outline text-[0.5625rem] truncate">Shift → 08:00 UTC</span>
              </div>
            </div>
            <div className="w-2 h-2 rounded-full bg-secondary" title="On-Call Active"></div>
          </div>
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        {/* HEADER */}
        <header className="h-16 bg-surface-container-low border-b border-outline-variant z-40 px-space-lg flex items-center justify-between gap-space-md shrink-0">
          <div className="flex items-center gap-space-md">
            <div className="flex items-center gap-space-xs font-label-code-md text-on-surface-variant text-[0.75rem]">
              <span className="text-outline">Cluster:</span>
              <span className="text-primary font-semibold">prod-core-01</span>
              <span className="text-outline-variant">/</span>
              <span className="text-outline">Region:</span>
              <span className="text-on-surface">us-east-1</span>
            </div>
          </div>
          <div className="w-[380px] relative">
            <div className="absolute inset-y-0 left-0 pl-space-sm flex items-center pointer-events-none">
              <span className="material-symbols-outlined text-outline text-[16px]">search</span>
            </div>
            <input className="w-full bg-surface-container-lowest border border-outline-variant rounded-DEFAULT pl-8 pr-12 py-1.5 font-label-code-sm text-on-surface placeholder:text-outline/70 focus:outline-none focus:border-primary-container text-[0.6875rem]" placeholder="Search situations, services, traces, pods..." readOnly type="text" />
            <div className="absolute inset-y-0 right-0 pr-space-xs flex items-center pointer-events-none">
              <kbd className="px-1.5 py-0.5 rounded-DEFAULT bg-surface-container-high border border-outline-variant font-label-code-sm text-outline text-[0.5625rem]">⌘K</kbd>
            </div>
          </div>
          <div className="flex items-center gap-space-md shrink-0">
            <div className="flex items-center gap-space-xs px-space-sm py-1 rounded-DEFAULT bg-surface-container border border-outline-variant">
              <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
              <span className="font-label-code-sm text-outline text-[0.6875rem]">Telemetry:</span>
              <span className="font-label-code-sm text-on-surface font-semibold text-[0.6875rem]">2.4M evt/s</span>
            </div>
            <div className="flex items-center gap-1 px-space-xs py-1 rounded-DEFAULT bg-surface-container border border-outline-variant font-label-code-sm text-on-surface text-[0.6875rem]">
              <span className="material-symbols-outlined text-[16px] text-outline">schedule</span>
              <span>Last 15m</span>
            </div>
            <button className="relative p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded-DEFAULT transition-colors">
              <span className="material-symbols-outlined text-[20px]">notifications</span>
              <span className="absolute top-1 right-1 w-2 h-2 bg-error rounded-full ring-2 ring-surface-container-low"></span>
            </button>
            <div className="flex items-center gap-space-xs pl-space-xs border-l border-outline-variant">
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
              </div>
            </div>
          </div>
        </header>

        {/* PAGE CONTENT */}
        <main className="flex-1 overflow-y-auto bg-surface-container-lowest text-on-surface w-full relative">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
