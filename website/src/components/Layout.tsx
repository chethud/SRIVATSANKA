import { NavLink, Outlet, useLocation } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard, MessageSquare, ShoppingBag, UtensilsCrossed, Users,
  HardHat, FileText, BarChart3, Settings,
  PanelLeftClose, PanelLeft, LogOut, X, Menu,
} from 'lucide-react';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppData } from '../context/AppDataContext';
import { useAuth } from '../context/AuthContext';
import { CreateActionProvider } from '../context/CreateActionContext';
import { LayoutProvider, SIDEBAR_EXPANDED, useLayout } from '../context/LayoutContext';
import { PageSearchProvider } from '../context/PageSearchContext';
import { BrandLogo } from './BrandLogo';
import { TopNav } from './TopNav';
import { AIChatWidget } from './AIChatWidget';
import { WhatsAppIcon } from './WhatsAppIcon';

type AppDataSlice = ReturnType<typeof useAppData>;

type NavIcon = LucideIcon | typeof WhatsAppIcon;

const navItems: {
  to: string;
  label: string;
  icon: NavIcon;
  badge?: (d: AppDataSlice) => number | null | undefined;
}[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/enquiries', label: 'Enquiries', icon: MessageSquare, badge: (d) => d.stats?.new_enquiries },
  { to: '/orders', label: 'Orders', icon: ShoppingBag, badge: (d) => d.stats?.new_orders },
  { to: '/dishes', label: 'Menu', icon: UtensilsCrossed },
  { to: '/vendors', label: 'Vendors', icon: Users },
  { to: '/workers', label: 'Workers', icon: HardHat },
  { to: '/invoices', label: 'Expenses Invoice', icon: FileText },
  { to: '/bot-tester', label: 'WhatsApp Chats', icon: WhatsAppIcon },
  { to: '/settings', label: 'Settings', icon: Settings },
];

