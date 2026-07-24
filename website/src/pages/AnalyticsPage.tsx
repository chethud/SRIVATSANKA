import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { TrendingDown } from 'lucide-react';
import { PageHeader, StatCard, Card } from '../components/Layout';
import { MoneyHistoryModal } from '../components/MoneyHistoryModal';
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
  const { loading, error, analytics, refresh } = useAppData();
  const navigate = useNavigate();
  const [history, setHistory] = useState<'revenue' | null>(null);

  if (loading && !analytics) return <LoadingScreen />;

  const profit = analytics?.net_profit ?? 0;
  const revenue = analytics?.order_revenue ?? analytics?.total_revenue ?? 0;
  const expenses = analytics?.total_expenses ?? 0;
  const expenseItems = analytics?.expense_items ?? [];
  const revenueItems = (analytics?.revenue_items ?? []).filter(
    (i) => !i.source || i.source === 'order',
  );

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
              Revenue from confirmed order payments minus expense bills on{' '}
              <Link to="/invoices" className="text-[var(--primary)] hover:underline">Expenses Invoice</Link>.
              Click Revenue for payment history, or Expenses to open the invoice list.
            </p>
          </div>
        </div>
        <NetProfitGauge
          profit={profit}
          revenue={revenue}
          expenses={expenses}
          onRevenueClick={() => setHistory('revenue')}
          onExpensesClick={() => navigate('/invoices')}
        />
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Revenue"
          value={formatCurrency(revenue)}
          subtext="From order payments"
          onClick={() => setHistory('revenue')}
        />
        <StatCard
          label="Bill expenses"
          value={formatCurrency(expenses)}
          subtext="From uploaded bills"
          onClick={() => navigate('/invoices')}
        />
        <StatCard
          label="Expense items"
          value={String(expenseItems.length)}
          subtext="From invoice uploads"
          onClick={() => navigate('/invoices')}
        />
      </div>

      {history && (
        <MoneyHistoryModal
          kind="revenue"
          items={revenueItems}
          onClose={() => setHistory(null)}
          onChanged={() => refresh()}
        />
      )}

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
          <h3 className="font-semibold mb-1">Revenue by order</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Confirmed payments on converted orders</p>
          {analytics && <ProfitBreakdownPie analytics={analytics} />}
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Enquiries by outcome</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Converted vs unconverted</p>
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
