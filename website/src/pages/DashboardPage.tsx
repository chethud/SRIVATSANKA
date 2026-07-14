import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { MessageSquare, ShoppingBag, TrendingUp, Wallet } from 'lucide-react';
import { DashboardKpiCard } from '../components/DashboardKpiCard';
import {
  AiInsightsPanel,
  ChartFilter,
  DashboardEnquiriesPanel,
  DashboardTabBar,
  GlassCard,
  NotificationsWidget,
  RecentOrdersTable,
  TodaysEventsWidget,
  TopDishesList,
  UpcomingEventsList,
  VendorPaymentsSummary,
  WorkerAttendanceOverview,
  type DashboardTab,
} from '../components/dashboard/DashboardSections';
import {
  ProfitRadialSnapshot,
  RevenueExpenseInteractiveChart,
  RevenueForecastChart,
} from '../components/charts';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, LoadingScreen } from '../components/ui';
import { formatCurrency } from '../api/client';
import {
  buildChartSeries,
  buildForecast,
  calcTrend,
  sparklineFromMonthly,
  type ChartPeriod,
  getAiInsights,
  getConvertedOrders,
  getRecentOrders,
  getTopDishes,
  getTodaysEvents,
  getUnreadNotifications,
  getUpcomingEvents,
  getWorkerOverview,
} from '../utils/dashboardData';

export default function DashboardPage() {
  const { loading, error, stats, enquiries, dishes, notifications, vendors, workers, analytics, refresh } = useAppData();
  const [chartMode, setChartMode] = useState<ChartPeriod>('monthly');
  const [tab, setTab] = useState<DashboardTab>('overview');

  const converted = useMemo(() => getConvertedOrders(enquiries), [enquiries]);
  const monthly = analytics?.monthly ?? [];
  const lastM = monthly[monthly.length - 1];
  const prevM = monthly[monthly.length - 2];

  const chartData = useMemo(() => buildChartSeries(analytics, chartMode), [analytics, chartMode]);
  const forecastData = useMemo(() => buildForecast(analytics), [analytics]);
  const insights = useMemo(() => getAiInsights(stats, analytics, enquiries), [stats, analytics, enquiries]);
  const workerOverview = useMemo(() => getWorkerOverview(workers), [workers]);

  if (loading && !stats) return <LoadingScreen />;

  const profit = analytics?.net_profit ?? 0;
  const revenue = analytics?.total_revenue ?? 0;
  const expenses = analytics?.total_expenses ?? 0;

  return (
    <div className="max-w-[1440px] mx-auto space-y-6">
      <motion.header initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} className="mb-1 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-semibold text-[var(--foreground)] tracking-tight">Operations overview</h1>
          <p className="text-[var(--muted)] mt-1.5 text-sm">SRIVATSANKA EVENTS — live metrics and pipeline</p>
        </div>
        <DashboardTabBar
          tab={tab}
          onChange={setTab}
          newEnquiries={stats?.new_enquiries ?? 0}
        />
      </motion.header>

      <ErrorBanner message={error} />

      {tab === 'enquiries' ? (
        <DashboardEnquiriesPanel enquiries={enquiries} onRefresh={refresh} />
      ) : (
        <>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <DashboardKpiCard
          label="New enquiries"
          value={String(stats?.new_enquiries ?? 0)}
          numericValue={stats?.new_enquiries ?? 0}
          subtext="awaiting callback"
          icon={MessageSquare}
          trend={calcTrend(stats?.new_enquiries ?? 0, Math.max(0, (stats?.new_enquiries ?? 0) - 1))}
          sparkline={sparklineFromMonthly(analytics, 'revenue')}
          sparkId="enq"
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
          sparkline={sparklineFromMonthly(analytics, 'profit')}
          sparkId="ord"
          gradient={2}
        />
        <DashboardKpiCard
          label="Net profit"
          value={formatCurrency(profit)}
          numericValue={profit}
          formatValue={formatCurrency}
          subtext="after expenses"
          icon={TrendingUp}
          trend={calcTrend(lastM?.profit ?? profit, prevM?.profit ?? 0)}
          sparkline={sparklineFromMonthly(analytics, 'profit')}
          sparkId="profit"
        />
        <DashboardKpiCard
          label="Bill expenses"
          value={formatCurrency(expenses)}
          numericValue={expenses}
          formatValue={formatCurrency}
          subtext="from invoices"
          icon={Wallet}
          trend={calcTrend(lastM?.expenses ?? expenses, prevM?.expenses ?? 0)}
          sparkline={sparklineFromMonthly(analytics, 'expenses')}
          sparkId="exp"
          gradient={2}
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
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
          <ProfitRadialSnapshot profit={profit} revenue={revenue} expenses={expenses} />
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <GlassCard className="lg:col-span-2" title="Revenue forecast" action={<span className="text-xs text-[var(--muted)]">Projected</span>}>
          <RevenueForecastChart data={forecastData} />
        </GlassCard>
        <GlassCard title="Today's events">
          <TodaysEventsWidget events={getTodaysEvents(enquiries)} />
        </GlassCard>
      </div>

      <AiInsightsPanel insights={insights} />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <GlassCard title="Recent orders" action={<Link to="/orders" className="text-xs font-semibold text-[var(--primary)]">View all</Link>}>
          <RecentOrdersTable orders={getRecentOrders(enquiries)} />
        </GlassCard>
        <GlassCard title="Upcoming events" action={<Link to="/orders" className="text-xs font-semibold text-[var(--primary)]">Calendar</Link>}>
          <UpcomingEventsList events={getUpcomingEvents(enquiries)} />
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <GlassCard title="Top selling dishes">
          <TopDishesList dishes={getTopDishes(enquiries)} />
        </GlassCard>
        <GlassCard title="Vendor payments" action={<Link to="/vendors" className="text-xs text-[var(--primary)]">Vendors</Link>}>
          <VendorPaymentsSummary vendors={vendors} />
          <p className="text-xs text-[var(--muted)] mt-3">{vendors.length} suppliers registered</p>
        </GlassCard>
        <GlassCard title="Worker overview" action={<Link to="/workers" className="text-xs text-[var(--primary)]">Workers</Link>}>
          <WorkerAttendanceOverview workers={workerOverview.workers} byRole={workerOverview.byRole} />
        </GlassCard>
        <GlassCard title="Notifications" action={<span className="text-xs text-[var(--muted)]">{stats?.unread_notifications ?? 0} unread</span>}>
          <NotificationsWidget items={getUnreadNotifications(notifications)} />
        </GlassCard>
      </div>

      <p className="text-center text-xs text-[var(--muted)] pb-4">
        {dishes.length} menu items · {vendors.length} vendors tracked
      </p>
        </>
      )}
    </div>
  );
}
