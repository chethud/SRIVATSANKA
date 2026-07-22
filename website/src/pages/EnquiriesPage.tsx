import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { MessageCircle } from 'lucide-react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { AttentionBadge } from '../components/AttentionBadge';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, FilterChips, LoadingScreen } from '../components/ui';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { usePageSearch } from '../context/PageSearchContext';
import { createEnquiry, updateEnquiryStatus, formatDate, formatDateTime } from '../api/client';
import { isUnviewedEnquiry, sortEnquiriesForAttention } from '../utils/attention';
import { ENQUIRY_STATUS_FILTERS, statusOptionsForDropdown } from '../utils/enquiryStatus';
import { MONTH_FILTERS, matchesMonthFilter } from '../utils/monthFilter';
import { buildSerialNumberMap } from '../utils/serialNumbers';
import { PREFERENCE_CATEGORIES } from '../utils/mealSessions';

const EVENT_TYPES = ['Wedding', 'House Warming', 'Baby Shower', 'Reception', 'Corporate Lunch', 'Naming Ceremony', 'Other'];

function defaultEventDate() {
  const d = new Date();
  d.setDate(d.getDate() + 30);
  return d.toISOString().slice(0, 10);
}

function defaultCallbackAt() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  d.setHours(10, 0, 0, 0);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

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

