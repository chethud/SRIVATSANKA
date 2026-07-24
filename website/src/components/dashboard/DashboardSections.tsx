import { Link } from 'react-router-dom';
import { useState } from 'react';
import {
  Bell, Calendar, HardHat, Sparkles,
} from 'lucide-react';
import { formatDate, updateEnquiryStatus } from '../../api/client';
import type { Enquiry, Notification, Worker } from '../../api/client';
import type { ChartPeriod } from '../../utils/dashboardData';
import { ENQUIRY_STATUS_FILTERS, statusOptionsForDropdown } from '../../utils/enquiryStatus';

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
    <div
      className={`rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-sm)] hover:shadow-[var(--shadow-md)] transition-shadow ${className}`}
    >
      {(title || action) && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 sm:px-5 pt-4 sm:pt-5 pb-0">
          {title && <h3 className="text-sm font-semibold text-[var(--foreground)] min-w-0">{title}</h3>}
          {action && <div className="min-w-0 shrink-0">{action}</div>}
        </div>
      )}
      <div className="p-4 sm:p-5">{children}</div>
    </div>
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

export type DashboardTab = 'overview' | 'enquiries' | 'partial-payments';

export function DashboardTabBar({
  tab,
  onChange,
  newEnquiries,
  partialCount = 0,
}: {
  tab: DashboardTab;
  onChange: (tab: DashboardTab) => void;
  newEnquiries: number;
  partialCount?: number;
}) {
  return (
    <div className="inline-flex flex-wrap p-1 rounded-xl bg-[var(--background-alt)] border border-[var(--border)]">
      <button
        type="button"
        onClick={() => onChange('overview')}
        className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
          tab === 'overview' ? 'bg-[var(--primary)] text-white shadow-sm' : 'text-[var(--muted)] hover:text-[var(--foreground)]'
        }`}
      >
        Overview
      </button>
      <button
        type="button"
        onClick={() => onChange('enquiries')}
        className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all inline-flex items-center gap-2 ${
          tab === 'enquiries' ? 'bg-[var(--primary)] text-white shadow-sm' : 'text-[var(--muted)] hover:text-[var(--foreground)]'
        }`}
      >
        Enquiries
        {newEnquiries > 0 && (
          <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-md bg-white/20 tabular-nums">
            {newEnquiries > 99 ? '99+' : newEnquiries}
          </span>
        )}
      </button>
      <button
        type="button"
        onClick={() => onChange('partial-payments')}
        className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all inline-flex items-center gap-2 ${
          tab === 'partial-payments' ? 'bg-[var(--primary)] text-white shadow-sm' : 'text-[var(--muted)] hover:text-[var(--foreground)]'
        }`}
      >
        Partial payments
        {partialCount > 0 && (
          <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-md bg-amber-500/90 text-white tabular-nums">
            {partialCount > 99 ? '99+' : partialCount}
          </span>
        )}
      </button>
    </div>
  );
}

export function DashboardEnquiriesPanel({
  enquiries,
  onRefresh,
}: {
  enquiries: Enquiry[];
  onRefresh: () => void;
}) {
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filtered = enquiries.filter(
    (e) =>
      statusFilter === 'ALL' ||
      e.status === statusFilter ||
      (statusFilter === 'NOT_CONVERTED' && e.status === 'CLOSED'),
  );

  async function changeStatus(id: string, status: string) {
    await updateEnquiryStatus(id, status);
    onRefresh();
  }

  return (
    <GlassCard
      title="Enquiries"
      action={
        <Link to="/enquiries" className="text-xs font-semibold text-[var(--primary)] hover:underline">
          Full page ?
        </Link>
      }
    >
      <div className="flex flex-wrap gap-2 mb-4">
        {ENQUIRY_STATUS_FILTERS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setStatusFilter(s.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              statusFilter === s.id
                ? 'bg-[var(--primary)] text-white'
                : 'bg-[var(--background-alt)] border border-[var(--border)] text-[var(--muted)] hover:text-[var(--foreground)]'
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <p className="text-sm text-[var(--muted)] py-8 text-center">No enquiries in this filter.</p>
      ) : (
        <>
          <div className="space-y-3 md:hidden">
            {filtered.map((e) => (
              <div key={e.id} className="rounded-xl border border-[var(--border)] p-3 bg-[var(--background)]">
                <p className="font-medium break-words">{e.customerName}</p>
                <p className="text-xs text-[var(--muted)] break-all">{e.phoneNumber}</p>
                <p className="text-sm mt-1">{e.eventType} · {formatDate(e.eventDate)}</p>
                <select
                  value={e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status}
                  onChange={(ev) => void changeStatus(e.id, ev.target.value)}
                  className="form-select mt-2 w-full text-sm px-3 py-2.5 rounded-lg min-h-[2.5rem]"
                >
                  {statusOptionsForDropdown(e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status).map((s) => (
                    <option key={s.id} value={s.id}>{s.label}</option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <div className="hidden md:block overflow-x-auto max-h-[min(70vh,640px)] -mx-1 rounded-xl border border-[var(--border)]">
            <table className="data-table w-full text-sm min-w-[36rem]">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--background)]">
                  <th className="px-4 py-3 text-left">Customer</th>
                  <th className="px-4 py-3 text-left">Event</th>
                  <th className="px-4 py-3 text-left">Date</th>
                  <th className="px-4 py-3 text-left min-w-[9rem]">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr key={e.id} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--background)]">
                    <td className="px-4 py-3 min-w-0">
                      <div className="font-medium break-words">{e.customerName}</div>
                      <div className="text-xs text-[var(--muted)] break-all">{e.phoneNumber}</div>
                    </td>
                    <td className="px-4 py-3 text-[var(--muted)] whitespace-nowrap">{e.eventType}</td>
                    <td className="px-4 py-3 text-[var(--muted)] whitespace-nowrap">{formatDate(e.eventDate)}</td>
                    <td className="px-4 py-3">
                      <select
                        value={e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status}
                        onChange={(ev) => void changeStatus(e.id, ev.target.value)}
                        className="form-select text-xs px-2 py-1.5 rounded-lg min-w-[8.5rem]"
                      >
                        {statusOptionsForDropdown(e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status).map((s) => (
                          <option key={s.id} value={s.id}>{s.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </GlassCard>
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
            <th className="px-4 py-3 text-right">Items</th>
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
              <td className="px-4 py-3 text-right font-medium tabular-nums">{o.dishes?.length ?? 0}</td>
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
            <p className="text-xs text-[var(--muted)]">{e.eventType}</p>
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
            <span className="text-[var(--muted)] text-xs">? {w.role}</span>
          </li>
        ))}
      </ul>
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
        <p className="text-xs text-[var(--muted)] ml-auto">Use the AI chat button ?</p>
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
          <span className="text-[var(--muted)]"> ? {e.eventType}</span>
        </li>
      ))}
    </ul>
  );
}

