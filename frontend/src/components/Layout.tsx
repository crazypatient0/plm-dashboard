import { NavLink, Outlet } from 'react-router-dom';
import {
  DashboardIcon,
  PartsIcon,
  FileIcon,
  LayersIcon,
  SearchIcon,
  ClockIcon,
  ListIcon,
  SettingsIcon,
} from '../icons';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: DashboardIcon },
  { to: '/parts', label: 'Parts', icon: PartsIcon },
  { to: '/documents', label: 'Documents', icon: FileIcon },
  { to: '/conversion', label: 'Conversion', icon: LayersIcon },
  { to: '/scraper', label: 'Scraper', icon: SearchIcon },
  { to: '/scheduler', label: 'Scheduler', icon: ClockIcon },
  { to: '/logs', label: 'Logs', icon: ListIcon },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
];

export default function Layout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="sidebar-logo">PLM</span>
          <div className="sidebar-title">
            Dashboard
            <small>Monitoring Console</small>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `sidebar-link${isActive ? ' active' : ''}`
                }
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <div className="status-indicator">
            <span className="status-dot" />
            <span>System Nominal</span>
          </div>
          <span className="text-muted text-sm">v0.1.0</span>
        </div>
      </aside>
      <div className="main-area">
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
