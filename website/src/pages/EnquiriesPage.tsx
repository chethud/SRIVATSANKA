import { useMemo, useState } from 'react';
import { PageHeader, EmptyState, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, SearchInput, FilterChips, LoadingScreen } from '../components/ui';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { createEnquiry, updateEnquiryStatus, formatDate, formatDateTime } from '../api/client';

const STATUS_FILTERS = [
  { id: 'ALL', label: 'All' },
  { id: 'NEW', label: 'New' },
  { id: 'CONTACTED', label: 'Contacted' },
  { id: 'CONVERTED', label: 'Converted' },
  { id: 'CLOSED', label: 'Closed' },
];

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

const emptyForm = () => ({
  customerName: '',
  phoneNumber: '',
  eventType: EVENT_TYPES[0],
  eventDate: defaultEventDate(),
  eventLocation: '',
  guestCount: 50,
  preferredCallbackAt: defaultCallbackAt(),
});

export default function EnquiriesPage() {
  const { loading, error, enquiries, refresh } = useAppData();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selected, setSelected] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  useCreateActionListener('enquiry', () => setShowForm(true));

  const filtered = useMemo(() => {
    return enquiries.filter((e) => {
      const matchStatus = statusFilter === 'ALL' || e.status === statusFilter;
      const q = search.toLowerCase();
      const matchSearch =
        !q ||
        e.customerName.toLowerCase().includes(q) ||
        e.eventType.toLowerCase().includes(q) ||
        e.phoneNumber.includes(q) ||
        e.eventLocation.toLowerCase().includes(q);
      return matchStatus && matchSearch;
    });
  }, [enquiries, search, statusFilter]);

  const detail = enquiries.find((e) => e.id === selected);

  async function changeStatus(id: string, status: string) {
    await updateEnquiryStatus(id, status);
    refresh();
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      const created = await createEnquiry({
        customerName: form.customerName,
        phoneNumber: form.phoneNumber,
        eventType: form.eventType,
        eventDate: new Date(`${form.eventDate}T12:00:00`).toISOString(),
        eventLocation: form.eventLocation,
        guestCount: form.guestCount,
        preferredCallbackAt: new Date(form.preferredCallbackAt).toISOString(),
        notes: 'Created manually by owner',
      });
      setForm(emptyForm());
      setShowForm(false);
      setSelected(created.id);
      await refresh();
    } catch {
      setFormError('Could not save enquiry. Check API connection.');
    } finally {
      setSaving(false);
    }
  }

  if (loading && enquiries.length === 0) return <LoadingScreen />;

  return (
    <>
      <PageHeader
        title="Enquiries"
        description={`${filtered.length} enquiries — add manually or from WhatsApp; mark CONVERTED when confirmed`}
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
            <input
              required
              type="number"
              min={1}
              placeholder="Guest count"
              value={form.guestCount}
              onChange={(e) => setForm({ ...form, guestCount: Number(e.target.value) })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <div>
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
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <SearchInput value={search} onChange={setSearch} placeholder="Search name, event, phone..." />
        <FilterChips options={STATUS_FILTERS} selected={statusFilter} onSelect={setStatusFilter} />
      </div>

      {filtered.length === 0 ? (
        <EmptyState message="No enquiries match your filters." />
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-[var(--background)]">
                <tr>
                  <th className="text-left p-4">Customer</th>
                  <th className="text-left p-4">Event</th>
                  <th className="text-left p-4">Guests</th>
                  <th className="text-left p-4">Dishes</th>
                  <th className="text-left p-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => (
                  <tr
                    key={e.id}
                    onClick={() => setSelected(e.id)}
                    className={`border-t border-[var(--border)] cursor-pointer hover:bg-[var(--background)] ${
                      selected === e.id ? 'bg-[var(--primary-light)]' : ''
                    }`}
                  >
                    <td className="p-4">
                      <div className="font-medium">{e.customerName}</div>
                      <div className="text-[var(--muted)] text-xs">{e.phoneNumber}</div>
                    </td>
                    <td className="p-4">{e.eventType}</td>
                    <td className="p-4">{e.guestCount}</td>
                    <td className="p-4">{e.dishes?.length || 0}</td>
                    <td className="p-4" onClick={(ev) => ev.stopPropagation()}>
                      <select
                        value={e.status}
                        onChange={(ev) => changeStatus(e.id, ev.target.value)}
                        className="form-select text-xs px-2 py-1 rounded-lg"
                      >
                        {STATUS_FILTERS.filter((s) => s.id !== 'ALL').map((s) => (
                          <option key={s.id} value={s.id}>{s.label}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Card className="p-6 h-fit sticky top-4">
            {detail ? (
              <>
                <h3 className="font-semibold text-lg mb-4">{detail.customerName}</h3>
                <dl className="space-y-2 text-sm">
                  <div><dt className="text-[var(--muted)]">Phone</dt><dd>{detail.phoneNumber}</dd></div>
                  <div><dt className="text-[var(--muted)]">Event</dt><dd>{detail.eventType}</dd></div>
                  <div><dt className="text-[var(--muted)]">Date</dt><dd>{formatDate(detail.eventDate)}</dd></div>
                  <div><dt className="text-[var(--muted)]">Location</dt><dd>{detail.eventLocation}</dd></div>
                  <div><dt className="text-[var(--muted)]">Guests</dt><dd>{detail.guestCount}</dd></div>
                  <div><dt className="text-[var(--muted)]">Callback</dt><dd>{formatDateTime(detail.preferredCallbackAt)}</dd></div>
                </dl>
                {detail.dishes?.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="font-medium mb-2">Menu</p>
                    <ul className="text-sm space-y-1">
                      {detail.dishes.map((d, i) => (
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
