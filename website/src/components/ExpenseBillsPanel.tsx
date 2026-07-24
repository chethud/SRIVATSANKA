import { useEffect, useState } from 'react';
import { Eye, FileText, Trash2, X } from 'lucide-react';
import type { ChartMoneyItem } from '../api/client';
import {
  deleteUpload,
  downloadUploadFile,
  fetchUploadBlobUrl,
  formatCurrency,
} from '../api/client';
import { Card } from './Layout';

function previewMediaType(contentType: string, fileName: string): string {
  const type = (contentType || '').toLowerCase().split(';')[0].trim();
  if (type.startsWith('image/') || type.includes('pdf')) return type;
  const lower = fileName.toLowerCase();
  if (lower.endsWith('.pdf')) return 'application/pdf';
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
  if (lower.endsWith('.webp')) return 'image/webp';
  if (lower.endsWith('.gif')) return 'image/gif';
  return type || 'application/octet-stream';
}

export function ExpenseBillsPanel({
  items,
  highlightId,
  onChanged,
}: {
  items: ChartMoneyItem[];
  highlightId?: string | null;
  onChanged?: () => void | Promise<void>;
}) {
  const [rows, setRows] = useState(items);
  const [preview, setPreview] = useState<{ url: string; name: string; type: string } | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    setRows(items);
  }, [items]);

  useEffect(() => {
    if (!highlightId || items.length === 0) return;
    const match = items.find((i) => i.id === highlightId);
    if (!match) return;
    document.getElementById(`expense-${highlightId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    void viewDoc(match);
    // Auto-open document when deep-linked; avoid re-opening on every item refresh
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlightId, items.length]);

  const total = rows.reduce((sum, e) => sum + (e.amount ?? 0), 0);

  async function viewDoc(item: ChartMoneyItem) {
    if (!item.id) return;
    setBusyId(item.id);
    try {
      const { url, contentType, fileName } = await fetchUploadBlobUrl(item.id);
      const name = fileName || item.fileName || 'Document';
      setPreview({ url, name, type: previewMediaType(contentType, name) });
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
    if (!item.id) return;
    if (!window.confirm('Delete this expense? This cannot be undone.')) return;
    setBusyId(item.id);
    try {
      await deleteUpload(item.id);
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
      <Card className="overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--border)] flex flex-wrap items-end justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold">Uploaded expenses</h2>
            <p className="text-sm text-[var(--muted)]">
              {rows.length === 0
                ? 'No expense bills yet'
                : `${rows.length} bill${rows.length === 1 ? '' : 's'} · ${formatCurrency(total)} total`}
            </p>
          </div>
        </div>

        {rows.length === 0 ? (
          <p className="text-sm text-[var(--muted)] text-center py-10 px-4">
            Upload a photo or PDF above to record an expense bill.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-[var(--muted)] uppercase tracking-wide border-b border-[var(--border)]">
                  <th className="px-5 py-3 font-medium">Date</th>
                  <th className="px-3 py-3 font-medium">Description</th>
                  <th className="px-3 py-3 font-medium">Purpose</th>
                  <th className="px-3 py-3 font-medium">Document</th>
                  <th className="px-3 py-3 text-right font-medium">Amount</th>
                  <th className="px-5 py-3 text-right font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((item, i) => (
                  <tr
                    key={item.id || `${item.label}-${item.date}-${i}`}
                    id={item.id ? `expense-${item.id}` : undefined}
                    className={`border-b border-[var(--border)]/60 last:border-0 ${
                      highlightId && item.id === highlightId ? 'bg-[var(--primary-light)]' : ''
                    }`}
                  >
                    <td className="px-5 py-3 text-[var(--muted)] whitespace-nowrap">{item.date ?? '—'}</td>
                    <td className="px-3 py-3 font-medium">{item.label}</td>
                    <td className="px-3 py-3 text-[var(--muted)]">{item.purpose || '—'}</td>
                    <td className="px-3 py-3">
                      {item.id ? (
                        <div className="flex flex-wrap items-center gap-2">
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
                            <span className="truncate max-w-[120px]">{item.fileName || 'Download'}</span>
                          </button>
                        </div>
                      ) : (
                        <span className="text-[var(--muted)]">—</span>
                      )}
                    </td>
                    <td className="px-3 py-3 text-right tabular-nums font-semibold text-amber-900">
                      {formatCurrency(item.amount)}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        type="button"
                        disabled={!item.id || busyId === item.id}
                        onClick={() => void removeItem(item, i)}
                        className="inline-flex items-center gap-1 text-[var(--danger)] hover:underline disabled:opacity-40"
                      >
                        <Trash2 size={14} />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

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
