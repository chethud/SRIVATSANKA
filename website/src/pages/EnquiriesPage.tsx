import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { MessageCircle, Trash2, X } from 'lucide-react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { AttentionBadge } from '../components/AttentionBadge';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, FilterToolbar, LoadingScreen } from '../components/ui';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { usePageSearch } from '../context/PageSearchContext';
import {
  createEnquiry,
  deleteEnquiry,
  updateEnquiry,
  updateEnquiryStatus,
  retryOwnerNotification,
  formatDate,
  formatDateTime,
  type Enquiry,
} from '../api/client';
import { CustomerEventFormFields } from '../components/CustomerEventFormFields';
import { emptyCustomerEventForm } from '../utils/eventTypes';
import { isUnviewedEnquiry, sortEnquiriesForAttention } from '../utils/attention';
import { ENQUIRY_STATUS_FILTERS, statusOptionsForDropdown } from '../utils/enquiryStatus';
import { MONTH_FILTERS, matchesMonthFilter } from '../utils/monthFilter';
import { buildSerialNumberMap } from '../utils/serialNumbers';
import { PREFERENCE_CATEGORIES } from '../utils/mealSessions';

function callbackDisplay(enquiry: { preferredCallbackAt: string; notes?: string | null }) {
  const when = formatDateTime(enquiry.preferredCallbackAt);
  const requested = enquiry.notes
    ?.split('\n')
    .find((line) => line.startsWith('Callback requested: '))
    ?.slice('Callback requested: '.length)
    .trim();
  return requested ? `${when} (${requested})` : when;
}

function normalizePhoneDigits(value: string): string {
  return value.replace(/\D/g, '');
}

