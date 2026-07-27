import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { TrendingDown } from 'lucide-react';
import { PageHeader, Card } from '../components/Layout';
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
} from '../components/charts';

export default function AnalyticsPage() {
  const { loading, error, analytics, refresh } = useAppData();
  const navigate = useNavigate();
  const [history, setHistory] = useState<'revenue' | null>(null);

  if (loading && !analytics) return <LoadingScreen />;

  const revenue = analytics?.order_revenue ?? analytics?.total_revenue ?? 0;
  const expenses = analytics?.total_expenses ?? 0;
  const expenseItems = analytics?.expense_items ?? [];
  const revenueItems = (analytics?.revenue_items ?? []).filter(
    (i) => !i.source || i.source === 'order',
  );

  return (
    <>
      <PageHeader title="Analytics" description="Charts for revenue, expenses, and enquiries" />
      <ErrorBanner message={error} />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8 items-start">
        <Card className="p-6">
          <p className="text-sm font-medium text-[var(--muted)]">Total Revenue</p>
          <p className="text-4xl font-bold mt-1 text-[var(--primary)]">
            {formatCurrency(revenue)}
          </p>
          <p className="text-sm text-[var(--muted)] mt-2">
            Confirmed payments on converted orders. Click below to view payment history.
          </p>
          <button
            type="button"
            onClick={() => setHistory('revenue')}
            className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-[var(--primary)] hover:bg-[var(--primary-dark)] rounded-lg shadow-sm transition"
          >
            View history
          </button>
        </Card>

        <Card className="p-6">
          <p className="text-sm font-medium text-[var(--muted)]">Total Expenses</p>
          <p className="text-4xl font-bold mt-1 text-amber-950">
            {formatCurrency(expenses)}
          </p>
          <p className="text-sm text-[var(--muted)] mt-2">
            Extracted from uploaded bills ({expenseItems.length} items). Click below to view bills.
          </p>
          <button
            type="button"
            onClick={() => navigate('/invoices')}
            className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-amber-700 hover:bg-amber-800 rounded-lg shadow-sm transition"
          >
            View invoices
          </button>
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

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6 items-start">
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Revenue vs expenses</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Compare income sources and bill expenses</p>
          {analytics && <RevenueExpenseBarChart analytics={analytics} />}
        </Card>
        <Card className="p-6">
          <h3 className="font-semibold mb-1">Monthly trend</h3>
          <p className="text-xs text-[var(--muted)] mb-4">Revenue and expenses by month</p>
          {analytics && <MonthlyTrendChart analytics={analytics} />}
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mb-6 items-start">
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

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
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
