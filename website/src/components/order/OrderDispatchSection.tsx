import { useMemo, useState } from 'react';
import { Truck, User, X } from 'lucide-react';
import type { Enquiry, Worker } from '../../api/client';
import { updateEnquiry } from '../../api/client';
import { WorkerSearchSelect } from '../WorkerSearchSelect';
import { type OrderExtras, resolveAssignedWorkerIds, serializeOrderNotes } from '../../utils/orderNotes';

export function OrderDispatchSection({
  orderId,
  workers,
  extras,
  onOrderUpdated,
}: {
  orderId: string;
  workers: Worker[];
  extras: OrderExtras;
  onOrderUpdated: (order: Enquiry) => void;
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
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
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
    <div className="order-section">
      <div className="order-section-head">
        <div className="order-section-title">
          <span className="order-section-icon">
            <Truck size={18} />
          </span>
          Dispatch management
        </div>
      </div>
      <p className="order-section-sub">
        Assign one or more workers to this order. You can add as many as you need.
      </p>

      <label className="text-xs font-semibold text-[var(--order-accent)] uppercase tracking-wide flex items-center gap-1 mb-3">
        <User size={14} /> Assigned workers
      </label>

      {assignedWorkers.length === 0 ? (
        <p className="text-sm text-[var(--muted)] mb-4 py-4 text-center rounded-lg border border-dashed border-[var(--border)] bg-[var(--background-alt)]">
          No workers assigned yet.
        </p>
      ) : (
        <ul className="space-y-2 mb-4">
          {assignedWorkers.map((worker) => (
            <li key={worker.id} className="order-worker-card">
              <div className="order-worker-avatar" aria-hidden>
                {worker.name.charAt(0).toUpperCase()}
              </div>
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
                className="order-btn-ghost text-red-600 hover:text-red-700 hover:border-red-200"
              >
                <X size={14} /> Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {availableWorkers.length > 0 ? (
        <WorkerSearchSelect
          workers={availableWorkers}
          disabled={saving}
          onSelect={(worker) => addWorker(worker.id)}
        />
      ) : sortedWorkers.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">Add workers under Workers in the sidebar first.</p>
      ) : (
        <p className="text-sm text-[var(--muted)]">All workers are already assigned to this order.</p>
      )}
    </div>
  );
}