export default function EnquiriesPage() {
  const { loading, error, enquiries, refresh, markEnquiryViewed } = useAppData();
  const [searchParams] = useSearchParams();
  const attentionOnly = searchParams.get('attention') === '1';
  const deepLinkId = searchParams.get('id');
  const deepLinkPhone = normalizePhoneDigits(searchParams.get('phone') || '');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [monthFilter, setMonthFilter] = useState('ALL');
  const [selected, setSelected] = useState<string | null>(null);
  const markedSeenRef = useRef(new Set<string>());
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyCustomerEventForm);
  const [adminNoteDraft, setAdminNoteDraft] = useState('');
  const [savingAdminNote, setSavingAdminNote] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [retryMsg, setRetryMsg] = useState('');
  const [deletingId, setDeletingId] = useState('');

  useCreateActionListener('enquiry', () => setShowForm(true));
  usePageSearch('Search name, event, phone...', search, setSearch);

  const serialNumbers = useMemo(() => buildSerialNumberMap(enquiries), [enquiries]);

  useEffect(() => {
    if (deepLinkId && enquiries.some((e) => e.id === deepLinkId)) {
      setSelected(deepLinkId);
      return;
    }
    if (deepLinkPhone) {
      const match = enquiries.find((e) => normalizePhoneDigits(e.phoneNumber) === deepLinkPhone);
      if (match) {
        setSelected(match.id);
        setSearch(deepLinkPhone.slice(-10));
      }
    }
  }, [deepLinkId, deepLinkPhone, enquiries]);

  const filtered = useMemo(() => {
    let list = enquiries.filter((e) => {
      const matchStatus =
        statusFilter === 'ALL' ||
        e.status === statusFilter ||
        (statusFilter === 'NOT_CONVERTED' && e.status === 'CLOSED');
      const matchMonth = matchesMonthFilter(e.createdAt, monthFilter);
      const q = search.toLowerCase();
      const matchSearch =
        !q ||
        e.customerName.toLowerCase().includes(q) ||
        e.eventType.toLowerCase().includes(q) ||
        e.phoneNumber.includes(q) ||
        e.eventLocation.toLowerCase().includes(q);
      return matchStatus && matchMonth && matchSearch;
    });
    if (attentionOnly) {
      list = list.filter(isUnviewedEnquiry);
    }
    return sortEnquiriesForAttention(list);
  }, [enquiries, search, statusFilter, monthFilter, attentionOnly]);

  const detail = enquiries.find((e) => e.id === selected);

  useEffect(() => {
    if (detail) setAdminNoteDraft(detail.adminNote ?? '');
  }, [detail?.id, detail?.adminNote]);
  const cuisinePreferences = useMemo(
    () => (detail?.dishes ?? []).filter((d) => PREFERENCE_CATEGORIES.has(d.category)),
    [detail],
  );

  function handleRowHover(enquiry: (typeof enquiries)[0]) {
    if (!isUnviewedEnquiry(enquiry) || markedSeenRef.current.has(enquiry.id)) return;
    markedSeenRef.current.add(enquiry.id);
    void markEnquiryViewed(enquiry.id);
  }

  async function changeStatus(id: string, status: string) {
    await updateEnquiryStatus(id, status);
    refresh();
  }

  async function handleDeleteEnquiry(enquiry: Enquiry) {
    if (deletingId) return;
    const ok = window.confirm(
      `Delete enquiry for ${enquiry.customerName}?\n\nThis permanently removes the enquiry and related dishes, payments, and notifications. This cannot be undone.`,
    );
    if (!ok) return;
    setDeletingId(enquiry.id);
    try {
      await deleteEnquiry(enquiry.id);
      if (selected === enquiry.id) setSelected(null);
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not delete the enquiry. Please try again.');
    } finally {
      setDeletingId('');
    }
  }

  async function retryAlert(id: string) {
    setRetryingId(id);
    setRetryMsg('');
    try {
      await retryOwnerNotification(id);
      setRetryMsg('Owner alert sent.');
      await refresh();
    } catch (err) {
      setRetryMsg(err instanceof Error ? err.message : 'Retry failed.');
    } finally {
      setRetryingId(null);
    }
  }

  function notificationFailed(enquiry: (typeof enquiries)[0]) {
    return (enquiry.notificationStatus || '').toLowerCase() === 'failed';
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      const eventDate = new Date(`${form.eventDate}T12:00:00`);
      const preferredCallbackAt = new Date(form.preferredCallbackAt);
      if (Number.isNaN(eventDate.getTime()) || Number.isNaN(preferredCallbackAt.getTime())) {
        setFormError('Enter a valid event date and preferred callback time.');
        return;
      }
      const created = await createEnquiry({
        customerName: form.customerName.trim(),
        phoneNumber: form.phoneNumber.trim(),
        eventType: form.eventType,
        eventDate: eventDate.toISOString(),
        eventLocation: form.eventLocation.trim(),
        guestCount: 0,
        preferredCallbackAt: preferredCallbackAt.toISOString(),
        notes: 'Created manually by owner',
        adminNote: form.adminNote.trim() || undefined,
      });
      setForm(emptyCustomerEventForm());
      setShowForm(false);
      setSelected(created.id);
      await refresh();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Could not save enquiry. Check API connection.');
    } finally {
      setSaving(false);
    }
  }

  if (loading && enquiries.length === 0) return <LoadingScreen />;

  return (
    <>
      <PageHeader
        title="Enquiries"
        description={
          attentionOnly
            ? `${filtered.length} new ${filtered.length === 1 ? 'enquiry needs' : 'enquiries need'} your attention`
            : `${filtered.length} enquiries — add manually or from WhatsApp; mark CONVERTED when confirmed`
        }
      />
      <ErrorBanner message={error || formError} />
      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <h3 className="font-semibold mb-4 text-[var(--foreground)]">New enquiry (owner)</h3>
          <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CustomerEventFormFields form={form} setForm={setForm} />
            <div className="md:col-span-2 flex gap-3">
              <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save enquiry'}</Button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setFormError(''); }}
                className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl text-[var(--foreground)] hover:bg-[var(--sidebar-hover)]"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}
      <FilterToolbar
        sections={[
          { label: 'Period', options: MONTH_FILTERS, selected: monthFilter, onSelect: setMonthFilter },
          { label: 'Status', options: ENQUIRY_STATUS_FILTERS, selected: statusFilter, onSelect: setStatusFilter },
        ]}
      />

      {filtered.length === 0 ? (
        <EmptyState message={attentionOnly ? 'No new enquiries waiting — all caught up.' : 'No enquiries match your filters.'} />
      ) : (
        <>
          {/* Mobile / tablet: stacked cards */}
          <div className="space-y-3 md:hidden">
            {filtered.map((e) => {
              const unread = isUnviewedEnquiry(e);
              const serial = serialNumbers.get(e.id);
              return (
                <div
                  key={e.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => {
                    setSelected(e.id);
                    handleRowHover(e);
                  }}
                  onKeyDown={(ev) => {
                    if (ev.key === 'Enter' || ev.key === ' ') {
                      ev.preventDefault();
                      setSelected(e.id);
                      handleRowHover(e);
                    }
                  }}
                  className={`w-full text-left rounded-xl border p-4 shadow-sm transition-colors cursor-pointer ${
                    unread
                      ? 'attention-unread-row border-[var(--attention-border)]'
                      : 'border-[var(--border)] bg-[var(--card)]'
                  }`}
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-[var(--muted)] tabular-nums">#{serial}</span>
                      <span className="font-semibold text-[var(--foreground)] break-words">{e.customerName}</span>
                      {unread && <AttentionBadge />}
                      {notificationFailed(e) && (
                        <span className="text-[10px] font-semibold uppercase tracking-wide text-red-600">
                          Owner notification failed
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[var(--muted)] mt-1 break-all">{e.phoneNumber}</p>
                    <p className="text-sm mt-2 text-[var(--foreground)]">{e.eventType}</p>
                    {unread && (
                      <p className="text-xs text-[var(--primary)] mt-1">
                        Callback: {formatDateTime(e.preferredCallbackAt)}
                      </p>
                    )}
                  </div>
                  <div className="mt-3 pt-3 border-t border-[var(--border)]" onClick={(ev) => ev.stopPropagation()}>
                    <label className="text-[10px] uppercase tracking-wide text-[var(--muted)] font-semibold">Status</label>
                    <select
                      value={e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status}
                      onChange={(ev) => changeStatus(e.id, ev.target.value)}
                      className="form-select mt-1 w-full text-sm px-3 py-2.5 rounded-lg min-h-[2.5rem]"
                    >
                      {statusOptionsForDropdown(e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status).map((s) => (
                        <option key={s.id} value={s.id}>{s.label}</option>
                      ))}
                    </select>
                    <button
                      type="button"
                      disabled={Boolean(deletingId)}
                      onClick={() => void handleDeleteEnquiry(e)}
                      className="mt-2 inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-60"
                      aria-label={`Delete enquiry for ${e.customerName}`}
                      title="Delete"
                    >
                      <Trash2 size={11} />
                      {deletingId === e.id ? '…' : 'Delete'}
                    </button>
                  </div>
                  <p className="text-xs text-[var(--primary)] mt-3 font-medium">Tap for full details</p>
                </div>
              );
            })}
          </div>

          {/* Desktop table */}
          <div className="hidden md:block bg-[var(--card)] border border-[var(--border)] rounded-xl shadow-sm overflow-x-auto">
            <table className="w-full text-sm min-w-[36rem]">
              <thead className="bg-[var(--background)]">
                <tr>
                  <th className="text-left p-4 w-12">#</th>
                  <th className="text-left p-4">Customer</th>
                  <th className="text-left p-4">Event</th>
                  <th className="text-left p-4 min-w-[9rem]">Status</th>
                  <th className="text-left p-4 w-14"> </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => {
                  const unread = isUnviewedEnquiry(e);
                  const serial = serialNumbers.get(e.id);
                  return (
                  <tr
                    key={e.id}
                    onClick={() => {
                      setSelected(e.id);
                      handleRowHover(e);
                    }}
                    onMouseEnter={() => handleRowHover(e)}
                    className={`border-t border-[var(--border)] cursor-pointer hover:bg-[var(--background)] ${
                      unread ? 'attention-unread-row' : ''
                    }`}
                  >
                    <td className="p-4 text-[var(--muted)] font-medium tabular-nums">{serial}</td>
                    <td className="p-4 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium break-words">{e.customerName}</span>
                        {unread && <AttentionBadge />}
                        {notificationFailed(e) && (
                          <span className="text-[10px] font-semibold uppercase tracking-wide text-red-600">
                            Owner notification failed
                          </span>
                        )}
                      </div>
                      <div className="text-[var(--muted)] text-xs break-all">{e.phoneNumber}</div>
                      {unread && (
                        <div className="text-xs text-[var(--primary)] mt-1">
                          Callback: {formatDateTime(e.preferredCallbackAt)}
                        </div>
                      )}
                    </td>
                    <td className="p-4 whitespace-nowrap">{e.eventType}</td>
                    <td className="p-4" onClick={(ev) => ev.stopPropagation()}>
                      <select
                        value={e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status}
                        onChange={(ev) => changeStatus(e.id, ev.target.value)}
                        className="form-select text-xs px-2 py-1.5 rounded-lg min-w-[8.5rem] max-w-full"
                      >
                        {statusOptionsForDropdown(e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status).map((s) => (
                          <option key={s.id} value={s.id}>{s.label}</option>
                        ))}
                      </select>
                    </td>
                    <td className="p-4" onClick={(ev) => ev.stopPropagation()}>
                      <button
                        type="button"
                        disabled={Boolean(deletingId)}
                        onClick={() => void handleDeleteEnquiry(e)}
                        className="inline-flex items-center justify-center p-1 rounded border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-60"
                        aria-label={`Delete enquiry for ${e.customerName}`}
                        title={deletingId === e.id ? 'Deleting…' : 'Delete'}
                      >
                        <Trash2 size={12} />
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {detail && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
              role="dialog"
              aria-modal="true"
              aria-labelledby="enquiry-detail-title"
              onClick={() => setSelected(null)}
            >
              <div className="w-full max-w-lg max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
                <Card className="flex flex-col overflow-hidden shadow-xl max-h-[90vh]">
                  <div className="flex items-start justify-between gap-3 p-4 sm:p-5 border-b border-[var(--border)]">
                    <div className="min-w-0 flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-[var(--muted)] tabular-nums">
                        #{serialNumbers.get(detail.id)}
                      </span>
                      <h2 id="enquiry-detail-title" className="font-semibold text-lg break-words">
                        {detail.customerName}
                      </h2>
                      {isUnviewedEnquiry(detail) && <AttentionBadge />}
                      {notificationFailed(detail) && (
                        <span className="text-xs font-semibold text-red-600">Owner notification failed</span>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelected(null)}
                      className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)] shrink-0"
                      aria-label="Close"
                    >
                      <X size={20} />
                    </button>
                  </div>

                  <div className="overflow-y-auto p-4 sm:p-5">
                    <dl className="space-y-3 text-sm">
                      <div>
                        <dt className="text-[var(--muted)]">Phone</dt>
                        <dd className="break-all font-medium">{detail.phoneNumber}</dd>
                      </div>
                      <Link
                        to={`/bot-tester?phone=${encodeURIComponent(detail.phoneNumber)}`}
                        className="inline-flex items-center gap-1.5 text-sm text-[var(--primary)] hover:underline min-h-[2.5rem]"
                        onClick={() => setSelected(null)}
                      >
                        <MessageCircle size={14} />
                        Open WhatsApp chat
                      </Link>
                      <div>
                        <dt className="text-[var(--muted)]">Enquired on</dt>
                        <dd>{formatDateTime(detail.createdAt)}</dd>
                      </div>
                      <div>
                        <dt className="text-[var(--muted)]">Event</dt>
                        <dd>{detail.eventType}</dd>
                      </div>
                      <div>
                        <dt className="text-[var(--muted)]">Event date (occasion)</dt>
                        <dd>{formatDate(detail.eventDate)}</dd>
                      </div>
                      <div>
                        <dt className="text-[var(--muted)]">Location</dt>
                        <dd className="break-words">{detail.eventLocation}</dd>
                      </div>
                      <div>
                        <dt className="text-[var(--muted)]">Callback</dt>
                        <dd className="break-words">
                          {detail.callbackDate || callbackDisplay(detail)}
                          {detail.callbackTime ? ` · ${detail.callbackTime}` : ''}
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[var(--muted)]">Owner WhatsApp alert</dt>
                        <dd className="break-words">
                          {(detail.notificationStatus || 'pending').toUpperCase()}
                          {detail.notificationError ? ` — ${detail.notificationError}` : ''}
                        </dd>
                      </div>
                      {notificationFailed(detail) && (
                        <div className="rounded-lg border border-red-200 bg-red-50 p-3 space-y-2">
                          <p className="text-sm font-semibold text-red-700">Owner notification failed</p>
                          <p className="text-xs text-red-800 break-words">
                            Lead ID: {detail.id}
                            <br />
                            {detail.customerName} · {detail.phoneNumber}
                            <br />
                            {detail.eventType} · {formatDate(detail.eventDate)}
                            <br />
                            {detail.notificationError || 'WhatsApp provider error'}
                          </p>
                          <Button
                            type="button"
                            disabled={retryingId === detail.id}
                            onClick={() => retryAlert(detail.id)}
                          >
                            {retryingId === detail.id ? 'Retrying…' : 'Retry owner alert'}
                          </Button>
                          {retryMsg && <p className="text-xs">{retryMsg}</p>}
                        </div>
                      )}
                      <div>
                        <dt className="text-[var(--muted)] mb-1">Admin note</dt>
                        <dd>
                          <textarea
                            rows={3}
                            value={adminNoteDraft}
                            onChange={(e) => setAdminNoteDraft(e.target.value)}
                            className="form-input w-full px-3 py-2 rounded-lg text-sm resize-y"
                            placeholder="Internal notes for this enquiry"
                          />
                          <button
                            type="button"
                            disabled={savingAdminNote}
                            onClick={async () => {
                              setSavingAdminNote(true);
                              try {
                                await updateEnquiry(detail.id, { adminNote: adminNoteDraft.trim() || null });
                                await refresh();
                              } catch (err) {
                                alert(err instanceof Error ? err.message : 'Could not save note');
                              } finally {
                                setSavingAdminNote(false);
                              }
                            }}
                            className="mt-2 px-3 py-1.5 text-xs font-semibold rounded-lg bg-[var(--primary)] text-white disabled:opacity-60"
                          >
                            {savingAdminNote ? 'Saving…' : 'Save note'}
                          </button>
                        </dd>
                      </div>
                      <div>
                        <dt className="text-[var(--muted)] mb-1">Status</dt>
                        <dd>
                          <select
                            value={detail.status === 'CLOSED' ? 'NOT_CONVERTED' : detail.status}
                            onChange={(ev) => changeStatus(detail.id, ev.target.value)}
                            className="form-select w-full text-sm px-3 py-2.5 rounded-lg min-h-[2.5rem]"
                          >
                            {statusOptionsForDropdown(detail.status === 'CLOSED' ? 'NOT_CONVERTED' : detail.status).map((s) => (
                              <option key={s.id} value={s.id}>{s.label}</option>
                            ))}
                          </select>
                        </dd>
                      </div>
                      <div>
                        <button
                          type="button"
                          disabled={Boolean(deletingId)}
                          onClick={() => void handleDeleteEnquiry(detail)}
                          className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 disabled:opacity-60"
                          aria-label={`Delete enquiry for ${detail.customerName}`}
                          title="Delete enquiry"
                        >
                          <Trash2 size={11} />
                          {deletingId === detail.id ? '…' : 'Delete'}
                        </button>
                      </div>
                      <p className="text-xs text-[var(--muted)] pt-1">Pax is set per meal session on the order menu.</p>
                    </dl>
                    {cuisinePreferences.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-[var(--border)]">
                        <p className="font-medium mb-2">Cuisine preferences</p>
                        <ul className="text-sm space-y-1">
                          {cuisinePreferences.map((d, i) => (
                            <li key={i} className="break-words">
                              • {d.dishName}{' '}
                              {d.customizations && <span className="text-[var(--muted)]">({d.customizations})</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  <div className="p-4 sm:p-5 border-t border-[var(--border)] flex justify-end">
                    <button
                      type="button"
                      onClick={() => setSelected(null)}
                      className="px-4 py-2.5 text-sm font-medium rounded-xl bg-[var(--primary)] text-white min-h-[2.5rem]"
                    >
                      Close
                    </button>
                  </div>
                </Card>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}
