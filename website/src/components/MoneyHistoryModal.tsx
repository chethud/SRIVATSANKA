import { Link } from 'react-router-dom';
import { FileText, X } from 'lucide-react';
import type { ChartMoneyItem } from '../api/client';
import { downloadUploadFile, formatCurrency } from '../api/client';
import { Card } from './Layout';

type HistoryKind = 'revenue' | 'expense';

export function MoneyHistoryModal({
  kind,
  items,
  onClose,
}: {
  kind: HistoryKind;
  items: ChartMoneyItem[];
  onClose: () => void;
}) {
  const total = items.reduce((sum, e) => sum + (e.amount ?? 0), 0);
  const title = kind === 'revenue' ? 'Revenue history' : 'Expense history';
  const emptyHint =
    kind === 'revenue' ? (
      <>
        No confirmed payments yet. Mark an order delivered, then confirm payment on the dashboard — or upload profit bills on{' '}
        <Link to="/invoices" className="text-[var(--primary)] hover:underline" onClick={onClose}>
          Expenses Invoice
        </Link>
        .
      </>
    ) : (
      <>
        No expense bills yet.{' '}
        <Link to="/invoices" className="text-[var(--primary)] hover:underline" onClick={onClose}>
          Upload on Expenses Invoice
        </Link>
      </>
    );

  async function openDoc(item: ChartMoneyItem) {
    if (!item.id) return;
    try {
      await downloadUploadFile(item.id, item.fileName || 'document');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not download document');
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="money-history-title"
      onClick={onClose}
    >
      <div className="w-full max-w-2xl max-h-[85vh]" onClick={(e) => e.stopPropagation()}>
        <Card className="flex flex-col p-0 overflow-hidden shadow-xl h-full max-h-[85vh]">
          <div className="flex items-start justify-between gap-4 p-6 border-b border-[var(--border)]">
            <div>
              <h2 id="money-history-title" className="text-lg font-semibold">
                {title}
              </h2>
              <p className="text-sm text-[var(--muted)] mt-1">
                {items.length} item{items.length === 1 ? '' : 's'} · {formatCurrency(total)} total
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)]"
              aria-label="Close"
            >
              <X size={20} />
            </button>
          </div>
          <div className="overflow-auto flex-1 p-4">
            {items.length === 0 ? (
              <p className="text-sm text-[var(--muted)] text-center py-8">{emptyHint}</p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-[var(--muted)] uppercase tracking-wide border-b border-[var(--border)]">
                    <th className="pb-2 pr-3 font-medium">Date</th>
                    <th className="pb-2 pr-3 font-medium">Description</th>
                    {kind === 'expense' && <th className="pb-2 pr-3 font-medium">Purpose</th>}
                    {kind === 'expense' && <th className="pb-2 pr-3 font-medium">Document</th>}
                    {kind === 'revenue' && <th className="pb-2 pr-3 font-medium">Source</th>}
                    <th className="pb-2 text-right font-medium">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item, i) => (
                    <tr key={`${item.id || item.label}-${item.date}-${i}`} className="border-b border-[var(--border)]/60 last:border-0">
                      <td className="py-3 pr-3 text-[var(--muted)] whitespace-nowrap">{item.date ?? '—'}</td>
                      <td className="py-3 pr-3 font-medium">{item.label}</td>
                      {kind === 'expense' && (
                        <td className="py-3 pr-3 text-[var(--muted)]">{item.purpose || '—'}</td>
                      )}
                      {kind === 'expense' && (
                        <td className="py-3 pr-3">
                          {item.id ? (
                            <button
                              type="button"
                              onClick={() => void openDoc(item)}
                              className="inline-flex items-center gap-1.5 text-[var(--primary)] hover:underline"
                            >
                              <FileText size={14} />
                              <span className="truncate max-w-[140px]">{item.fileName || 'View file'}</span>
                            </button>
                          ) : (
                            '—'
                          )}
                        </td>
                      )}
                      {kind === 'revenue' && (
                        <td className="py-3 pr-3 text-[var(--muted)]">
                          {item.source === 'upload' ? 'Uploaded bill' : 'Order payment'}
                          {item.id ? (
                            <button
                              type="button"
                              onClick={() => void openDoc(item)}
                              className="ml-2 inline-flex items-center gap-1 text-[var(--primary)] hover:underline"
                            >
                              <FileText size={14} />
                              File
                            </button>
                          ) : null}
                        </td>
                      )}
                      <td
                        className={`py-3 text-right tabular-nums font-semibold ${
                          kind === 'expense' ? 'text-amber-900' : 'text-[var(--success-text)]'
                        }`}
                      >
                        {formatCurrency(item.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div className="p-4 border-t border-[var(--border)] flex flex-wrap gap-3 justify-end">
            {kind === 'expense' && (
              <Link to="/invoices" className="text-sm text-[var(--primary)] hover:underline" onClick={onClose}>
                Upload another bill
              </Link>
            )}
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)]"
            >
              Close
            </button>
          </div>
        </Card>
      </div>
    </div>
  );
}
