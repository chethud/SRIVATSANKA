import { useMemo, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Check, ChevronRight, Pencil, Trash2, Upload, X } from 'lucide-react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { AttentionBadge } from '../components/AttentionBadge';
import { OrderScheduleBadge } from '../components/OrderScheduleBadge';
import { FilterToolbar } from '../components/ui';
import { useAppData } from '../context/AppDataContext';
import {
  createEnquiry,
  deleteEnquiry,
  formatDate,
  importOrderExcel,
  recognizeOrderExcel,
  updateEnquiry,
  updateEnquiryStatus,
  type Enquiry,
  type OrderExcelRecognizePreview,
} from '../api/client';
import { CustomerEventFormFields } from '../components/CustomerEventFormFields';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { emptyCustomerEventForm } from '../utils/eventTypes';
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
  const [importPhone, setImportPhone] = useState('');
  const [deletingId, setDeletingId] = useState('');
  const [editingId, setEditingId] = useState('');
  const [editingName, setEditingName] = useState('');
  const [savingNameId, setSavingNameId] = useState('');
  const [showNewOrderForm, setShowNewOrderForm] = useState(false);
  const [newOrderForm, setNewOrderForm] = useState(emptyCustomerEventForm);
  const [newOrderSaving, setNewOrderSaving] = useState(false);
  const [newOrderError, setNewOrderError] = useState('');

  useCreateActionListener('order', () => setShowNewOrderForm(true));

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
      setImportPhone(result.order.phoneNumber ?? '');
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

  async function handleDeleteOrder(order: Enquiry) {
    if (deletingId) return;
    const ok = window.confirm(
      `Delete this order for ${order.customerName}?\n\nThis permanently removes the order, menu, payments, and related files. This cannot be undone.`,
    );
    if (!ok) return;
    setDeletingId(order.id);
    try {
      await deleteEnquiry(order.id);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not delete the order. Please try again.');
    } finally {
      setDeletingId('');
    }
  }

  function startEditingName(order: Enquiry) {
    setEditingId(order.id);
    setEditingName(order.customerName);
  }

  function cancelEditingName() {
    setEditingId('');
    setEditingName('');
  }

  async function handleSaveName(order: Enquiry) {
    const trimmed = editingName.trim();
    if (!trimmed || savingNameId) return;
    if (trimmed === order.customerName) {
      cancelEditingName();
      return;
    }
    setSavingNameId(order.id);
    try {
      await updateEnquiry(order.id, { customerName: trimmed });
      await refresh();
      cancelEditingName();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not update the order name. Please try again.');
    } finally {
      setSavingNameId('');
    }
  }

  function resetImportFlow() {
    setPreview(null);
    setImportMode('new');
    setExistingOrderId('');
    setImportError('');
    setImportPhone('');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleCreateOrder(e: FormEvent) {
    e.preventDefault();
    setNewOrderSaving(true);
    setNewOrderError('');
    try {
      const eventDate = new Date(`${newOrderForm.eventDate}T12:00:00`);
      const preferredCallbackAt = new Date(newOrderForm.preferredCallbackAt);
      if (Number.isNaN(eventDate.getTime()) || Number.isNaN(preferredCallbackAt.getTime())) {
        setNewOrderError('Enter a valid event date and callback time.');
        return;
      }
      const created = await createEnquiry({
        customerName: newOrderForm.customerName.trim(),
        phoneNumber: newOrderForm.phoneNumber.trim(),
        eventType: newOrderForm.eventType,
        eventDate: eventDate.toISOString(),
        eventLocation: newOrderForm.eventLocation.trim(),
        guestCount: 0,
        preferredCallbackAt: preferredCallbackAt.toISOString(),
        notes: 'Order created manually by admin',
        adminNote: newOrderForm.adminNote.trim() || undefined,
      });
      const converted = await updateEnquiryStatus(created.id, 'CONVERTED');
      setNewOrderForm(emptyCustomerEventForm());
      setShowNewOrderForm(false);
      await refresh();
      navigate(`/orders/${converted.id}`);
    } catch (err) {
      setNewOrderError(err instanceof Error ? err.message : 'Could not create order.');
    } finally {
      setNewOrderSaving(false);
    }
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
        order: { ...preview.order, phoneNumber: importPhone.trim() },
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
      {newOrderError && (
        <p className="text-sm text-[var(--danger)] mb-4">{newOrderError}</p>
      )}
      {showNewOrderForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <h3 className="font-semibold mb-4 text-[var(--foreground)]">New order</h3>
          <p className="text-sm text-[var(--muted)] mb-4">
            Creates a converted order immediately — add menu, venue, and payments on the order page.
          </p>
          <form onSubmit={handleCreateOrder} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CustomerEventFormFields form={newOrderForm} setForm={setNewOrderForm} />
            <div className="md:col-span-2 flex gap-3">
              <Button type="submit" disabled={newOrderSaving}>
                {newOrderSaving ? 'Creating…' : 'Create order'}
              </Button>
              <button
                type="button"
                onClick={() => {
                  setShowNewOrderForm(false);
                  setNewOrderError('');
                }}
                className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <Button type="button" onClick={() => setShowNewOrderForm(true)} disabled={newOrderSaving}>
          New order
        </Button>
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
                <div className="flex flex-col gap-1.5 sm:flex-row sm:justify-between sm:items-center">
                  <dt className="text-[var(--muted)]">Contact phone</dt>
                  <dd className="sm:text-right">
                    <input
                      type="tel"
                      value={importPhone}
                      onChange={(e) => setImportPhone(e.target.value)}
                      className="form-input w-full sm:w-48 px-2 py-1.5 rounded-lg text-sm tabular-nums"
                      placeholder="Phone number"
                    />
                  </dd>
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
      <FilterToolbar
        sections={[
          { label: 'Orders', options: SCHEDULE_FILTERS, selected: scheduleFilter, onSelect: setScheduleFilter },
          { label: 'Period', options: MONTH_FILTERS, selected: monthFilter, onSelect: setMonthFilter },
        ]}
      />
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
            const deleting = deletingId === e.id;
            const editing = editingId === e.id;
            const savingName = savingNameId === e.id;
            return (
              <Card
                key={e.id}
                className={`w-full self-stretch p-5 hover:border-[var(--primary)] transition-colors flex items-center justify-between gap-4 ${
                  unread ? 'attention-unread' : completed ? 'opacity-90' : ''
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-[var(--muted)] tabular-nums">#{serial}</span>
                    {editing ? (
                      <div
                        className="flex items-center gap-2 flex-1 min-w-0"
                        onClick={(ev) => ev.stopPropagation()}
                      >
                        <input
                          type="text"
                          value={editingName}
                          onChange={(ev) => setEditingName(ev.target.value)}
                          onKeyDown={(ev) => {
                            if (ev.key === 'Enter') void handleSaveName(e);
                            if (ev.key === 'Escape') cancelEditingName();
                          }}
                          disabled={savingName}
                          autoFocus
                          className="form-input flex-1 min-w-0 px-3 py-1.5 rounded-lg text-sm font-semibold"
                          aria-label={`Edit order name for ${e.customerName}`}
                        />
                        <button
                          type="button"
                          disabled={savingName || !editingName.trim()}
                          onClick={() => void handleSaveName(e)}
                          className="inline-flex items-center justify-center p-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--foreground)] hover:bg-[var(--sidebar-hover)] disabled:opacity-60"
                          aria-label="Save order name"
                        >
                          <Check size={14} />
                        </button>
                        <button
                          type="button"
                          disabled={savingName}
                          onClick={cancelEditingName}
                          className="inline-flex items-center justify-center p-2 rounded-lg border border-[var(--border)] bg-[var(--card)] text-[var(--muted)] hover:bg-[var(--sidebar-hover)] disabled:opacity-60"
                          aria-label="Cancel editing order name"
                        >
                          <X size={14} />
                        </button>
                      </div>
                    ) : (
                      <>
                        <Link to={`/orders/${e.id}`} className="font-semibold hover:text-[var(--primary)] break-words">
                          {e.customerName}
                        </Link>
                        <button
                          type="button"
                          onClick={() => startEditingName(e)}
                          className="inline-flex items-center justify-center p-1.5 rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--sidebar-hover)]"
                          aria-label={`Edit order name for ${e.customerName}`}
                        >
                          <Pencil size={14} />
                        </button>
                      </>
                    )}
                    {unread ? <AttentionBadge label="New order" /> : null}
                  </div>
                  <Link to={`/orders/${e.id}`} className="block">
                    <p className="text-sm text-[var(--muted)]">
                      {e.eventType} · {formatDate(e.eventDate)}
                    </p>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      {(e.dishes?.length ?? 0)} menu items
                      {unread ? ' · Not opened yet' : completed ? ' · Event finished' : ''}
                    </p>
                  </Link>
                </div>
                <div className="flex flex-col items-end gap-2 shrink-0 self-stretch justify-center">
                  <OrderScheduleBadge eventDate={e.eventDate} />
                  <div className="flex items-center gap-1">
                    <button
                      type="button"
                      disabled={Boolean(deletingId)}
                      onClick={() => void handleDeleteOrder(e)}
                      className="inline-flex items-center gap-1.5 px-2.5 py-2 text-xs font-semibold rounded-lg border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-60 min-h-[2.5rem]"
                      aria-label={`Delete order for ${e.customerName}`}
                    >
                      <Trash2 size={14} />
                      <span className="hidden sm:inline">{deleting ? 'Deleting…' : 'Delete'}</span>
                    </button>
                    <Link
                      to={`/orders/${e.id}`}
                      className="p-1 text-[var(--muted)] hover:text-[var(--foreground)]"
                      aria-label={`Open order for ${e.customerName}`}
                    >
                      <ChevronRight size={20} />
                    </Link>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </>
  );
}
