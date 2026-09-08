import {
  BarChart3,
  Grid3x3,
  LineChart,
  LogOut,
  Menu,
  PackageCheck,
  Sunrise,
} from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';
import { DriftBanner } from '@/components/DriftBanner';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';
import { useUiStore } from '@/store/ui';

const NAV_ITEMS = [
  { to: '/', label: 'Morning Brief', icon: Sunrise, end: true },
  { to: '/forecast', label: 'Forecast Explorer', icon: LineChart, end: false },
  { to: '/inventory', label: 'Inventory Engine', icon: PackageCheck, end: false },
  { to: '/monitor', label: 'Model Monitor', icon: BarChart3, end: false },
  { to: '/analytics', label: 'Store Analytics', icon: Grid3x3, end: false },
];

export function Layout() {
  const { user, logout } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUiStore();

  return (
    <div className="flex h-full min-h-screen bg-slate-50">
      <aside
        aria-label="Main navigation"
        className={cn(
          'fixed inset-y-0 left-0 z-40 w-64 shrink-0 bg-navy text-slate-100 transition-transform md:static md:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center gap-2 border-b border-white/10 px-6">
          <span className="h-3 w-3 rounded-full bg-teal" aria-hidden />
          <span className="text-lg font-semibold tracking-tight">ForecastIQ</span>
        </div>
        <nav className="flex flex-col gap-1 p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => sidebarOpen && toggleSidebar()}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive ? 'bg-teal text-white' : 'text-slate-300 hover:bg-white/10',
                )
              }
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 w-full border-t border-white/10 p-4 text-xs text-slate-300">
          <p className="font-semibold text-white">{user?.full_name}</p>
          <p className="capitalize">{user?.role.replace('_', ' ')}</p>
          {user?.store_nbr ? <p>Store #{user.store_nbr}</p> : null}
          <Button variant="ghost" size="sm" className="mt-3 w-full text-slate-200 hover:bg-white/10" onClick={logout}>
            <LogOut className="h-4 w-4" aria-hidden /> Sign out
          </Button>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 items-center gap-3 border-b border-slate-200 bg-white px-4 md:px-6">
          <Button
            variant="ghost"
            size="sm"
            className="md:hidden"
            aria-label="Toggle navigation"
            onClick={toggleSidebar}
          >
            <Menu className="h-5 w-5" aria-hidden />
          </Button>
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Corporacion Favorita</p>
            <p className="text-sm font-semibold text-navy">Retail Demand Intelligence</p>
          </div>
        </header>
        <DriftBanner />
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
