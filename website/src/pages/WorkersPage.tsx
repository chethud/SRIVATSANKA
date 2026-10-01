import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Pencil, Trash2 } from 'lucide-react';
import { PageHeader, Card, Button, EmptyState } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { useCreateActionListener } from '../hooks/useCreateActionListener';
import { usePageSearch } from '../context/PageSearchContext';
import { createWorker, deleteWorker, updateWorker, type Worker } from '../api/client';

type WorkerForm = {
  name: string;
  phoneNumber: string;
  role: string;
  isActive: boolean;
};

function emptyForm(): WorkerForm {
  return { name: '', phoneNumber: '', role: '', isActive: true };
}

function workerIsActive(w: Worker): boolean {
  return w.isActive !== false;
}

export default function WorkersPage() {
  const navigate = useNavigate();
  const { workers, refresh } = useAppData();
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [search, setSearch] = useState('');
  const [form, setForm] = useState<WorkerForm>(emptyForm);

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

  function openCreate() {
    setEditingId(null);
    setForm(emptyForm());
    setShowForm(true);
  }

  function openEdit(w: Worker) {
    setEditingId(w.id);
    setForm({
      name: w.name,
      phoneNumber: w.phoneNumber,
      role: w.role,
      isActive: workerIsActive(w),
    });
    setShowForm(true);
    document.getElementById('page-create-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function closeForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(emptyForm());
  }

  useCreateActionListener('worker', openCreate);
  usePageSearch('Search by name, role, or phone...', search, setSearch);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await updateWorker(editingId, {
          name: form.name.trim(),
          phoneNumber: form.phoneNumber.trim(),
          role: form.role.trim(),
          isActive: form.isActive,
        });
        closeForm();
        await refresh();
      } else {
        const created = await createWorker({
          name: form.name.trim(),
          phoneNumber: form.phoneNumber.trim(),
          role: form.role.trim(),
          dailyWage: 0,
          isLead: false,
          isActive: form.isActive,
        });
        closeForm();
        await refresh();
        navigate(`/workers/${created.id}`);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not save worker.');
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(w: Worker) {
    const next = !workerIsActive(w);
    const label = next ? 'Mark this worker as active?' : 'Mark this worker as inactive?';
    if (!window.confirm(label)) return;
    try {
      await updateWorker(w.id, { isActive: next });
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not update status.');
    }
  }

  async function handleDelete(w: Worker) {
    if (!window.confirm(`Delete worker ${w.name}? Assignments will be removed.`)) return;
    try {
      await deleteWorker(w.id);
      if (editingId === w.id) closeForm();
      await refresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not delete worker.');
    }
  }

  const activeCount = workers.filter(workerIsActive).length;

  return (
    <>
      <PageHeader
        title="Workers"
        description={`${activeCount} active · ${workers.length} total — click a name for profile and duties`}
      />

      {showForm && (
        <Card id="page-create-form" className="p-6 mb-6">
          <h2 className="text-sm font-semibold mb-4">{editingId ? 'Edit worker' : 'New worker'}</h2>
          <form onSubmit={(ev) => void handleSave(ev)} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <input
              required
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <input
              placeholder="Phone (optional)"
              value={form.phoneNumber}
              onChange={(e) => setForm({ ...form, phoneNumber: e.target.value })}
              className="form-input px-3 py-2 rounded-lg"
            />
            <input
              required
              placeholder="Role (e.g. Chef, Server)"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="form-input px-3 py-2 rounded-lg md:col-span-2"
            />
            <label className="flex items-center gap-2 text-sm md:col-span-2 cursor-pointer">
              <input
                type="checkbox"
                checked={form.isActive}
                onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
                className="rounded border-[var(--border)]"
              />
              Active (shown for new duty assignments)
            </label>
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit" disabled={saving}>
                {saving ? 'Saving…' : editingId ? 'Update worker' : 'Save worker'}
              </Button>
              <button
                type="button"
                onClick={closeForm}
                className="px-4 py-2.5 text-sm border border-[var(--border)] rounded-xl hover:bg-[var(--sidebar-hover)]"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          message={workers.length === 0 ? 'No workers yet. Use New worker in the header.' : 'No workers match your search.'}
        />
      ) : (
        <div className="bg-[var(--card)] border border-[var(--border)] rounded-xl overflow-hidden shadow-sm overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]">
            <thead className="bg-[var(--background)]">
              <tr>
                <th className="p-4 text-left">Name</th>
                <th className="p-4 text-left">Role</th>
                <th className="p-4 text-left">Phone</th>
                <th className="p-4 text-left">Status</th>
                <th className="p-4 text-left">Actions</th>
                <th className="p-4 w-10" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((w) => {
                const active = workerIsActive(w);
                return (
                  <tr
                    key={w.id}
                    className={`border-t border-[var(--border)] transition-colors ${
                      active ? 'hover:bg-[var(--background)]' : 'opacity-70 bg-[var(--background)]/40'
                    }`}
                  >
                    <td className="p-4 font-medium">
                      <button
                        type="button"
                        onClick={() => navigate(`/workers/${w.id}`)}
                        className="text-left hover:text-[var(--primary)] hover:underline"
                      >
                        {w.name}
                      </button>
                    </td>
                    <td className="p-4">{w.role}</td>
                    <td className="p-4 tabular-nums">{w.phoneNumber}</td>
                    <td className="p-4">
                      <span
                        className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          active
                            ? 'bg-[var(--primary-light)] text-[var(--foreground)]'
                            : 'bg-[var(--border)] text-[var(--muted)]'
                        }`}
                      >
                        {active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(w)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:underline"
                        >
                          <Pencil size={12} /> Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => void toggleActive(w)}
                          className="text-xs font-semibold text-[var(--muted)] hover:text-[var(--foreground)] hover:underline"
                        >
                          {active ? 'Deactivate' : 'Activate'}
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(w)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 hover:underline"
                        >
                          <Trash2 size={12} /> Delete
                        </button>
                      </div>
                    </td>
                    <td className="p-4">
                      <button
                        type="button"
                        onClick={() => navigate(`/workers/${w.id}`)}
                        className="text-[var(--muted)] hover:text-[var(--foreground)]"
                        aria-label={`Open ${w.name} profile`}
                      >
                        <ChevronRight size={18} />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
