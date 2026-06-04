import { useState } from 'react';
import { PageHeader, Card, Button } from '../components/Layout';
import { WorkerProfilePanel } from '../components/workers/WorkerProfilePanel';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { createWorker, deleteWorker, updateWorker, type Worker } from '../api/client';

export default function WorkersPage() {
  const { workers, enquiries, refresh } = useAppData();
  const [showForm, setShowForm] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState({ name: '', phoneNumber: '', role: '', dailyWage: 0, isLead: false });

  useCreateActionListener('worker', () => setShowForm(true));

  const selected = workers.find((w) => w.id === selectedId) ?? null;

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    const created = await createWorker(form);
    setForm({ name: '', phoneNumber: '', role: '', dailyWage: 0, isLead: false });
    setShowForm(false);
    setSelectedId(created.id);
    refresh();
  }

  async function toggleLead(e: React.MouseEvent, id: string, current: boolean) {
    e.stopPropagation();
    await updateWorker(id, { isLead: !current });
    refresh();
  }

  function openProfile(w: Worker) {
    setSelectedId(w.id);
    setShowForm(false);
  }

  return (
    <>
      <PageHeader
        title="Workers"
        description={`${workers.length} workers — click a name for profile & duty history; use header New worker to add`}
      />
      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required placeholder="Phone" value={form.phoneNumber} onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required placeholder="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required type="number" placeholder="Daily wage" value={form.dailyWage || ''} onChange={(e) => setForm({ ...form, dailyWage: Number(e.target.value) })} className="form-input px-3 py-2 rounded-lg" />
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input type="checkbox" checked={form.isLead} onChange={(e) => setForm({ ...form, isLead: e.target.checked })} />
              Lead worker (प्रधान) — primary contact for dispatch
            </label>
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit">Save Worker</Button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]">Cancel</button>
            </div>
          </form>
        </Card>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-[var(--background)]">
              <tr>
                <th className="p-4 text-left">Name</th>
                <th className="p-4 text-left">Role</th>
                <th className="p-4 text-left">Phone</th>
                <th className="p-4 text-left">Daily Wage</th>
                <th className="p-4 text-left">Lead</th>
                <th className="p-4" />
              </tr>
            </thead>
            <tbody>
              {workers.map((w) => (
                <tr
                  key={w.id}
                  onClick={() => openProfile(w)}
                  className={`border-t border-[var(--border)] cursor-pointer transition-colors hover:bg-[var(--background)] ${
                    selectedId === w.id ? 'bg-[var(--primary-light)]' : ''
                  }`}
                >
                  <td className="p-4 font-medium">
                    {w.name}
                    {(w.isLead ?? false) && <span className="ml-2 text-xs text-[var(--primary)]">★ Lead</span>}
                  </td>
                  <td className="p-4">{w.role}</td>
                  <td className="p-4">{w.phoneNumber}</td>
                  <td className="p-4">₹{w.dailyWage}</td>
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      onClick={(e) => toggleLead(e, w.id, w.isLead ?? false)}
                      className={`text-xs px-2 py-1 rounded-full border ${
                        (w.isLead ?? false)
                          ? 'bg-[var(--primary-light)] text-[var(--primary)] border-[var(--primary)]'
                          : 'border-[var(--border)] hover:border-[var(--primary)]'
                      }`}
                    >
                      {(w.isLead ?? false) ? 'Lead' : 'Set lead'}
                    </button>
                  </td>
                  <td className="p-4" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      onClick={() => deleteWorker(w.id).then(() => { if (selectedId === w.id) setSelectedId(null); refresh(); })}
                      className="text-red-600 text-xs hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {workers.length === 0 && (
            <p className="text-center text-[var(--muted)] py-12 text-sm">No workers yet. Use New worker in the header.</p>
          )}
        </div>

        {selected ? (
          <WorkerProfilePanel
            worker={selected}
            orders={enquiries}
            onClose={() => setSelectedId(null)}
            onUpdated={refresh}
          />
        ) : (
          <Card className="p-8 text-center text-sm text-[var(--muted)] h-fit sticky top-4">
            Click a worker to view profile, assign duties to orders & dates, and full work history.
          </Card>
        )}
      </div>
    </>
  );
}
