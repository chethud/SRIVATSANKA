import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart3, Receipt, TrendingUp, Wallet } from 'lucide-react';
import { PageHeader, Card } from '../components/Layout';
import { MoneyHistoryModal } from '../components/MoneyHistoryModal';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, FilterChips, LoadingScreen } from '../components/ui';
import { formatCurrency } from '../api/client';
import {
  EnquiryStatusChart,
  EventTypeChart,
  ExpenseItemsChart,
  MonthlyTrendChart,
  ProfitBreakdownPie,
  ProfitRadialSnapshot,
  RevenueExpenseBarChart,
  RevenueExpenseInteractiveChart,
} from '../components/charts';
import { buildChartSeries, totalBookedOrderValue, type ChartPeriod } from '../utils/dashboardData';

const CHART_VIEWS = [
  { id: 'overview', label: 'Revenue vs expense' },
  { id: 'monthly', label: 'Monthly lines' },
  { id: 'totals', label: 'Income vs bills' },
  { id: 'revenue-mix', label: 'Revenue sources' },
  { id: 'expenses', label: 'Expense bills' },
  { id: 'enquiries', label: 'Enquiries' },
  { id: 'events', label: 'Event types' },
] as const;

type ChartViewId = (typeof CHART_VIEWS)[number]['id'];

const CHART_HINTS: Record<ChartViewId, string> = {
  overview: 'Bars = expenses, line = revenue received. Use period to zoom weekly, monthly, or yearly.',
  monthly: 'Cash received vs invoice expenses by calendar month.',
  totals: 'Side-by-side comparison of order revenue and uploaded bill totals.',
  'revenue-mix': 'Share of confirmed payments by order (top entries).',
  expenses: 'Each recognized amount from uploaded expense invoices.',
  enquiries: 'Converted vs still in the enquiry pipeline.',
  events: 'Orders grouped by event type.',
};

function AnalyticsKpi({
  label,
  value,
  hint,
  tone = 'primary',
  onClick,
}: {
  label: string;
  value: string;
  hint: string;
  tone?: 'primary' | 'neutral' | 'amber' | 'profit';
  onClick?: () => void;
}) {
  const toneClass =
    tone === 'amber'
      ? 'text-amber-600 dark:text-amber-400'
      : tone === 'neutral'
        ? 'text-[var(--foreground)]'
        : tone === 'profit'
          ? 'text-[var(--success-text)]'
          : 'text-[var(--primary)]';

  const inner = (
    <>
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{label}</p>
      <p className={`analytics-kpi-value font-bold mt-1.5 ${toneClass}`}>{value}</p>
      <p className="text-xs text-[var(--muted)] mt-2 leading-snug line-clamp-2">{hint}</p>
    </>
  );

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="text-left rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)] hover:border-[var(--primary)]/40 transition-colors w-full min-w-0"
      >
        {inner}
      </button>
    );
  }

  return (
    <div className="rounded-[var(--radius-xl)] border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)] min-w-0">
      {inner}
    </div>
  );
}

