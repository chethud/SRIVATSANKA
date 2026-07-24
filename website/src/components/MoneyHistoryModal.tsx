import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, FileText, Trash2, X } from 'lucide-react';
import type { ChartMoneyItem } from '../api/client';
import {
  deleteUpload,
  downloadUploadFile,
  fetchUploadBlobUrl,
  formatCurrency,
  removeOrderFromRevenue,
} from '../api/client';
import { Card } from './Layout';

type HistoryKind = 'revenue' | 'expense';

export function MoneyHistoryModal({
  kind,
  items,
  onClose,
  onChanged,
}: {
  kind: HistoryKind;
  items: ChartMoneyItem[];
  onClose: () => void;
  onChanged?: () => void | Promise<void>;
}) {
  const [rows, setRows] = useState(items);
  const [preview, setPreview] = useState<{ url: string; name: string; type: string } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    setRows(items);
  }, [items]);

  const total = rows.reduce((sum, e) => sum + (e.amount ?? 0), 0);
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

  function rowKey(item: ChartMoneyItem, i: number) {
    return item.id || item.enquiryId || `${item.label}-${item.date}-${i}`;
  }

  async function viewDoc(item: ChartMoneyItem) {
    if (!item.id) return;
    setBusyId(item.id);
    try {
      const { url, contentType } = await fetchUploadBlobUrl(item.id);
      setPreview({ url, name: item.fileName || 'Document', type: contentType });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not open document');
    } finally {
      setBusyId(null);
    }
  }

  async function saveDoc(item: ChartMoneyItem) {
    if (!item.id) return;
    setBusyId(item.id);
    try {
      await downloadUploadFile(item.id, item.fileName || 'document');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not download document');
    } finally {
      setBusyId(null);
    }
  }

  async function removeItem(item: ChartMoneyItem, index: number) {
    const label = kind === 'expense' ? 'expense' : 'revenue entry';
    if (!window.confirm(`Delete this ${label}? This cannot be undone.`)) return;

    const key = rowKey(item, index);
    setBusyId(key);
    try {
      if (item.id) {
        await deleteUpload(item.id);
      } else if (item.enquiryId && kind === 'revenue') {
        await removeOrderFromRevenue(item.enquiryId);
      } else {
        throw new Error('This entry cannot be deleted');
      }
      setRows((prev) => prev.filter((_, i) => i !== index));
      await onChanged?.();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not delete');
    } finally {
      setBusyId(null);
    }
  }

  function closePreview() {
    if (preview?.url) URL.revokeObjectURL(preview.url);
    setPreview(null);
  }

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
        role="dialog"
        aria-modal="true"
        aria-labelledby="money-history-title"
        onClick={onClose}
      >
        <div className="w-full max-w-3xl max-h-[85vh]" onClick={(e) => e.stopPropagation()}>
          <Card className="flex flex-col p-0 overflow-hidden shadow-xl h-full max-h-[85vh]">
            <div className="flex items-start justify-between gap-4 p-6 border-b border-[var(--border)]">
              <div>
                <h2 id="money-history-title" className="text-lg font-semibold">
                  {title}
                </h2>
                <p className="text-sm text-[var(--muted)] mt-1">
                  {rows.length} item{rows.length === 1 ? '' : 's'} · {formatCurrency(total)} total
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
              {rows.length === 0 ? (
                <p className="text-sm text-[var(--muted)] text-center py-8">{emptyHint}</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-[var(--muted)] uppercase tracking-wide border-b border-[var(--border)]">
                      <th className="pb-2 pr-3 font-medium">Date</th>
                      <th className="pb-2 pr-3 font-medium">Description</th>
                      {kind === 'expense' && <th className="pb-2 pr-3 font-medium">Purpose</th>}
                      <th className="pb-2 pr-3 font-medium">{kind === 'expense' ? 'Document' : 'Source'}</th>
                      <th className="pb-2 text-right font-medium">Amount</th>
                      <th className="pb-2 pl-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((item, i) => {
                      const key = rowKey(item, i);
                      const canDelete = Boolean(item.id || (kind === 'revenue' && item.enquiryId));
                      return (
                        <tr key={key} className="border-b border-[var(--border)]/60 last:border-0">
                          <td className="py-3 pr-3 text-[var(--muted)] whitespace-nowrap">{item.date ?? '—'}</td>
                          <td className="py-3 pr-3 font-medium">{item.label}</td>
                          {kind === 'expense' && (
                            <td className="py-3 pr-3 text-[var(--muted)]">{item.purpose || '—'}</td>
                          )}
                          <td className="py-3 pr-3">
                            {kind === 'revenue' && !item.id ? (
                              <span className="text-[var(--muted)]">Order payment</span>
                            ) : item.id ? (
                              <div className="flex flex-wrap items-center gap-2">
                                {kind === 'revenue' && (
                                  <span className="text-[var(--muted)] text-xs">Uploaded bill</span>
                                )}
                                <button
                                  type="button"
                                  disabled={busyId === item.id}
                                  onClick={() => void viewDoc(item)}
                                  className="inline-flex items-center gap-1 text-[var(--primary)] hover:underline disabled:opacity-50"
                                >
                                  <Eye size={14} />
                                  View
                                </button>
                                <button
                                  type="button"
                                  disabled={busyId === item.id}
                                  onClick={() => void saveDoc(item)}
                                  className="inline-flex items-center gap-1 text-[var(--muted)] hover:text-[var(--foreground)] hover:underline disabled:opacity-50"
                                >
                                  <FileText size={14} />
                                  <span className="truncate max-w-[100px]">{item.fileName || 'Download'}</span>
                                </button>
                              </div>
                            ) : (
                              <span className="text-[var(--muted)]">—</span>
                            )}
                          </td>
                          <td
                            className={`py-3 text-right tabular-nums font-semibold ${
                              kind === 'expense' ? 'text-amber-900' : 'text-[var(--success-text)]'
                            }`}
                          >
                            {formatCurrency(item.amount)}
                          </td>
                          <td className="py-3 pl-3 text-right">
                            <button
                              type="button"
                              disabled={!canDelete || busyId === key}
                              onClick={() => void removeItem(item, i)}
                              className="inline-flex items-center gap-1 text-[var(--danger)] hover:underline disabled:opacity-40"
                              title={
                                kind === 'revenue' && item.enquiryId && !item.id
                                  ? 'Remove this order payment from revenue'
                                  : 'Delete'
                              }
                            >
                              <Trash2 size={14} />
                              Delete
                            </button>
                          </td>
                        </tr>
                      );
                    })}
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

      {preview && (
        <div
          className="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-black/60"
          role="dialog"
          aria-modal="true"
          aria-label="Document preview"
          onClick={closePreview}
        >
          <div
            className="w-full max-w-4xl max-h-[90vh] bg-[var(--card)] rounded-xl overflow-hidden shadow-2xl flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-[var(--border)]">
              <p className="font-medium truncate">{preview.name}</p>
              <button
                type="button"
                onClick={closePreview}
                className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)]"
                aria-label="Close preview"
              >
                <X size={20} />
              </button>
            </div>
            <div className="flex-1 min-h-[50vh] bg-[var(--background)]">
              {preview.type.startsWith('image/') ? (
                <img src={preview.url} alt={preview.name} className="max-h-[75vh] mx-auto object-contain p-4" />
              ) : preview.type.includes('pdf') ? (
                <iframe title={preview.name} src={preview.url} className="w-full h-[75vh] border-0" />
              ) : (
                <div className="p-8 text-center space-y-3">
                  <p className="text-sm text-[var(--muted)]">Preview not available for this file type.</p>
                  <a
                    href={preview.url}
                    download={preview.name}
                    className="inline-flex text-sm text-[var(--primary)] hover:underline"
                  >
                    Download instead
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
