import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  LayoutDashboard, MessageSquare, ShoppingBag, UtensilsCrossed, Users,
  HardHat, FileText, BarChart3, Bot, Settings, MessageCircle,
  PanelLeftClose, PanelLeft, Moon, Sun,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useTheme } from '../context/ThemeContext';
import { CreateActionProvider } from '../context/CreateActionContext';
import { LayoutProvider, useLayout } from '../context/LayoutContext';
import { BrandLogo } from './BrandLogo';
import { TopNav } from './TopNav';

type AppDataSlice = ReturnType<typeof useAppData>;

const navItems: {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: (d: AppDataSlice) => number | null | undefined;
}[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/enquiries', label: 'Enquiries', icon: MessageSquare, badge: (d) => d.stats?.new_enquiries },
  { to: '/orders', label: 'Orders', icon: ShoppingBag, badge: (d) => d.enquiries.filter((e) => e.status === 'CONVERTED').length },
  { to: '/dishes', label: 'Cuisine', icon: UtensilsCrossed, badge: (d) => d.stats?.total_dishes },
  { to: '/vendors', label: 'Vendors', icon: Users, badge: (d) => d.vendors.length },
  { to: '/workers', label: 'Workers', icon: HardHat, badge: (d) => d.workers.length },
  { to: '/invoices', label: 'Invoices', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/ai-assistant', label: 'AI Assistant', icon: Bot },
  { to: '/bot-tester', label: 'Bot Tester', icon: MessageCircle },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function DashboardLayoutInner() {
  const data = useAppData();
  const { theme, toggleTheme } = useTheme();
  const { sidebarCollapsed, toggleSidebar, sidebarWidth } = useLayout();
  const location = useLocation();

  return (
    <div className="flex min-h-screen bg-[var(--background)]">
      <motion.aside
        layout
        className="fixed left-0 top-0 h-screen flex flex-col z-20 border-r border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] shadow-[var(--shadow-sm)]"
        style={{ width: sidebarWidth }}
        transition={{ type: 'spring', stiffness: 380, damping: 32 }}
      >
        <div className="shrink-0 flex items-center border-b border-[var(--sidebar-border)] px-2">
          <BrandLogo variant="sidebar" />
        </div>

        <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 px-2 space-y-0.5">
          {navItems.map(({ to, label, icon: Icon, badge }) => {
            const count = badge?.(data);
            return (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                title={sidebarCollapsed ? label : undefined}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 ${
                    sidebarCollapsed ? 'justify-center' : ''
                  } ${
                    isActive
                      ? 'bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] shadow-sm'
                      : 'text-[var(--sidebar-foreground)] hover:bg-[var(--sidebar-hover)]'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-[var(--sidebar-active-indicator)]" />
                    )}
                    <Icon size={18} className="shrink-0 opacity-90" />
                    {!sidebarCollapsed && <span className="truncate">{label}</span>}
                    {!sidebarCollapsed && count != null && count > 0 && (
                      <span className="ml-auto px-2 py-0.5 text-[10px] font-bold rounded-md bg-[var(--sidebar-badge-bg)] text-[var(--sidebar-badge-text)] tabular-nums">
                        {count > 99 ? '99+' : count}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>

        <div className="shrink-0 p-2 border-t border-[var(--sidebar-border)] space-y-1">
          <button
            type="button"
            onClick={toggleTheme}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] transition-colors ${
              sidebarCollapsed ? 'justify-center' : ''
            }`}
            title={theme === 'light' ? 'Dark mode' : 'Light mode'}
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
            {!sidebarCollapsed && <span>{theme === 'light' ? 'Dark mode' : 'Light mode'}</span>}
          </button>
          <button
            type="button"
            onClick={toggleSidebar}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] transition-colors ${
              sidebarCollapsed ? 'justify-center' : ''
            }`}
          >
            {sidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
            {!sidebarCollapsed && <span>Collapse</span>}
          </button>
        </div>
      </motion.aside>

      <motion.main
        layout
        className="flex-1 min-h-screen px-4 py-4 md:px-6 lg:px-8"
        style={{ marginLeft: sidebarWidth }}
        transition={{ type: 'spring', stiffness: 380, damping: 32 }}
      >
        <div className="topnav-root">
          <TopNav />
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </motion.main>
    </div>
  );
}

export function DashboardLayout() {
  return (
    <LayoutProvider>
      <CreateActionProvider>
        <DashboardLayoutInner />
      </CreateActionProvider>
    </LayoutProvider>
  );
}

export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-semibold text-[var(--foreground)] tracking-tight">{title}</h1>
      {description && <p className="text-[var(--muted)] mt-1.5 text-sm max-w-2xl">{description}</p>}
    </div>
  );
}

export function StatCard({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow">
      <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold mt-2 text-[var(--primary)] tabular-nums">{value}</p>
      {subtext && <p className="text-xs text-[var(--muted)] mt-1">{subtext}</p>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] p-12 text-center text-[var(--muted)] shadow-[var(--shadow-sm)]">
      <p className="text-sm">{message}</p>
    </div>
  );
}

export function Button({ children, type = 'button', onClick, className = '', disabled }: {
  children: React.ReactNode; type?: 'button' | 'submit'; onClick?: () => void; className?: string; disabled?: boolean;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`px-4 py-2.5 bg-[var(--primary)] text-white rounded-xl text-sm font-semibold hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50 shadow-sm ${className}`}
    >
      {children}
    </button>
  );
}

export function Card({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
  return (
    <div id={id} className={`bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] shadow-[var(--shadow-sm)] ${className}`}>
      {children}
    </div>
  );
}