export default function AnalyticsPage() {
  const { loading, error, analytics, enquiries, refresh } = useAppData();
  const navigate = useNavigate();
  const [history, setHistory] = useState<'revenue' | null>(null);
  const [chartView, setChartView] = useState<ChartViewId>('overview');
  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('monthly');

  const revenueReceived = analytics?.order_revenue ?? analytics?.total_revenue ?? 0;
  const bookedValue = useMemo(() => totalBookedOrderValue(enquiries), [enquiries]);
  const expenses = analytics?.total_expenses ?? 0;
  const profit = analytics?.net_profit ?? 0;
  const expenseItems = analytics?.expense_items ?? [];
  const revenueItems = (analytics?.revenue_items ?? []).filter(
    (i) => !i.source || i.source === 'order',
  );

  const chartSeries = useMemo(
    () => buildChartSeries(analytics, chartPeriod),
    [analytics, chartPeriod],
  );

  const showPeriodFilter = chartView === 'overview';

  if (loading && !analytics) return <LoadingScreen />;

  function renderChart() {
    if (!analytics) {
      return <p className="text-sm text-[var(--muted)] text-center py-16">Loading charts…</p>;
    }
    switch (chartView) {
      case 'overview':
        return <RevenueExpenseInteractiveChart data={chartSeries} />;
      case 'monthly':
        return <MonthlyTrendChart analytics={analytics} />;
      case 'totals':
        return <RevenueExpenseBarChart analytics={analytics} />;
      case 'revenue-mix':
        return <ProfitBreakdownPie analytics={analytics} />;
      case 'expenses':
        return <ExpenseItemsChart analytics={analytics} />;
      case 'enquiries':
        return <EnquiryStatusChart analytics={analytics} />;
      case 'events':
        return <EventTypeChart analytics={analytics} />;
      default:
        return null;
    }
  }

  return (
    <>
      <PageHeader
        title="Analytics"
        description="Revenue, expenses, and pipeline — pick a chart below to explore."
      />
      <ErrorBanner message={error} />

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <AnalyticsKpi
          label="Revenue received"
          value={formatCurrency(revenueReceived)}
          hint="Cash logged on orders (partials count only what is paid)."
          onClick={() => setHistory('revenue')}
        />
        <AnalyticsKpi
          label="Booked order value"
          value={formatCurrency(bookedValue)}
          hint="Same overall total as order copy (grand total line when set)."
          tone="neutral"
        />
        <AnalyticsKpi
          label="Bill expenses"
          value={formatCurrency(expenses)}
          hint={`From ${expenseItems.length} uploaded invoice${expenseItems.length === 1 ? '' : 's'}.`}
          tone="amber"
          onClick={() => navigate('/invoices')}
        />
        <AnalyticsKpi
          label="Net profit"
          value={formatCurrency(profit)}
          hint="Revenue received minus bill expenses."
          tone="profit"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6 grid-cards-equal">
        <Card className="card-tile p-5 sm:p-6 xl:col-span-2 min-w-0">
          <div className="mb-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-semibold text-[var(--foreground)] flex items-center gap-2">
                <BarChart3 size={18} className="text-[var(--primary)] shrink-0" />
                Charts
              </h2>
              {showPeriodFilter && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--muted)]">Period</span>
                  <FilterChips
                    options={[
                      { id: 'weekly', label: 'Weekly' },
                      { id: 'monthly', label: 'Monthly' },
                      { id: 'yearly', label: 'Yearly' },
                    ]}
                    selected={chartPeriod}
                    onSelect={(id) => setChartPeriod(id as ChartPeriod)}
                  />
                </div>
              )}
            </div>
            <FilterChips
              options={CHART_VIEWS.map((c) => ({ id: c.id, label: c.label }))}
              selected={chartView}
              onSelect={(id) => setChartView(id as ChartViewId)}
            />
            <p className="text-xs text-[var(--muted)] leading-relaxed">
              <span className="font-semibold text-[var(--foreground)]">
                {CHART_VIEWS.find((c) => c.id === chartView)?.label}:
              </span>{' '}
              {CHART_HINTS[chartView]}
            </p>
          </div>
          <div className="analytics-chart-panel w-full min-w-0">{renderChart()}</div>
        </Card>

        <Card className="card-tile p-5 sm:p-6 flex flex-col gap-4">
          <div>
            <h2 className="font-semibold text-[var(--foreground)] flex items-center gap-2">
              <TrendingUp size={18} className="text-[var(--primary)]" />
              Profit snapshot
            </h2>
            <p className="text-xs text-[var(--muted)] mt-1">Margin vs revenue received</p>
          </div>
          {analytics ? (
            <ProfitRadialSnapshot profit={profit} revenue={revenueReceived} expenses={expenses} />
          ) : (
            <p className="text-sm text-[var(--muted)] py-8 text-center">Loading…</p>
          )}
          <div className="mt-auto pt-2 border-t border-[var(--border)] space-y-2 text-sm">
            <button
              type="button"
              onClick={() => setHistory('revenue')}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-left text-[var(--foreground)]"
            >
              <Wallet size={16} className="text-[var(--primary)]" />
              Payment history
            </button>
            <button
              type="button"
              onClick={() => navigate('/invoices')}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-left text-[var(--foreground)]"
            >
              <Receipt size={16} className="text-amber-600 dark:text-amber-400" />
              View expense invoices
            </button>
          </div>
        </Card>
      </div>

      {history && (
        <MoneyHistoryModal
          kind="revenue"
          items={revenueItems}
          onClose={() => setHistory(null)}
          onChanged={() => refresh()}
        />
      )}
    </>
  );
}
