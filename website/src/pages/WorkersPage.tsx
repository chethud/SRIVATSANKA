import { useState } from 'react';
import { PageHeader, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { createWorker, deleteWorker, updateWorker } from '../api/client';

export default function WorkersPage() {
  const { workers, refresh } = useAppData();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', phoneNumber: '', role: '', dailyWage: 0, isLead: false });

  useCreateActionListener('worker', () => setShowForm(true));

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    await createWorker(form);
    setForm({ name: '', phoneNumber: '', role: '', dailyWage: 0, isLead: false });
    setShowForm(false);
    refresh();
  }

  async function toggleLead(id: string, current: boolean) {
    await updateWorker(id, { isLead: !current });
    refresh();
  }

  return (
    <>
      <PageHeader title="Workers" description={`${workers.length} workers — use header New worker to add`} />
      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required placeholder="Phone" value={form.phoneNumber} onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required placeholder="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="form-input px-3 py-2 rounded-lg" />
            <input required type="number" placeholder="Daily wage" value={form.dailyWage || ''} onChange={(e) => setForm({ ...form, dailyWage: Number(e.target.value) })} className="form-input px-3 py-2 rounded-lg" />
            <label className="flex items-center gap-2 text-sm md:col-span-2">
              <input
                type="checkbox"
                checked={form.isLead}
                onChange={(e) => setForm({ ...form, isLead: e.target.checked })}
              />
              Lead worker (प्रधान) — primary contact for dispatch
            </label>
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit">Save Worker</Button>
              <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]">Cancel</button>
            </div>
          </form>
        </Card>
      )}
      <div className="bg-[var(--card)] border rounded-xl overflow-hidden">
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
              <tr key={w.id} className="border-t border-[var(--border)]">
                <td className="p-4 font-medium">
                  {w.name}
                  {(w.isLead ?? false) && <span className="ml-2 text-xs text-[var(--primary)]">★ Lead</span>}
                </td>
                <td className="p-4">{w.role}</td>
                <td className="p-4">{w.phoneNumber}</td>
                <td className="p-4">₹{w.dailyWage}</td>
                <td className="p-4">
                  <button
                    type="button"
                    onClick={() => toggleLead(w.id, w.isLead ?? false)}
                    className={`text-xs px-2 py-1 rounded-full border ${
                      (w.isLead ?? false)
                        ? 'bg-[var(--primary-light)] text-[var(--primary)] border-[var(--primary)]'
                        : 'border-[var(--border)] hover:border-[var(--primary)]'
                    }`}
                  >
                    {(w.isLead ?? false) ? 'Lead' : 'Set lead'}
                  </button>
                </td>
                <td className="p-4">
                  <button type="button" onClick={() => deleteWorker(w.id).then(refresh)} className="text-red-600 text-xs hover:underline">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
