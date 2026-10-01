import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MessageSquare, ShoppingBag, TrendingUp, Wallet } from 'lucide-react';
import { DashboardKpiCard } from '../components/DashboardKpiCard';
import {
  ChartFilter,
  DashboardEnquiriesPanel,
  DashboardTabBar,
  GlassCard,
  RecentOrdersTable,
  TodaysEventsWidget,
  UpcomingEventsList,
  type DashboardTab,
} from '../components/dashboard/DashboardSections';
import { ProfitRadialSnapshot, RevenueExpenseInteractiveChart } from '../components/charts';
import { MoneyHistoryModal } from '../components/MoneyHistoryModal';
import { BRAND_NAME } from '../brand';
import { PaymentReceivedModal } from '../components/PaymentReceivedModal';
import { PartialPaymentsPanel } from '../components/PartialPaymentsPanel';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, LoadingScreen } from '../components/ui';
import { formatCurrency } from '../api/client';
import {
  buildChartSeries,
  calcTrend,
  type ChartPeriod,
  getConvertedOrders,
  getRecentOrders,
  getTodaysEvents,
  getUpcomingEvents,
  totalBookedOrderValue,
} from '../utils/dashboardData';
import { isPartialPaymentOrder } from '../utils/orderBilling';

export default function DashboardPage() {
  const { loading, error, stats, enquiries, analytics, refresh, patchEnquiry } = useAppData();
  const navigate = useNavigate();
  const [chartMode, setChartMode] = useState<ChartPeriod>('monthly');
  const [tab, setTab] = useState<DashboardTab>('overview');
  const [history, setHistory] = useState<'revenue' | null>(null);

  const converted = useMemo(() => getConvertedOrders(enquiries), [enquiries]);
  const partialCount = useMemo(() => enquiries.filter(isPartialPaymentOrder).length, [enquiries]);
  const monthly = analytics?.monthly ?? [];
  const lastM = monthly[monthly.length - 1];
  const prevM = monthly[monthly.length - 2];

  const chartData = useMemo(() => buildChartSeries(analytics, chartMode), [analytics, chartMode]);
  const bookedValue = useMemo(() => totalBookedOrderValue(enquiries), [enquiries]);
  if (loading && !stats) return <LoadingScreen />;

  const profit = analytics?.net_profit ?? 0;
  const revenueReceived = analytics?.order_revenue ?? analytics?.total_revenue ?? 0;
  const expenses = analytics?.total_expenses ?? 0;
  const revenueItems = (analytics?.revenue_items ?? []).filter(
    (i) => !i.source || i.source === 'order',
  );

  return (
    <div className="max-w-[1440px] mx-auto space-y-6">
      <PaymentReceivedModal
        orders={enquiries}
        onResolved={async (updated) => {
          patchEnquiry(updated);
          await refresh();
        }}
      />

      {history && (
        <MoneyHistoryModal
          kind="revenue"
          items={revenueItems}
          onClose={() => setHistory(null)}
          onChanged={() => refresh()}
        />
      )}

      <header className="mb-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold text-[var(--foreground)] tracking-tight">Operations overview</h1>
          <p className="text-[var(--muted)] mt-1.5 text-sm">{BRAND_NAME}</p>
        </div>
        <DashboardTabBar
          tab={tab}
          onChange={setTab}
          newEnquiries={stats?.new_enquiries ?? 0}
          partialCount={partialCount}
        />
      </header>

      <ErrorBanner message={error} />

      {tab === 'enquiries' ? (
        <DashboardEnquiriesPanel enquiries={enquiries} onRefresh={refresh} />
      ) : tab === 'partial-payments' ? (
        <PartialPaymentsPanel
          enquiries={enquiries}
          onUpdated={async (updated) => {
            patchEnquiry(updated);
            await refresh();
          }}
        />
      ) : (
        <>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4 grid-cards-equal">
        <DashboardKpiCard
          label="New enquiries"
          value={String(stats?.new_enquiries ?? 0)}
          numericValue={stats?.new_enquiries ?? 0}
          subtext="awaiting callback"
          icon={MessageSquare}
          trend={calcTrend(stats?.new_enquiries ?? 0, Math.max(0, (stats?.new_enquiries ?? 0) - 1))}
          gradient={1}
          onClick={() => setTab('enquiries')}
        />
        <DashboardKpiCard
          label="Converted orders"
          value={String(converted.length)}
          numericValue={converted.length}
          subtext="active pipeline"
          icon={ShoppingBag}
          trend={calcTrend(converted.length, analytics?.converted_orders ?? converted.length)}
          gradient={2}
        />
        <DashboardKpiCard
          label="Revenue received"
          value={formatCurrency(revenueReceived)}
          numericValue={revenueReceived}
          formatValue={formatCurrency}
          subtext="cash logged on orders"
          icon={TrendingUp}
          trend={calcTrend(lastM?.revenue ?? revenueReceived, prevM?.revenue ?? 0)}
          onClick={() => setHistory('revenue')}
        />
        <DashboardKpiCard
          label="Booked order value"
          value={formatCurrency(bookedValue)}
          numericValue={bookedValue}
          formatValue={formatCurrency}
          subtext="order copy totals (incl. unpaid)"
          icon={Wallet}
          gradient={2}
        />
        <DashboardKpiCard
          label="Bill expenses"
          value={formatCurrency(expenses)}
          numericValue={expenses}
          formatValue={formatCurrency}
          subtext="from invoices"
          icon={Wallet}
          trend={calcTrend(lastM?.expenses ?? expenses, prevM?.expenses ?? 0)}
          gradient={2}
          onClick={() => navigate('/invoices')}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 grid-cards-equal">
        <GlassCard title="Upcoming events" action={<Link to="/orders" className="text-xs font-semibold text-[var(--primary)]">Calendar</Link>}>
          <UpcomingEventsList events={getUpcomingEvents(enquiries)} />
        </GlassCard>
        <GlassCard title="Today's events">
          <TodaysEventsWidget events={getTodaysEvents(enquiries)} />
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 gap-4 items-start">
        <GlassCard title="Recent orders" action={<Link to="/orders" className="text-xs font-semibold text-[var(--primary)]">View all</Link>}>
          <RecentOrdersTable orders={getRecentOrders(enquiries)} />
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 grid-cards-equal">
        <GlassCard
          className="xl:col-span-2"
          title="Revenue vs expense"
          action={
            <div className="flex items-center gap-3">
              <ChartFilter mode={chartMode} onChange={setChartMode} />
              <Link to="/analytics" className="text-xs font-semibold text-[var(--primary)] hover:underline">Analytics</Link>
            </div>
          }
        >
          {analytics ? <RevenueExpenseInteractiveChart data={chartData} /> : <p className="text-sm text-[var(--muted)] py-12 text-center">Loading…</p>}
        </GlassCard>

        <GlassCard title="Profit snapshot">
          <ProfitRadialSnapshot profit={profit} revenue={revenueReceived} expenses={expenses} />
        </GlassCard>
      </div>

        </>
      )}
    </div>
  );
}
