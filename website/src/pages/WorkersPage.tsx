import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { PageHeader, Card, Button, EmptyState } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { usePageSearch } from '../context/PageSearchContext';
import { createWorker } from '../api/client';

export default function WorkersPage() {
  const navigate = useNavigate();
  const { workers, refresh } = useAppData();
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState({ name: '', phoneNumber: '', role: '' });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return workers;
    return workers.filter(
      (w) =>
        w.name.toLowerCase().includes(q) ||
        w.role.toLowerCase().includes(q) ||
        w.phoneNumber.toLowerCase().includes(q),
    );
  }, [workers, search]);

  useCreateActionListener('worker', () => setShowForm(true));
  usePageSearch('Search by name, role, or phone...', search, setSearch);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const created = await createWorker({
      name: form.name,
      phoneNumber: form.phoneNumber,
      role: form.role,
      dailyWage: 0,
      isLead: false,
    });
    setForm({ name: '', phoneNumber: '', role: '' });
    setShowForm(false);
    refresh();
    navigate(`/workers/${created.id}`);
  }

  return (
    <>
      <PageHeader
        title="Workers"
        description={`${workers.length} workers — click a name to open profile and assign duties`}
      />

      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required placeholder="Phone" value={form.phoneNumber} onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required placeholder="Role (e.g. Chef, Server)" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="form-input px-3 py-2 rounded-lg md:col-span-2" />
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit">Save Worker</Button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]">Cancel</button>
            </div>
          </form>
        </Card>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          message={workers.length === 0 ? 'No workers yet. Use New worker in the header.' : 'No workers match your search.'}
        />
      ) : (
      <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-[var(--background)]">
            <tr>
              <th className="p-4 text-left">Name</th>
              <th className="p-4 text-left">Role</th>
              <th className="p-4 text-left">Phone</th>
              <th className="p-4 w-10" />
            </tr>
          </thead>
          <tbody>
            {filtered.map((w) => (
              <tr
                key={w.id}
                onClick={() => navigate(`/workers/${w.id}`)}
                className="border-t border-[var(--border)] cursor-pointer hover:bg-[var(--background)] transition-colors"
              >
                <td className="p-4 font-medium">{w.name}</td>
                <td className="p-4">{w.role}</td>
                <td className="p-4">{w.phoneNumber}</td>
                <td className="p-4">
                  <ChevronRight size={18} className="text-[var(--muted)]" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
    </>
  );
}
