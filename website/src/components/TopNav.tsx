import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, Moon, Plus, Search, Sun } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { useTheme } from '../context/ThemeContext';
import { getUnreadNotifications } from '../utils/dashboardData';

export function TopNav() {
  const { notifications, stats } = useAppData();
  const { theme, toggleTheme } = useTheme();
  const [search, setSearch] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);

  const unread = getUnreadNotifications(notifications);

  return (
    <header className="sticky top-0 z-30 mb-6 -mx-1 px-1">
      <div className="flex flex-wrap items-center gap-3 py-3 px-4 rounded-[var(--radius-xl)] bg-[var(--card)] border border-[var(--border)] shadow-[var(--shadow-sm)]">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)] pointer-events-none" />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search enquiries, orders, dishes…"
            className="form-input w-full pl-10 pr-4 py-2.5 rounded-xl text-sm"
          />
        </div>

        <div className="flex items-center gap-2 ml-auto">
          <div className="relative">
            <button
              type="button"
              onClick={() => { setCreateOpen((o) => !o); setNotifOpen(false); }}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[var(--primary)] text-white text-sm font-semibold hover:bg-[var(--primary-hover)] transition-colors shadow-sm"
            >
              <Plus size={18} />
              <span className="hidden sm:inline">Create</span>
            </button>
            {createOpen && (
              <div className="absolute right-0 mt-2 w-48 py-2 rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-[var(--shadow-md)] z-50">
                <Link to="/enquiries" className="block px-4 py-2 text-sm hover:bg-[var(--sidebar-hover)]" onClick={() => setCreateOpen(false)}>New enquiry</Link>
                <Link to="/orders" className="block px-4 py-2 text-sm hover:bg-[var(--sidebar-hover)]" onClick={() => setCreateOpen(false)}>View orders</Link>
                <Link to="/invoices" className="block px-4 py-2 text-sm hover:bg-[var(--sidebar-hover)]" onClick={() => setCreateOpen(false)}>Upload invoice</Link>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            className="p-2.5 rounded-xl border border-[var(--border)] hover:bg-[var(--sidebar-hover)] transition-colors"
            aria-label="Toggle theme"
          >
            {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
          </button>

          <div className="relative">
            <button
              type="button"
              onClick={() => { setNotifOpen((o) => !o); setCreateOpen(false); }}
              className="relative p-2.5 rounded-xl border border-[var(--border)] hover:bg-[var(--sidebar-hover)] transition-colors"
            >
              <Bell size={18} />
              {(stats?.unread_notifications ?? 0) > 0 && (
                <span className="absolute -top-0.5 -right-0.5 w-4 h-4 text-[10px] font-bold rounded-full bg-[var(--accent)] text-[var(--sidebar-badge-text)] flex items-center justify-center">
                  {stats!.unread_notifications! > 9 ? '9+' : stats!.unread_notifications}
                </span>
              )}
            </button>
            {notifOpen && (
              <div className="absolute right-0 mt-2 w-80 max-h-72 overflow-y-auto rounded-xl bg-[var(--card)] border border-[var(--border)] shadow-[var(--shadow-md)] z-50">
                <p className="px-4 py-3 text-xs font-semibold text-[var(--muted)] border-b border-[var(--border)]">Notifications</p>
                {unread.length === 0 ? (
                  <p className="px-4 py-6 text-sm text-[var(--muted)]">No new notifications</p>
                ) : (
                  unread.map((n) => (
                    <div key={n.id} className="px-4 py-3 border-b border-[var(--border)] last:border-0 text-sm">
                      <p className="font-medium">{n.title}</p>
                      <p className="text-xs text-[var(--muted)] mt-0.5 line-clamp-2">{n.message}</p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