const emptyForm = () => ({
  customerName: '',
  phoneNumber: '',
  eventType: EVENT_TYPES[0],
  eventDate: defaultEventDate(),
  eventLocation: '',
  preferredCallbackAt: defaultCallbackAt(),
});

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
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  useCreateActionListener('enquiry', () => setShowForm(true));
  usePageSearch('Search name, event, phone...', search, setSearch);

  const unviewedEnquiries = useMemo(
    () => sortEnquiriesForAttention(enquiries.filter(isUnviewedEnquiry)),
    [enquiries],
  );

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
  const cuisinePreferences = useMemo(
    () => (detail?.dishes ?? []).filter((d) => PREFERENCE_CATEGORIES.has(d.category)),
    [detail],
  );

  useEffect(() => {
    if (deepLinkId || deepLinkPhone) return;
    if (selected || unviewedEnquiries.length === 0) return;
    setSelected(unviewedEnquiries[0].id);
  }, [unviewedEnquiries, selected, deepLinkId, deepLinkPhone]);

  function handleRowHover(enquiry: (typeof enquiries)[0]) {
    if (!isUnviewedEnquiry(enquiry) || markedSeenRef.current.has(enquiry.id)) return;
    markedSeenRef.current.add(enquiry.id);
    void markEnquiryViewed(enquiry.id);
  }

  async function changeStatus(id: string, status: string) {
    await updateEnquiryStatus(id, status);
    refresh();
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
      });
      setForm(emptyForm());
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
            <input
              required
              placeholder="Customer name"
              value={form.customerName}
              onChange={(e) => setForm({ ...form, customerName: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <input
              required
              placeholder="Phone number"
              value={form.phoneNumber}
              onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <select
              value={form.eventType}
              onChange={(e) => setForm({ ...form, eventType: e.target.value })}
              className="form-select px-3 py-2 rounded-lg"
            >
              {EVENT_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <input
              required
              type="date"
              value={form.eventDate}
              onChange={(e) => setForm({ ...form, eventDate: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <input
              required
              placeholder="Event location"
              value={form.eventLocation}
              onChange={(e) => setForm({ ...form, eventLocation: e.target.value })}
              className="form-input px-3 py-2 rounded-lg md:col-span-2"
            />
            <div className="md:col-span-2">
              <label className="text-xs text-[var(--muted)] block mb-1">Preferred callback</label>
              <input
                required
                type="datetime-local"
                value={form.preferredCallbackAt}
                onChange={(e) => setForm({ ...form, preferredCallbackAt: e.target.value })}
                className="form-input w-full px-3 py-2 rounded-lg"
              />
            </div>
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
      <div className="flex flex-col gap-3 mb-6">
        <FilterChips options={MONTH_FILTERS} selected={monthFilter} onSelect={setMonthFilter} />
        <FilterChips options={ENQUIRY_STATUS_FILTERS} selected={statusFilter} onSelect={setStatusFilter} />
      </div>

      {filtered.length === 0 ? (
        <EmptyState message={attentionOnly ? 'No new enquiries waiting — all caught up.' : 'No enquiries match your filters.'} />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-[var(--background)]">
                <tr>
                  <th className="text-left p-4 w-12">#</th>
                  <th className="text-left p-4">Customer</th>
                  <th className="text-left p-4">Event</th>
                  <th className="text-left p-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => {
                  const unread = isUnviewedEnquiry(e);
                  const serial = serialNumbers.get(e.id);
                  return (
                  <tr
                    key={e.id}
                    onClick={() => setSelected(e.id)}
                    onMouseEnter={() => handleRowHover(e)}
                    className={`border-t border-[var(--border)] cursor-pointer hover:bg-[var(--background)] ${
                      unread ? 'attention-unread-row' : selected === e.id ? 'bg-[var(--primary-light)]' : ''
                    }`}
                  >
                    <td className="p-4 text-[var(--muted)] font-medium tabular-nums">{serial}</td>
                    <td className="p-4">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">{e.customerName}</span>
                        {unread && <AttentionBadge />}
                      </div>
                      <div className="text-[var(--muted)] text-xs">{e.phoneNumber}</div>
                      {unread && (
                        <div className="text-xs text-[var(--primary)] mt-1">
                          Callback: {formatDateTime(e.preferredCallbackAt)}
                        </div>
                      )}
                    </td>
                    <td className="p-4">{e.eventType}</td>
                    <td className="p-4" onClick={(ev) => ev.stopPropagation()}>
                      <select
                        value={e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status}
                        onChange={(ev) => changeStatus(e.id, ev.target.value)}
                        className="form-select text-xs px-2 py-1 rounded-lg"
                      >
                        {statusOptionsForDropdown(e.status === 'CLOSED' ? 'NOT_CONVERTED' : e.status).map((s) => (
                          <option key={s.id} value={s.id}>{s.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <Card className="p-6 h-fit sticky top-4">
            {detail ? (
              <>
                <div className="flex items-center gap-2 flex-wrap mb-4">
                  <span className="text-sm font-semibold text-[var(--muted)] tabular-nums">
                    #{serialNumbers.get(detail.id)}
                  </span>
                  <h3 className="font-semibold text-lg">{detail.customerName}</h3>
                  {isUnviewedEnquiry(detail) && <AttentionBadge />}
                </div>
                <dl className="space-y-2 text-sm">
                  <div><dt className="text-[var(--muted)]">Phone</dt><dd>{detail.phoneNumber}</dd></div>
                  <Link
                    to={`/bot-tester?phone=${encodeURIComponent(detail.phoneNumber)}`}
                    className="inline-flex items-center gap-1.5 text-sm text-[var(--primary)] hover:underline mt-2"
                  >
                    <MessageCircle size={14} />
                    Open WhatsApp chat
                  </Link>
                  <div><dt className="text-[var(--muted)]">Event</dt><dd>{detail.eventType}</dd></div>
                  <div><dt className="text-[var(--muted)]">Date</dt><dd>{formatDate(detail.eventDate)}</dd></div>
                  <div><dt className="text-[var(--muted)]">Location</dt><dd>{detail.eventLocation}</dd></div>
                  <div><dt className="text-[var(--muted)]">Callback</dt><dd>{callbackDisplay(detail)}</dd></div>
                  <p className="text-xs text-[var(--muted)] pt-1">Pax is set per meal session on the order menu.</p>
                </dl>
                {cuisinePreferences.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="font-medium mb-2">Cuisine preferences</p>
                    <ul className="text-sm space-y-1">
                      {cuisinePreferences.map((d, i) => (
                        <li key={i}>• {d.dishName} {d.customizations && <span className="text-[var(--muted)]">({d.customizations})</span>}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            ) : (
              <p className="text-[var(--muted)] text-sm">Click a row to view details</p>
            )}
          </Card>
        </div>
      )}
    </>
  );
}
