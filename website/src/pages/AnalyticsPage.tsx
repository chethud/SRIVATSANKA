import { Link } from 'react-router-dom';
import { TrendingDown } from 'lucide-react';
import { PageHeader, StatCard, Card } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, LoadingScreen } from '../components/ui';
import { formatCurrency } from '../api/client';
import {
  RevenueExpenseBarChart,
  MonthlyTrendChart,
  ProfitBreakdownPie,
  EnquiryStatusChart,
  EventTypeChart,
  ExpenseItemsChart,
  NetProfitGauge,
} from '../components/charts';

export default function AnalyticsPage() {
  const { loading, error, analytics } = useAppData();

  if (loading && !analytics) return <LoadingScreen />;

  const profit = analytics?.net_profit ?? 0;
  const revenue = analytics?.total_revenue ?? 0;
  const expenses = analytics?.total_expenses ?? 0;

  return (
    <>
      <PageHeader title="Analytics" description="Charts for revenue, expenses, profit, and enquiries" />
      <ErrorBanner message={error} />

      <Card className="p-6 mb-8">
        <div className="flex flex-wrap justify-between items-start gap-4 mb-6">
          <div>
            <p className="text-sm font-medium text-[var(--muted)]">Net profit</p>
            <p className={`text-4xl font-bold mt-1 ${profit >= 0 ? 'text-[var(--primary)]' : 'text-[var(--danger)]'}`}>
              {formatCurrency(profit)}
            </p>
            <p className="text-sm text-[var(--muted)] mt-2">
              Order revenue + expense bills confirmed on the{' '}
              <Link to="/invoices" className="text-[var(--primary)] hover:underline">Invoices</Link> page.
            </p>
          </div>
        </div>
        <NetProfitGauge profit={profit} revenue={revenue} expenses={expenses} />
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total revenue" value={formatCurrency(revenue)} />
        <StatCard label="Order revenue" value={formatCurrency(analytics?.order_revenue ?? 0)} />
        <StatCard label="Bill expenses" value={formatCurrency(expenses)} subtext="From uploaded bills" />
        <StatCard label="Expense items" value={String(analytics?.expense_items?.length ?? 0)} subtext="From invoice uploads" />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Revenue vs expenses</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Compare income sources and bill expenses</p>
          {analytics && <RevenueExpenseBarChart analytics={analytics} />}
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Monthly trend</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Revenue, expenses, and net profit by month</p>
          {analytics && <MonthlyTrendChart analytics={analytics} />}
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6">
        <Card className="p-6">
          <h3 className="font-semibold mb-1 flex items-center gap-2">
            <TrendingDown size={18} className="text-[var(--chart-amber)]" />
            Expense breakdown
          </h3>
          <p className="text-xs text-[var(--muted)] mb-4">Each uploaded expense bill (auto-recognized)</p>
          {analytics && <ExpenseItemsChart analytics={analytics} />}
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Revenue from orders</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Converted catering orders</p>
          {analytics && <ProfitBreakdownPie analytics={analytics} />}
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Enquiries by status</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Pipeline overview</p>
          {analytics && <EnquiryStatusChart analytics={analytics} />}
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Events by type</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Weddings, birthdays, and more</p>
          {analytics && <EventTypeChart analytics={analytics} />}
        </Card>
      </div>
    </>
  );
}
