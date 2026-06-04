import { useState } from 'react';
import { Link } from 'react-router-dom';
import { TrendingDown, X } from 'lucide-react';
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
  const [showAllExpenses, setShowAllExpenses] = useState(false);

  if (loading && !analytics) return <LoadingScreen />;

  const profit = analytics?.net_profit ?? 0;
  const revenue = analytics?.total_revenue ?? 0;
  const expenses = analytics?.total_expenses ?? 0;
  const expenseItems = analytics?.expense_items ?? [];
  const expenseTotal = expenseItems.reduce((sum, e) => sum + (e.amount ?? 0), 0);

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
        <StatCard
          label="Expense items"
          value={String(expenseItems.length)}
          subtext="From invoice uploads"
          onClick={() => setShowAllExpenses(true)}
        />
      </div>

      {showAllExpenses && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="expense-list-title"
          onClick={() => setShowAllExpenses(false)}
        >
          <div className="w-full max-w-2xl max-h-[85vh]" onClick={(e) => e.stopPropagation()}>
          <Card className="flex flex-col p-0 overflow-hidden shadow-xl h-full max-h-[85vh]">
            <div className="flex items-start justify-between gap-4 p-6 border-b border-[var(--border)]">
              <div>
                <h2 id="expense-list-title" className="text-lg font-semibold">
                  All expense bills
                </h2>
                <p className="text-sm text-[var(--muted)] mt-1">
                  {expenseItems.length} item{expenseItems.length === 1 ? '' : 's'} · {formatCurrency(expenseTotal)} total
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowAllExpenses(false)}
                className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)]"
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>
            <div className="overflow-auto flex-1 p-4">
              {expenseItems.length === 0 ? (
                <p className="text-sm text-[var(--muted)] text-center py-8">
                  No expense bills yet.{' '}
                  <Link to="/invoices" className="text-[var(--primary)] hover:underline" onClick={() => setShowAllExpenses(false)}>
                    Upload on Invoices
                  </Link>
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-[var(--muted)] uppercase tracking-wide border-b border-[var(--border)]">
                      <th className="pb-2 pr-3 font-medium">Date</th>
                      <th className="pb-2 pr-3 font-medium">Description</th>
                      <th className="pb-2 pr-3 font-medium">Purpose</th>
                      <th className="pb-2 text-right font-medium">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {expenseItems.map((item, i) => (
                      <tr key={`${item.label}-${item.date}-${i}`} className="border-b border-[var(--border)]/60 last:border-0">
                        <td className="py-3 pr-3 text-[var(--muted)] whitespace-nowrap">{item.date ?? '—'}</td>
                        <td className="py-3 pr-3 font-medium">{item.label}</td>
                        <td className="py-3 pr-3 text-[var(--muted)]">{item.purpose || '—'}</td>
                        <td className="py-3 text-right tabular-nums font-semibold text-amber-900">{formatCurrency(item.amount)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="p-4 border-t border-[var(--border)] flex flex-wrap gap-3 justify-end">
              <Link
                to="/invoices"
                className="text-sm text-[var(--primary)] hover:underline"
                onClick={() => setShowAllExpenses(false)}
              >
                Upload another bill
              </Link>
              <button
                type="button"
                onClick={() => setShowAllExpenses(false)}
                className="px-4 py-2 text-sm font-medium rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]"
              >
                Close
              </button>
            </div>
          </Card>
          </div>
        </div>
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
