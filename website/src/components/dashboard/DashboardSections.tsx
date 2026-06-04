import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Bot, Bell, Calendar, ChevronRight, HardHat, Sparkles, Truck, UtensilsCrossed,
  FileText, Plus, Users,
} from 'lucide-react';
import { formatCurrency, formatDate } from '../../api/client';
import type { Enquiry, Notification, Vendor, Worker } from '../../api/client';
import { orderRevenueEstimate, type ChartPeriod } from '../../utils/dashboardData';

const fade = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
};

export function GlassCard({
  children,
  className = '',
  title,
  action,
}: {
  children: React.ReactNode;
  className?: string;
  title?: string;
  action?: React.ReactNode;
}) {
  return (
    <motion.div
      {...fade}
      className={`rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow ${className}`}
    >
      {(title || action) && (
        <div className="flex items-center justify-between px-5 pt-5 pb-0">
          {title && <h3 className="text-sm font-semibold text-[var(--foreground)]">{title}</h3>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </motion.div>
  );
}

const PERIOD_LABELS: Record<ChartPeriod, string> = {
  weekly: 'Weekly',
  monthly: 'Monthly',
  yearly: 'Yearly',
};

export function ChartFilter({
  mode,
  onChange,
}: {
  mode: ChartPeriod;
  onChange: (m: ChartPeriod) => void;
}) {
  return (
    <div className="inline-flex p-1 rounded-xl bg-[var(--background-alt)] border border-[var(--border)]">
      {(['weekly', 'monthly', 'yearly'] as const).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            mode === m ? 'bg-[var(--primary)] text-white shadow-sm' : 'text-[var(--muted)] hover:text-[var(--foreground)]'
          }`}
        >
          {PERIOD_LABELS[m]}
        </button>
      ))}
    </div>
  );
}

export function RecentOrdersTable({ orders }: { orders: Enquiry[] }) {
  if (orders.length === 0) {
    return <p className="text-sm text-[var(--muted)] py-4">No converted orders yet.</p>;
  }
  return (
    <div className="overflow-auto max-h-80 -mx-1 rounded-xl border border-[var(--border)]">
      <table className="data-table w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)]">
            <th className="px-4 py-3 text-left">Customer</th>
            <th className="px-4 py-3 text-left">Event</th>
            <th className="px-4 py-3 text-left">Date</th>
            <th className="px-4 py-3 text-right">Est.</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} className="border-b border-[var(--border)] last:border-0">
              <td className="px-4 py-3 font-medium">
                <Link to={`/orders/${o.id}`} className="hover:text-[var(--primary)]">{o.customerName}</Link>
              </td>
              <td className="px-4 py-3 text-[var(--muted)]">{o.eventType}</td>
              <td className="px-4 py-3 text-[var(--muted)]">{formatDate(o.eventDate)}</td>
              <td className="px-4 py-3 text-right font-medium tabular-nums">{formatCurrency(orderRevenueEstimate(o))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function UpcomingEventsList({ events }: { events: Enquiry[] }) {
  if (events.length === 0) {
    return <p className="text-sm text-[var(--muted)]">No upcoming events scheduled.</p>;
  }
  return (
    <ul className="space-y-3">
      {events.map((e) => (
        <li key={e.id} className="flex gap-3 p-3 rounded-2xl bg-[var(--primary-light)]/60 border border-[var(--border)]">
          <div className="w-10 h-10 rounded-xl bg-[var(--card)] flex items-center justify-center shrink-0">
            <Calendar size={18} className="text-[var(--primary)]" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-medium text-sm truncate">{e.customerName}</p>
            <p className="text-xs text-[var(--muted)]">{e.eventType} · {e.guestCount} guests</p>
            <p className="text-xs text-[var(--primary)] mt-0.5">{formatDate(e.eventDate)}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function TopDishesList({ dishes }: { dishes: { name: string; qty: number }[] }) {
  if (dishes.length === 0) {
    return <p className="text-sm text-[var(--muted)]">Dish popularity appears after orders include menu items.</p>;
  }
  const max = dishes[0]?.qty ?? 1;
  return (
    <ul className="space-y-3">
      {dishes.map((d) => (
        <li key={d.name}>
          <div className="flex justify-between text-sm mb-1">
            <span className="font-medium truncate pr-2">{d.name}</span>
            <span className="text-[var(--muted)] shrink-0">{d.qty}</span>
          </div>
          <div className="h-2 rounded-full bg-[var(--background-alt)] overflow-hidden">
            <div className="h-full rounded-full bg-[var(--primary)] transition-all" style={{ width: `${(d.qty / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export function VendorPaymentsSummary({ vendors }: { vendors: Vendor[] }) {
  const list = vendors.slice(0, 5);
  if (list.length === 0) {
    return <p className="text-sm text-[var(--muted)]">Add vendors to track supplier relationships.</p>;
  }
  return (
    <ul className="space-y-2">
      {list.map((v) => (
        <li key={v.id} className="flex items-center justify-between py-2 border-b border-[var(--border)] last:border-0">
          <div className="flex items-center gap-2 min-w-0">
            <Truck size={16} className="text-[var(--primary)] shrink-0" />
            <span className="text-sm font-medium truncate">{v.businessName || v.name}</span>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--primary-light)] text-[var(--primary)]">{v.category}</span>
        </li>
      ))}
    </ul>
  );
}

export function WorkerAttendanceOverview({ workers, byRole }: { workers: Worker[]; byRole: Record<string, number> }) {
  return (
    <div>
      <p className="text-2xl font-bold text-[var(--foreground)] mb-1">{workers.length}</p>
      <p className="text-xs text-[var(--muted)] mb-4">workers on roster</p>
      <div className="flex flex-wrap gap-2 mb-4">
        {Object.entries(byRole).map(([role, n]) => (
          <span key={role} className="text-xs px-2 py-1 rounded-lg bg-[var(--background-alt)] border border-[var(--border)]">
            {role}: {n}
          </span>
        ))}
      </div>
      <ul className="space-y-2">
        {workers.map((w) => (
          <li key={w.id} className="flex items-center gap-2 text-sm">
            <HardHat size={14} className="text-[var(--accent)]" />
            <span className="font-medium">{w.name}</span>
            <span className="text-[var(--muted)] text-xs">· {w.role}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function QuickActionsPanel() {
  const actions = [
    { to: '/enquiries', label: 'Enquiries', icon: Users },
    { to: '/orders', label: 'New order', icon: Plus },
    { to: '/invoices', label: 'Upload bill', icon: FileText },
    { to: '/dishes', label: 'Menu', icon: UtensilsCrossed },
    { to: '/ai-assistant', label: 'AI Assistant', icon: Bot },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
      {actions.map(({ to, label, icon: Icon }) => (
        <Link
          key={to}
          to={to}
          className="flex flex-col items-center gap-2 p-4 rounded-2xl border border-[var(--border)] bg-[var(--background-alt)]/50 hover:bg-[var(--primary-light)] hover:border-[var(--primary)] transition-all text-center"
        >
          <Icon size={20} className="text-[var(--primary)]" />
          <span className="text-xs font-semibold">{label}</span>
        </Link>
      ))}
    </div>
  );
}

export function NotificationsWidget({ items }: { items: Notification[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-[var(--muted)]">No new notifications.</p>;
  }
  return (
    <ul className="space-y-3 max-h-48 overflow-y-auto">
      {items.map((n) => (
        <li key={n.id} className="flex gap-2 text-sm border-b border-[var(--border)] pb-3 last:border-0">
          <Bell size={16} className="text-[var(--accent)] shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">{n.title}</p>
            <p className="text-[var(--muted)] text-xs line-clamp-2">{n.message}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function AiInsightsPanel({ insights }: { insights: string[] }) {
  return (
    <div className="glass-panel rounded-[var(--radius-xl)] p-5 border border-[var(--border)]">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[var(--primary)] to-[var(--accent)] flex items-center justify-center">
          <Sparkles size={18} className="text-white" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">AI Business Assistant</h3>
          <p className="text-xs text-[var(--muted)]">Smart recommendations</p>
        </div>
        <Link to="/ai-assistant" className="ml-auto text-xs font-medium text-[var(--primary)] hover:underline flex items-center gap-0.5">
          Open <ChevronRight size={14} />
        </Link>
      </div>
      <ul className="space-y-3">
        {insights.map((text, i) => (
          <li key={i} className="text-sm text-[var(--foreground)] leading-relaxed pl-3 border-l-2 border-[var(--accent)]">
            {text}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function TodaysEventsWidget({ events }: { events: Enquiry[] }) {
  if (events.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)] py-2">No events scheduled for today.</p>
    );
  }
  return (
    <ul className="space-y-2">
      {events.map((e) => (
        <li key={e.id} className="text-sm p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--border)]">
          <span className="font-semibold">{e.customerName}</span>
          <span className="text-[var(--muted)]"> — {e.eventType}, {e.guestCount} pax</span>
        </li>
      ))}
    </ul>
  );
}
