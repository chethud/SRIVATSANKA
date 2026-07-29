import { useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, ChevronRight, Upload, X } from 'lucide-react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { AttentionBadge } from '../components/AttentionBadge';
import { OrderScheduleBadge } from '../components/OrderScheduleBadge';
import { FilterChips } from '../components/ui';
import { useAppData } from '../context/AppDataContext';
import {
  formatDate,
  importOrderExcel,
  recognizeOrderExcel,
  type OrderExcelRecognizePreview,
} from '../api/client';
import { isUnviewedOrder, sortOrdersForAttention } from '../utils/attention';
import { MONTH_FILTERS, matchesMonthFilter } from '../utils/monthFilter';
import { isOrderCompleted, sortOrdersBySchedule } from '../utils/orderSchedule';
import { buildSerialNumberMap } from '../utils/serialNumbers';

const SCHEDULE_FILTERS = [
  { id: 'ALL', label: 'All orders' },
  { id: 'UPCOMING', label: 'Upcoming' },
  { id: 'COMPLETED', label: 'Completed' },
];

export default function OrdersPage() {
  const { enquiries, refresh } = useAppData();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attentionOnly = searchParams.get('attention') === '1';
  const [monthFilter, setMonthFilter] = useState('ALL');
  const [scheduleFilter, setScheduleFilter] = useState('ALL');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [recognizing, setRecognizing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [preview, setPreview] = useState<OrderExcelRecognizePreview | null>(null);
  const [importMode, setImportMode] = useState<'new' | 'existing'>('new');
  const [existingOrderId, setExistingOrderId] = useState('');
  const [importError, setImportError] = useState('');

  const allOrders = useMemo(
    () => enquiries.filter((e) => e.status === 'CONVERTED'),
    [enquiries],
  );

  const serialNumbers = useMemo(() => buildSerialNumberMap(allOrders), [allOrders]);

  const unviewedOrders = useMemo(
    () => sortOrdersForAttention(allOrders.filter(isUnviewedOrder)),
    [allOrders],
  );

  const orders = useMemo(() => {
    let list = attentionOnly ? unviewedOrders : allOrders;
    list = list.filter((e) => matchesMonthFilter(e.createdAt, monthFilter));
    if (scheduleFilter === 'UPCOMING') {
      list = list.filter((e) => !isOrderCompleted(e.eventDate));
    } else if (scheduleFilter === 'COMPLETED') {
      list = list.filter((e) => isOrderCompleted(e.eventDate));
    }
    list = attentionOnly ? sortOrdersForAttention(list) : sortOrdersBySchedule(list);
    return list;
  }, [allOrders, attentionOnly, unviewedOrders, monthFilter, scheduleFilter]);

  async function handleExcelSelect(file: File) {
    setRecognizing(true);
    setImportError('');
    try {
      const result = await recognizeOrderExcel(file);
      setPreview(result);
      setImportMode('new');
      setExistingOrderId(allOrders[0]?.id ?? '');
    } catch (err) {
      setPreview(null);
      setImportError(err instanceof Error ? err.message : 'Could not read this Excel file.');
    } finally {
      setRecognizing(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  function resetImportFlow() {
    setPreview(null);
    setImportMode('new');
    setExistingOrderId('');
    setImportError('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function submitImport() {
    if (!preview || importing) return;
    if (importMode === 'existing' && !existingOrderId) {
      setImportError('Choose an existing order to replace.');
      return;
    }
    setImporting(true);
    setImportError('');
    try {
      const result = await importOrderExcel({
        mode: importMode,
        existingEnquiryId: importMode === 'existing' ? existingOrderId : undefined,
        order: preview.order,
      });
      await refresh();
      resetImportFlow();
      navigate(`/orders/${result.order.id}`);
    } catch (err) {
      setImportError(err instanceof Error ? err.message : 'Could not import this Excel file.');
    } finally {
      setImporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Orders"
        description={
          attentionOnly
            ? `${orders.length} new ${orders.length === 1 ? 'order needs' : 'orders need'} your attention`
            : undefined
        }
      />
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx"
        className="hidden"
        disabled={recognizing || importing}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleExcelSelect(file);
        }}
      />
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={recognizing || importing}
        >
          <Upload size={16} className="mr-2 inline" />
          {recognizing ? 'Reading Excel…' : 'Import Excel'}
        </Button>
        <p className="text-sm text-[var(--muted)]">
          Upload an Excel file and create a new order or replace an existing one automatically.
        </p>
      </div>
      {preview && (
        <Card className="p-5 sm:p-6 mb-6 w-full">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold">Review imported Excel</h3>
              <p className="text-sm text-[var(--muted)] mt-1">
                File: <span className="text-[var(--foreground)] font-medium">{preview.fileName}</span>
                {' '}· Layout: <span className="text-[var(--foreground)] font-medium">{preview.layout.replace('_', ' ')}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={resetImportFlow}
              className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)]"
              aria-label="Close import preview"
            >
              <X size={18} />
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-5">
            <div className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4">
              <p className="text-xs uppercase tracking-wide font-semibold text-[var(--muted)] mb-3">Imported summary</p>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--muted)]">Customer</dt>
                  <dd className="text-right font-medium">{preview.order.customerName}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--muted)]">Event</dt>
                  <dd className="text-right font-medium">{preview.order.eventType}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--muted)]">Location</dt>
                  <dd className="text-right font-medium">{preview.order.eventLocation}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--muted)]">Sessions</dt>
                  <dd className="text-right font-medium">{preview.order.menuColumns.length}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--muted)]">Menu items</dt>
                  <dd className="text-right font-medium">{preview.order.dishes.length}</dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-[var(--muted)]">Extras</dt>
                  <dd className="text-right font-medium">{preview.order.extraItems.length}</dd>
                </div>
              </dl>
            </div>

            <div className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4">
              <p className="text-xs uppercase tracking-wide font-semibold text-[var(--muted)] mb-3">Import target</p>
              <div className="space-y-3">
                <label className="flex items-start gap-3 text-sm">
                  <input
                    type="radio"
                    name="import-mode"
                    checked={importMode === 'new'}
                    onChange={() => setImportMode('new')}
                    className="mt-0.5"
                  />
                  <span>
                    <span className="font-medium block">Create new order</span>
                    <span className="text-[var(--muted)]">Create a converted order directly from this Excel data.</span>
                  </span>
                </label>
                <label className="flex items-start gap-3 text-sm">
                  <input
                    type="radio"
                    name="import-mode"
                    checked={importMode === 'existing'}
                    onChange={() => setImportMode('existing')}
                    className="mt-0.5"
                  />
                  <span className="flex-1 min-w-0">
                    <span className="font-medium block">Replace existing order</span>
                    <span className="text-[var(--muted)] block mb-2">Overwrite the order’s current menu, sessions, and extras.</span>
                    <select
                      value={existingOrderId}
                      onChange={(e) => setExistingOrderId(e.target.value)}
                      disabled={importMode !== 'existing'}
                      className="form-select w-full px-3 py-2 rounded-lg text-sm"
                    >
                      <option value="">Choose existing order</option>
                      {allOrders.map((order) => (
                        <option key={order.id} value={order.id}>
                          {order.customerName} · {formatDate(order.eventDate)}
                        </option>
                      ))}
                    </select>
                  </span>
                </label>
              </div>
            </div>
          </div>

          {preview.warnings.length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
              <p className="text-sm font-medium flex items-center gap-2 mb-2">
                <AlertTriangle size={16} />
                Import warnings
              </p>
              <ul className="text-sm text-[var(--muted)] space-y-1">
                {preview.warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>• {warning}</li>
                ))}
              </ul>
            </div>
          )}

          {importMode === 'existing' && (
            <p className="mt-4 text-sm text-[var(--danger)]">
              Replacing an existing order will overwrite its current imported menu/session/extras data.
            </p>
          )}

          {importError && <p className="mt-4 text-sm text-[var(--danger)]">{importError}</p>}

          <div className="mt-5 flex flex-wrap gap-3">
            <Button type="button" onClick={() => void submitImport()} disabled={importing || recognizing}>
              {importing ? 'Importing…' : importMode === 'existing' ? 'Replace order from Excel' : 'Create order from Excel'}
            </Button>
            <button
              type="button"
              onClick={resetImportFlow}
              className="px-4 py-2.5 rounded-xl border border-[var(--border)] text-sm font-medium hover:bg-[var(--sidebar-hover)]"
            >
              Cancel
            </button>
          </div>
        </Card>
      )}
      {importError && !preview && (
        <p className="mb-6 text-sm text-[var(--danger)]">{importError}</p>
      )}
      <div className="flex flex-col gap-3 mb-6">
        <FilterChips options={SCHEDULE_FILTERS} selected={scheduleFilter} onSelect={setScheduleFilter} />
        <FilterChips options={MONTH_FILTERS} selected={monthFilter} onSelect={setMonthFilter} />
      </div>
      {orders.length === 0 ? (
        <EmptyState
          message={
            attentionOnly
              ? 'No new orders waiting — all caught up.'
              : 'No orders match your filters.'
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          {orders.map((e) => {
            const unread = isUnviewedOrder(e);
            const serial = serialNumbers.get(e.id);
            const completed = isOrderCompleted(e.eventDate);
            return (
              <Link key={e.id} to={`/orders/${e.id}`} className="block">
                <Card
                  className={`relative p-5 hover:border-[var(--primary)] transition-colors flex items-center justify-between gap-4 ${
                    unread ? 'attention-unread' : completed ? 'opacity-90' : ''
                  }`}
                >
                  <OrderScheduleBadge
                    eventDate={e.eventDate}
                    className="absolute top-3 right-12 sm:right-14"
                  />
                  <div className="min-w-0 pr-24 sm:pr-28">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-[var(--muted)] tabular-nums">#{serial}</span>
                      <h3 className="font-semibold">{e.customerName}</h3>
                      {unread && <AttentionBadge label="New order" />}
                    </div>
                    <p className="text-sm text-[var(--muted)]">
                      {e.eventType} · {formatDate(e.eventDate)}
                    </p>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      {(e.dishes?.length ?? 0)} menu items
                      {unread ? ' · Not opened yet' : completed ? ' · Event finished' : ''}
                    </p>
                  </div>
                  <ChevronRight className="text-[var(--muted)] shrink-0" size={20} />
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
