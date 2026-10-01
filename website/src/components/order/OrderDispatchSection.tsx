import { useMemo, useState } from 'react';
import { Truck, User, X } from 'lucide-react';
import type { Enquiry, Worker } from '../../api/client';
import { updateEnquiry } from '../../api/client';
import { WorkerSearchSelect } from '../WorkerSearchSelect';
import { workerNeedsHeadcount } from '../../utils/workerStaff';
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
    () =>
      [...workers]
        .filter((w) => w.isActive !== false)
        .sort((a, b) => a.name.localeCompare(b.name)),
    [workers],
  );

  const assignedIds = resolveAssignedWorkerIds(extras);
  const headcounts = extras.staffHeadcounts ?? {};
  const assignedWorkers = assignedIds
    .map((id) => workers.find((w) => w.id === id))
    .filter(Boolean) as Worker[];
  const availableWorkers = sortedWorkers.filter((w) => !assignedIds.includes(w.id));

  async function persist(patch: Partial<OrderExtras>) {
    setSaving(true);
    try {
      const merged = { ...extras, ...patch };
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
    } finally {
      setSaving(false);
    }
  }

  async function saveAssignedWorkerIds(ids: string[]) {
    const nextHeadcounts = { ...headcounts };
    for (const id of Object.keys(nextHeadcounts)) {
      if (!ids.includes(id)) delete nextHeadcounts[id];
    }
    await persist({ assignedWorkerIds: ids, primaryWorkerId: ids[0] ?? null, staffHeadcounts: nextHeadcounts });
  }

  function addWorker(workerId: string) {
    if (!workerId || assignedIds.includes(workerId)) return;
    const worker = workers.find((w) => w.id === workerId);
    const nextHeadcounts = { ...headcounts };
    if (worker && workerNeedsHeadcount(worker.name) && !nextHeadcounts[workerId]) {
      nextHeadcounts[workerId] = 1;
    }
    void persist({
      assignedWorkerIds: [...assignedIds, workerId],
      primaryWorkerId: assignedIds[0] ?? workerId,
      staffHeadcounts: nextHeadcounts,
    });
  }

  function removeWorker(workerId: string) {
    void saveAssignedWorkerIds(assignedIds.filter((id) => id !== workerId));
  }

  function setHeadcount(workerId: string, raw: string) {
    const n = Math.max(0, Math.floor(Number(raw) || 0));
    const next = { ...headcounts };
    if (n <= 0) delete next[workerId];
    else next[workerId] = n;
    void persist({ staffHeadcounts: next });
  }

  return (
    <div className="order-section order-section--dropdown">
      <div className="order-section-head">
        <div className="order-section-title">
          <span className="order-section-icon">
            <Truck size={18} />
          </span>
          Dispatch management
        </div>
      </div>
      <p className="order-section-sub">
        Assign one or more workers to this order. For Extra cleaners / Extra servers, enter how many people you need.
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
                {workerNeedsHeadcount(worker.name) && (
                  <label className="flex items-center gap-2 mt-2 text-xs font-semibold text-[var(--order-accent)]">
                    Count
                    <input
                      type="number"
                      min={1}
                      step={1}
                      disabled={saving}
                      value={headcounts[worker.id] ?? 1}
                      onChange={(e) => setHeadcount(worker.id, e.target.value)}
                      className="form-input w-20 px-2 py-1 rounded-md text-sm tabular-nums"
                    />
                  </label>
                )}
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