function DashboardLayoutInner() {
  const data = useAppData();
  const {
    sidebarCollapsed,
    toggleSidebar,
    sidebarWidth,
    isMobileNav,
    mobileNavOpen,
    closeMobileNav,
    openMobileNav,
  } = useLayout();
  const location = useLocation();
  const navigate = useNavigate();
  const { logout, username } = useAuth();

  const railCollapsed = !isMobileNav && sidebarCollapsed;
  const asideWidth = isMobileNav ? SIDEBAR_EXPANDED : sidebarWidth;

  useEffect(() => {
    closeMobileNav();
  }, [location.pathname, closeMobileNav]);

  useEffect(() => {
    if (!mobileNavOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') closeMobileNav();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [mobileNavOpen, closeMobileNav]);

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  const isWhatsAppChat =
    location.pathname === '/bot-tester' || location.pathname.startsWith('/bot-tester/');

  return (
    <div className="flex min-h-screen bg-[var(--background)]">
      {isMobileNav && mobileNavOpen && (
        <button
          type="button"
          className="sidebar-overlay"
          aria-label="Close navigation"
          onClick={closeMobileNav}
        />
      )}

      <aside
        className={`app-sidebar fixed left-0 top-0 h-dvh flex flex-col z-40 border-r border-[var(--sidebar-border)] bg-[var(--sidebar-bg)] shadow-[var(--shadow-sm)] ${
          isMobileNav ? (mobileNavOpen ? 'app-sidebar--open' : 'app-sidebar--closed') : ''
        }`}
        style={{ width: asideWidth }}
        aria-hidden={isMobileNav && !mobileNavOpen}
      >
        <div className="shrink-0 flex items-center justify-between border-b border-[var(--sidebar-border)] px-2 min-h-[3.5rem]">
          <BrandLogo variant="sidebar" />
          {isMobileNav && (
            <button
              type="button"
              onClick={closeMobileNav}
              className="topnav__icon-btn mr-1"
              aria-label="Close menu"
            >
              <X size={18} />
            </button>
          )}
        </div>

        <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 px-2 space-y-0.5 overscroll-contain">
          {navItems.map(({ to, label, icon: Icon, badge }) => {
            const count = badge?.(data);
            return (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                title={railCollapsed ? label : undefined}
                onClick={() => {
                  if (isMobileNav) closeMobileNav();
                }}
                className={({ isActive }) =>
                  `group relative flex items-center gap-3 px-3 py-3 text-sm font-medium rounded-xl transition-all duration-200 min-h-[2.75rem] ${
                    railCollapsed ? 'justify-center' : ''
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
                    {!railCollapsed && <span className="truncate">{label}</span>}
                    {!railCollapsed && count != null && count > 0 && (
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

        <div className="shrink-0 p-2 border-t border-[var(--sidebar-border)] space-y-1 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
          {!railCollapsed && username && (
            <p className="px-3 py-1 text-[10px] text-[var(--sidebar-muted)] truncate" title={username}>
              Signed in as {username}
            </p>
          )}
          <button
            type="button"
            onClick={handleLogout}
            className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] transition-colors min-h-[2.75rem] ${
              railCollapsed ? 'justify-center' : ''
            }`}
            title="Sign out"
          >
            <LogOut size={18} />
            {!railCollapsed && <span>Sign out</span>}
          </button>
          {!isMobileNav && (
            <button
              type="button"
              onClick={toggleSidebar}
              className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-sm text-[var(--sidebar-muted)] hover:bg-[var(--sidebar-hover)] transition-colors min-h-[2.75rem] ${
                railCollapsed ? 'justify-center' : ''
              }`}
            >
              {sidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
              {!railCollapsed && <span>Collapse</span>}
            </button>
          )}
        </div>
      </aside>

      <main
        className={`flex-1 flex flex-col min-w-0 ${
          isWhatsAppChat
            ? 'h-dvh max-h-dvh p-0 overflow-hidden'
            : 'min-h-screen px-3 py-3 sm:px-4 sm:py-4 md:px-6 lg:px-8'
        }`}
        style={{ marginLeft: isMobileNav ? 0 : sidebarWidth }}
      >
        {!isWhatsAppChat && (
          <div className="topnav-root">
            <TopNav />
          </div>
        )}
        {isWhatsAppChat && isMobileNav && (
          <button
            type="button"
            onClick={openMobileNav}
            className="wa-mobile-menu-btn"
            aria-label="Open menu"
          >
            <Menu size={18} />
          </button>
        )}
        <div
          className={
            isWhatsAppChat
              ? 'flex-1 min-h-0 h-full flex flex-col overflow-hidden'
              : undefined
          }
        >
          <Outlet />
        </div>
        {!isWhatsAppChat && <AIChatWidget />}
      </main>
    </div>
  );
}

export function DashboardLayout() {
  return (
    <LayoutProvider>
      <CreateActionProvider>
        <PageSearchProvider>
          <DashboardLayoutInner />
        </PageSearchProvider>
      </CreateActionProvider>
    </LayoutProvider>
  );
}

export function PageHeader({ title, description }: { title: string; description?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-xl sm:text-2xl font-semibold text-[var(--foreground)] tracking-tight">{title}</h1>
      {description && <p className="text-[var(--muted)] mt-1.5 text-sm max-w-2xl">{description}</p>}
    </div>
  );
}

export function StatCard({
  label,
  value,
  subtext,
  onClick,
}: {
  label: string;
  value: string;
  subtext?: string;
  onClick?: () => void;
}) {
  const interactive = Boolean(onClick);
  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        interactive
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={`bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-lg)] p-4 sm:p-5 shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow min-w-0 overflow-hidden h-auto self-start ${
        interactive ? 'cursor-pointer hover:border-[var(--primary)]/40 focus:outline-none focus:ring-2 focus:ring-[var(--primary)]/30' : ''
      }`}
    >
      <p className="text-xs font-medium text-[var(--muted)] uppercase tracking-wide">{label}</p>
      <p className="text-xl sm:text-2xl font-semibold mt-2 text-[var(--primary)] tabular-nums break-words">{value}</p>
      {subtext && <p className="text-xs text-[var(--muted)] mt-1">{subtext}</p>}
      {interactive && <p className="text-xs text-[var(--primary)] mt-2 font-medium">View all →</p>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] p-8 sm:p-12 text-center text-[var(--muted)] shadow-[var(--shadow-sm)]">
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
      className={`px-4 py-2.5 min-h-[2.75rem] bg-[var(--primary)] text-white rounded-xl text-sm font-semibold hover:bg-[var(--primary-hover)] transition-colors disabled:opacity-50 shadow-sm ${className}`}
    >
      {children}
    </button>
  );
}

export function Card({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
  return (
    <div id={id} className={`bg-[var(--card)] border border-[var(--border)] rounded-[var(--radius-xl)] shadow-[var(--shadow-sm)] min-w-0 h-auto self-start ${className}`}>
      {children}
    </div>
  );
}
