import { useState } from 'react';
import { PageHeader, Card, Button } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { createWorker, deleteWorker } from '../api/client';

export default function WorkersPage() {
  const { workers, refresh } = useAppData();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', phoneNumber: '', role: '', dailyWage: 0 });

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    await createWorker(form);
    setForm({ name: '', phoneNumber: '', role: '', dailyWage: 0 });
    setShowForm(false);
    refresh();
  }

  return (
    <>
      <PageHeader title="Workers" description={`${workers.length} workers — live database`} />
      <Button onClick={() => setShowForm(!showForm)} className="mb-6">{showForm ? 'Cancel' : '+ Add Worker'}</Button>
      {showForm && (
        <Card className="p-6 mb-6">
          <form onSubmit={handleAdd} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <input required placeholder="Phone" value={form.phoneNumber} onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <input required placeholder="Role" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })} className="px-3 py-2 border rounded-lg" />
            <input required type="number" placeholder="Daily wage" value={form.dailyWage || ''} onChange={(e) => setForm({ ...form, dailyWage: Number(e.target.value) })} className="px-3 py-2 border rounded-lg" />
            <Button type="submit">Save Worker</Button>
          </form>
        </Card>
      )}
      <div className="bg-[var(--card)] border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[var(--background)]">
            <tr><th className="p-4 text-left">Name</th><th className="p-4 text-left">Role</th><th className="p-4 text-left">Phone</th><th className="p-4 text-left">Daily Wage</th><th className="p-4"></th></tr>
          </thead>
          <tbody>
            {workers.map((w) => (
              <tr key={w.id} className="border-t">
                <td className="p-4 font-medium">{w.name}</td>
                <td className="p-4">{w.role}</td>
                <td className="p-4">{w.phoneNumber}</td>
                <td className="p-4">₹{w.dailyWage}</td>
                <td className="p-4"><button type="button" onClick={() => deleteWorker(w.id).then(refresh)} className="text-red-600 text-xs">Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
