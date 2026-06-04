import { NavLink, Outlet } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard, MessageSquare, ShoppingBag, UtensilsCrossed, Users,
  HardHat, FileText, BarChart3, Bot, Settings, MessageCircle, Moon, Sun,
} from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useTheme } from '../context/ThemeContext';
import { BrandLogo } from './BrandLogo';
import { FloatingActionButton } from './FloatingActionButton';

const SIDEBAR_WIDTH = '16.5rem';

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
  { to: '/dishes', label: 'Dishes', icon: UtensilsCrossed, badge: (d) => d.stats?.total_dishes },
  { to: '/vendors', label: 'Vendors', icon: Users, badge: (d) => d.vendors.length },
  { to: '/workers', label: 'Workers', icon: HardHat, badge: (d) => d.workers.length },
  { to: '/invoices', label: 'Invoices', icon: FileText },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/ai-assistant', label: 'AI Assistant', icon: Bot },
  { to: '/bot-tester', label: 'Bot Tester', icon: MessageCircle },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export function DashboardLayout() {
  const data = useAppData();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen">
      <aside
        className="fixed left-0 top-0 h-screen flex flex-col z-20 m-3 rounded-[var(--radius-xl)] glass-panel shadow-[var(--shadow-md)]"
        style={{ width: `calc(${SIDEBAR_WIDTH} - 24px)` }}
      >
        <div className="shrink-0 p-3 border-b border-[var(--sidebar-border)]">
          <BrandLogo variant="sidebar" />
        </div>
        <nav className="flex-1 overflow-y-auto py-2 px-2">
          {navItems.map(({ to, label, icon: Icon, badge }) => {
            const count = badge?.(data);
            return (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `relative flex items-center justify-between gap-2 px-3 py-2.5 text-sm font-medium transition-all rounded-full mb-1 ${
                    isActive
                      ? 'bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] shadow-sm'
                      : 'text-[var(--sidebar-foreground)] hover:bg-[var(--sidebar-hover)]'
                  }`
                }
              >
                <span className="flex items-center gap-3 min-w-0">
                  <Icon size={18} className="shrink-0" />
                  <span className="truncate">{label}</span>
                </span>
                {count != null && count > 0 && (
                  <span className="px-2 py-0.5 text-[10px] rounded-full bg-[var(--sidebar-badge-bg)] text-[var(--sidebar-badge-text)] font-bold min-w-[1.1rem] text-center shrink-0">
                    {count}
                  </span>
                )}
              </NavLink>
            );
          })}
        </nav>
        <div className="shrink-0 p-3 border-t border-[var(--sidebar-border)] flex items-center justify-between">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex items-center gap-2 px-3 py-2 rounded-full text-xs font-medium text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] transition-colors"
          >
            {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
            {theme === 'light' ? 'Dark' : 'Light'}
          </button>
        </div>
      </aside>
      <main
        className="flex-1 min-h-screen px-4 py-4 md:px-6 md:py-6"
        style={{ marginLeft: SIDEBAR_WIDTH, background: 'var(--background)' }}
      >
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.25 }}>
          <Outlet />
        </motion.div>
      </main>
      <FloatingActionButton />
    </div>
  );
}

export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-[var(--foreground)] tracking-tight">{title}</h1>
      {description && <p className="text-[var(--muted)] mt-1 text-sm">{description}</p>}
    </div>
  );
}

export function StatCard({ label, value, subtext }: { label: string; value: string; subtext?: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-5 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-all">
      <p className="text-sm text-[var(--muted)]">{label}</p>
      <p className="text-2xl font-bold mt-2 text-[var(--primary)]">{value}</p>
      {subtext && <p className="text-xs text-[var(--muted)] mt-1">{subtext}</p>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] p-12 text-center text-[var(--muted)] shadow-[var(--shadow-sm)]">
      {message}
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
