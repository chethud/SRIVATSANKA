import { useMemo, useState } from 'react';
import { PageHeader, EmptyState, Card } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { ErrorBanner, SearchInput, FilterChips, LoadingScreen } from '../components/ui';
import { updateEnquiryStatus, formatDate, formatDateTime } from '../api/client';

const STATUS_FILTERS = [
  { id: 'ALL', label: 'All' },
  { id: 'NEW', label: 'New' },
  { id: 'CONTACTED', label: 'Contacted' },
  { id: 'CONVERTED', label: 'Converted' },
  { id: 'CLOSED', label: 'Closed' },
];

export default function EnquiriesPage() {
  const { loading, error, enquiries, refresh } = useAppData();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [selected, setSelected] = useState<string | null>(null);

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

  if (loading && enquiries.length === 0) return <LoadingScreen />;

  return (
    <>
      <PageHeader
        title="Enquiries"
        description={`${filtered.length} enquiries — mark CONVERTED when client confirms, then manage dishes on Orders`}
      />
      <ErrorBanner message={error} />
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
                        className="text-xs px-2 py-1 rounded-lg border"
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
