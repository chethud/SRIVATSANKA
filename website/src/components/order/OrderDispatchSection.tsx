import { useMemo, useState } from 'react';
import { Truck, User, X } from 'lucide-react';
import type { Worker } from '../../api/client';
import { updateEnquiry } from '../../api/client';
import { type OrderExtras, resolveAssignedWorkerIds, serializeOrderNotes } from '../../utils/orderNotes';

export function OrderDispatchSection({
  orderId,
  workers,
  extras,
  onRefresh,
}: {
  orderId: string;
  workers: Worker[];
  extras: OrderExtras;
  onRefresh: () => void;
}) {
  const [saving, setSaving] = useState(false);

  const sortedWorkers = useMemo(
    () => [...workers].sort((a, b) => a.name.localeCompare(b.name)),
    [workers],
  );

  const assignedIds = resolveAssignedWorkerIds(extras);
  const assignedWorkers = assignedIds
    .map((id) => workers.find((w) => w.id === id))
    .filter(Boolean) as Worker[];
  const availableWorkers = sortedWorkers.filter((w) => !assignedIds.includes(w.id));

  async function saveAssignedWorkerIds(ids: string[]) {
    setSaving(true);
    try {
      const merged = { ...extras, assignedWorkerIds: ids, primaryWorkerId: ids[0] ?? null };
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  function addWorker(workerId: string) {
    if (!workerId || assignedIds.includes(workerId)) return;
    saveAssignedWorkerIds([...assignedIds, workerId]);
  }

  function removeWorker(workerId: string) {
    saveAssignedWorkerIds(assignedIds.filter((id) => id !== workerId));
  }

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mb-6">
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <Truck size={22} className="text-[var(--order-accent)]" />
        <h2 className="order-view-title text-xl font-semibold text-[var(--foreground)]">Dispatch management</h2>
      </div>
      <p className="text-sm text-[var(--muted)] mb-6">
        Assign one or more workers to this order. You can add as many as you need.
      </p>

      <label className="text-xs font-semibold text-[var(--order-accent)] uppercase tracking-wide flex items-center gap-1 mb-3">
        <User size={14} /> Assigned workers
      </label>

      {assignedWorkers.length === 0 ? (
        <p className="text-sm text-[var(--muted)] mb-4">No workers assigned yet.</p>
      ) : (
        <ul className="space-y-2 mb-4">
          {assignedWorkers.map((worker) => (
            <li
              key={worker.id}
              className="flex flex-wrap items-center gap-3 rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3"
            >
              <div className="flex-1 min-w-[160px]">
                <p className="text-sm font-semibold text-[var(--foreground)]">{worker.name}</p>
                <p className="text-xs text-[var(--muted)]">
                  {worker.role}
                  {worker.phoneNumber ? ` · ${worker.phoneNumber}` : ''}
                </p>
              </div>
              <button
                type="button"
                disabled={saving}
                onClick={() => removeWorker(worker.id)}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg border border-[var(--border)] text-[var(--muted)] hover:text-red-600 hover:border-red-300"
              >
                <X size={14} /> Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {availableWorkers.length > 0 ? (
        <div>
          <label className="text-xs font-medium text-[var(--muted)] mb-1 block">Add worker</label>
          <select
            value=""
            disabled={saving}
            onChange={(e) => addWorker(e.target.value)}
            className="form-select w-full max-w-md px-3 py-2.5 rounded-lg text-sm"
          >
            <option value="">Choose a worker…</option>
            {availableWorkers.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} — {w.role}
              </option>
            ))}
          </select>
        </div>
      ) : (
        sortedWorkers.length === 0 && (
          <p className="text-sm text-[var(--muted)]">Add workers under Workers in the sidebar first.</p>
        )
      )}
    </div>
  );
}
