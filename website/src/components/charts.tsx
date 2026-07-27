import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { Analytics } from '../api/client';
import { formatCurrency } from '../api/client';

const GREEN = '#006837';
const GREEN_LIGHT = '#8cc63f';
const AMBER = '#e6a817';
const BLUE = '#004d28';

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string; color?: string }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg shadow-lg px-3 py-2 text-sm text-[var(--foreground)]">
      {label && <p className="font-medium text-[var(--foreground)] mb-1">{label}</p>}
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color || GREEN }}>
          {p.name}: {formatCurrency(Number(p.value))}
        </p>
      ))}
    </div>
  );
}

function formatCompact(n: number) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `₹${(n / 1000).toFixed(1)}k`;
  return formatCurrency(n);
}

export function RevenueExpenseBarChart({ analytics }: { analytics: Analytics }) {
  const data = [
    { name: 'Order revenue', value: analytics.order_revenue, fill: GREEN },
    { name: 'Invoice expenses', value: analytics.order_expenses, fill: AMBER },
  ].filter((d) => d.value > 0);

  if (data.length === 0) {
    return <p className="text-sm text-[var(--muted)] text-center py-12">No financial data yet. Add orders and upload invoices.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#d4e8d4" />
        <XAxis dataKey="name" tick={{ fontSize: 12 }} />
        <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11 }} />
        <Tooltip content={<ChartTooltip />} />
        <Bar dataKey="value" radius={[8, 8, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MonthlyTrendChart({ analytics }: { analytics: Analytics }) {
  const data = analytics.monthly ?? [];
  if (data.length === 0) {
    return <p className="text-sm text-[var(--muted)] text-center py-12">Monthly trends appear after orders and invoice uploads.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#d4e8d4" />
        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11 }} />
        <Tooltip content={<ChartTooltip />} />
        <Legend />
        <Line type="monotone" dataKey="revenue" name="Revenue" stroke={GREEN} strokeWidth={2} dot={{ r: 4 }} />
        <Line type="monotone" dataKey="expenses" name="Expenses" stroke={AMBER} strokeWidth={2} dot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function ProfitBreakdownPie({ analytics }: { analytics: Analytics }) {
  const items = (analytics.revenue_items ?? [])
    .filter((i) => !i.source || i.source === 'order')
    .slice(0, 6)
    .map((i) => ({
      name: i.label.length > 22 ? `${i.label.slice(0, 20)}…` : i.label,
      value: i.amount,
      full: i.label,
    }));

  if (items.length === 0) {
    return (
      <p className="text-sm text-[var(--muted)] text-center py-12">
        Confirm order payments to see revenue breakdown.
      </p>
    );
  }

  const COLORS = [GREEN, GREEN_LIGHT, BLUE, AMBER, '#4a7c59', '#2d6a4f'];

  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie data={items} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={4}>
          {items.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v) => formatCurrency(Number(v ?? 0))}
          labelFormatter={(_, payload) => payload?.[0]?.payload?.full ?? ''}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function EnquiryStatusChart({ analytics }: { analytics: Analytics }) {
  const byStatus = analytics.by_status ?? {};
  const converted = byStatus.CONVERTED ?? 0;
  const unconverted = Object.entries(byStatus).reduce((sum, [status, count]) => {
    if (status === 'CONVERTED') return sum;
    return sum + count;
  }, 0);

  if (converted === 0 && unconverted === 0) {
    return <p className="text-sm text-[var(--muted)] text-center py-12">No enquiries yet.</p>;
  }

  const chartData = [
    { name: 'Converted', count: converted },
    { name: 'Unconverted', count: unconverted },
  ];
  const colors = [GREEN, '#9e9e9e'];

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e8f5e9" horizontal={false} />
        <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
        <Tooltip />
        <Bar dataKey="count" name="Enquiries" radius={[0, 6, 6, 0]}>
          {chartData.map((_, i) => (
            <Cell key={i} fill={colors[i % colors.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function EventTypeChart({ analytics }: { analytics: Analytics }) {
  const data = Object.entries(analytics.by_event_type ?? {})
    .map(([name, count]) => ({ name: name.length > 14 ? `${name.slice(0, 12)}…` : name, fullName: name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  if (data.length === 0) {
    return <p className="text-sm text-[var(--muted)] text-center py-12">No events yet.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#d4e8d4" />
        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
        <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
        <Tooltip labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName} />
        <Bar dataKey="count" name="Events" fill={GREEN} radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ExpenseItemsChart({ analytics }: { analytics: Analytics }) {
  const data = (analytics.expense_items ?? []).map((e) => ({
    name: e.label.length > 18 ? `${e.label.slice(0, 16)}…` : e.label,
    amount: e.amount,
    fullLabel: e.label,
  }));

  if (data.length === 0) {
    return <p className="text-sm text-[var(--muted)] text-center py-12">Upload expense bills on Invoices to see breakdown here.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, data.length * 36)}>
      <BarChart data={data} layout="vertical" margin={{ left: 4, right: 16 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e8f5e9" horizontal={false} />
        <XAxis type="number" tickFormatter={formatCompact} tick={{ fontSize: 11 }} />
        <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />
        <Tooltip
          formatter={(v) => formatCurrency(Number(v ?? 0))}
          labelFormatter={(_, payload) => payload?.[0]?.payload?.fullLabel}
        />
        <Bar dataKey="amount" name="Expense" fill={AMBER} radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

const DASH_BAR = '#c9a66b';
const DASH_DARK = '#4a3828';
const DASH_MID = '#b8a088';
const DASH_LIGHT = '#d4cfc4';
const PIE_COLORS = [DASH_DARK, DASH_BAR, DASH_MID, DASH_LIGHT, '#8dc63f', '#006837'];

function formatAxisK(n: number) {
  if (n >= 100000) return `₹${(n / 100000).toFixed(0)}L`;
  if (n >= 1000) return `₹${Math.round(n / 1000)}K`;
  return `₹${n}`;
}

function shortMonth(label: string) {
  return label.split(' ')[0] ?? label;
}

export function MonthlyCostTrendChart({ analytics }: { analytics: Analytics }) {
  const data = (analytics.monthly ?? []).map((m) => ({
    month: shortMonth(m.month),
    cost: m.expenses,
  }));

  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--dash-muted)] text-center py-16">
        Monthly costs appear after you upload expense invoices.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 12, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="var(--dash-chart-grid)" vertical={false} />
        <XAxis dataKey="month" tick={{ fontSize: 12, fill: 'var(--dash-muted)' }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={formatAxisK} tick={{ fontSize: 11, fill: 'var(--dash-muted)' }} axisLine={false} tickLine={false} width={52} />
        <Tooltip
          cursor={{ fill: 'rgba(201, 166, 107, 0.12)' }}
          content={({ active, payload, label }) =>
            active && payload?.[0] ? (
              <div className="bg-[var(--card)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm text-[var(--foreground)] shadow-md">
                <p className="font-medium text-[var(--dash-heading)]">{label}</p>
                <p className="text-[var(--dash-icon)]">{formatCurrency(Number(payload[0].value))}</p>
              </div>
            ) : null
          }
        />
        <Bar dataKey="cost" name="Expenses" fill={DASH_BAR} radius={[10, 10, 0, 0]} maxBarSize={56} />
      </BarChart>
    </ResponsiveContainer>
  );
}

type PieLabelProps = {
  cx?: number;
  cy?: number;
  midAngle?: number;
  outerRadius?: number;
  percent?: number;
  name?: string;
};

function renderPieLabel({ cx = 0, cy = 0, midAngle = 0, outerRadius = 0, percent = 0, name = '' }: PieLabelProps) {
  if (percent < 0.06) return null;
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 22;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  const short = name.length > 12 ? `${name.slice(0, 10)}…` : name;
  return (
    <text x={x} y={y} fill="var(--dash-heading)" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central" fontSize={12}>
      {short}
    </text>
  );
}

export function EventsByTypePieChart({ analytics }: { analytics: Analytics }) {
  const data = Object.entries(analytics.by_event_type ?? {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);

  if (data.length === 0) {
    return (
      <p className="text-sm text-[var(--dash-muted)] text-center py-16">
        Event breakdown appears when you have enquiries.
      </p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart margin={{ top: 8, right: 24, left: 24, bottom: 8 }}>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          cx="50%"
          cy="50%"
          innerRadius={0}
          outerRadius={88}
          paddingAngle={2}
          label={renderPieLabel}
          labelLine={{ stroke: 'var(--dash-muted)', strokeWidth: 1 }}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} stroke="#fff" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v, _n, item) => [`${v} events`, (item as { payload?: { name?: string } })?.payload?.name ?? '']}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function NetProfitGauge({
  profit,
  revenue,
  expenses,
  onRevenueClick,
  onExpensesClick,
}: {
  profit: number;
  revenue: number;
  expenses: number;
  onRevenueClick?: () => void;
  onExpensesClick?: () => void;
}) {
  const pct = revenue > 0 ? Math.min(100, Math.max(0, (profit / revenue) * 100)) : 0;
  const positive = profit >= 0;

  return (
    <div className="space-y-4">
      <div className="h-4 rounded-full bg-[var(--background)] overflow-hidden border border-[var(--border)]">
        <div
          className={`h-full rounded-full transition-all ${positive ? 'bg-gradient-to-r from-[var(--accent)] to-[var(--primary)]' : 'bg-gradient-to-r from-red-200 to-red-500'}`}
          style={{ width: `${Math.abs(pct)}%` }}
        />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <button
          type="button"
          onClick={onRevenueClick}
          disabled={!onRevenueClick}
          className={`p-2 rounded-lg bg-[var(--success-bg)] text-left sm:text-center transition ${
            onRevenueClick ? 'hover:ring-2 hover:ring-[var(--primary)]/30 cursor-pointer' : ''
          }`}
        >
          <p className="text-[var(--muted)]">Revenue</p>
          <p className="font-semibold text-[var(--success-text)]">{formatCurrency(revenue)}</p>
          {onRevenueClick && <p className="text-[10px] text-[var(--muted)] mt-0.5">View history</p>}
        </button>
        <button
          type="button"
          onClick={onExpensesClick}
          disabled={!onExpensesClick}
          className={`p-2 rounded-lg bg-amber-50 text-left sm:text-center transition ${
            onExpensesClick ? 'hover:ring-2 hover:ring-amber-400/40 cursor-pointer' : ''
          }`}
        >
          <p className="text-[var(--muted)]">Expenses</p>
          <p className="font-semibold text-amber-900">{formatCurrency(expenses)}</p>
          {onExpensesClick && <p className="text-[10px] text-[var(--muted)] mt-0.5">View history</p>}
        </button>
        <div className={`p-2 rounded-lg ${positive ? 'bg-[var(--success-bg)]' : 'bg-[var(--danger-bg)]'}`}>
          <p className="text-[var(--muted)]">Net</p>
          <p className={`font-semibold ${positive ? 'text-[var(--success-text)]' : 'text-[var(--danger)]'}`}>{formatCurrency(profit)}</p>
        </div>
      </div>
    </div>
  );
}

const BRAND_PRIMARY = '#0b6b3a';
const BRAND_ACCENT = '#7ac943';

function PremiumTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name?: string; value?: number; color?: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-3 shadow-[var(--shadow-md)] text-sm">
      {label && <p className="font-semibold text-[var(--foreground)] mb-2">{label}</p>}
      {payload.map((p) => (
        <p key={p.name} className="flex justify-between gap-4">
          <span style={{ color: p.color }}>{p.name}</span>
          <span className="font-medium">{formatCurrency(Number(p.value ?? 0))}</span>
        </p>
      ))}
    </div>
  );
}

export function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center">
      <p className="text-sm text-[var(--muted)] max-w-xs">{message}</p>
    </div>
  );
}

export function RevenueExpenseInteractiveChart({
  data,
}: {
  data: { label: string; revenue: number; expenses: number }[];
}) {
  const [ready, setReady] = useState(false);
  if (data.length === 0) {
    return <ChartEmpty message="Add orders and upload expense invoices to see revenue vs expenses." />;
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onAnimationComplete={() => setReady(true)}>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
          <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
          <YAxis tickFormatter={formatCompact} tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} width={48} />
          <Tooltip content={<PremiumTooltip />} />
          <Legend />
          <Bar dataKey="expenses" name="Expenses" fill={BRAND_ACCENT} radius={[8, 8, 0, 0]} maxBarSize={40} isAnimationActive={ready} />
          <Line type="monotone" dataKey="revenue" name="Revenue" stroke={BRAND_PRIMARY} strokeWidth={3} dot={{ r: 4, fill: BRAND_PRIMARY }} isAnimationActive={ready} />
        </ComposedChart>
      </ResponsiveContainer>
    </motion.div>
  );
}

export function ProfitRadialSnapshot({ profit, revenue, expenses }: { profit: number; revenue: number; expenses: number }) {
  const marginPct = revenue > 0 ? Math.min(100, Math.max(-100, (profit / revenue) * 100)) : 0;
  const positive = profit >= 0;
  const circumference = 2 * Math.PI * 54;
  const targetOffset = circumference - (Math.abs(marginPct) / 100) * circumference;
  const expenseRatio = revenue > 0 ? Math.min(100, (expenses / revenue) * 100) : 0;

  return (
    <div className="flex flex-col gap-5">
      <div className="relative w-40 h-40 mx-auto">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="var(--chart-grid)" strokeWidth="8" />
          <motion.circle
            cx="60"
            cy="60"
            r="54"
            fill="none"
            stroke={positive ? BRAND_ACCENT : 'var(--danger)'}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: targetOffset }}
            transition={{ duration: 1, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span
            className="text-3xl font-bold text-[var(--foreground)] tabular-nums"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
          >
            {Math.round(marginPct)}%
          </motion.span>
          <span className="text-xs text-[var(--muted)] mt-0.5">Net margin</span>
        </div>
      </div>
      <p className="text-center text-xs text-[var(--muted)]">
        Expenses are {Math.round(expenseRatio)}% of revenue
      </p>
      <div className="grid grid-cols-3 gap-3 text-center text-xs">
        <div className="p-3 rounded-xl bg-[var(--primary-light)] border border-[var(--border)]">
          <p className="text-[var(--muted)] mb-1 font-medium">Revenue</p>
          <p className="font-bold text-[var(--primary)] tabular-nums">{formatCurrency(revenue)}</p>
        </div>
        <div className="p-3 rounded-xl bg-[var(--background-alt)] border border-[var(--border)]">
          <p className="text-[var(--muted)] mb-1 font-medium">Expenses</p>
          <p className="font-bold tabular-nums">{formatCurrency(expenses)}</p>
        </div>
        <div className={`p-3 rounded-xl border ${positive ? 'bg-[var(--success-bg)] border-[var(--border)]' : 'bg-[var(--danger-bg)] border-[var(--danger)]'}`}>
          <p className="text-[var(--muted)] mb-1 font-medium">Net profit</p>
          <p className={`font-bold tabular-nums ${positive ? 'text-[var(--success-text)]' : 'text-[var(--danger)]'}`}>
            {formatCurrency(profit)}
          </p>
        </div>
      </div>
    </div>
  );
}

export function RevenueForecastChart({
  data,
}: {
  data: { label: string; actual: number | null; forecast: number | null }[];
}) {
  if (data.length === 0) {
    return <p className="text-sm text-[var(--muted)] text-center py-12">Forecast unlocks with more monthly data.</p>;
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" vertical={false} />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: 'var(--muted)' }} axisLine={false} tickLine={false} />
        <YAxis tickFormatter={formatCompact} tick={{ fontSize: 10, fill: 'var(--muted)' }} width={44} axisLine={false} tickLine={false} />
        <Tooltip content={<PremiumTooltip />} />
        <Legend />
        <Line type="monotone" dataKey="actual" name="Actual" stroke={BRAND_PRIMARY} strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
        <Line type="monotone" dataKey="forecast" name="Forecast" stroke={BRAND_ACCENT} strokeWidth={2} strokeDasharray="6 4" dot={{ r: 3 }} connectNulls />
      </LineChart>
    </ResponsiveContainer>
  );
}
