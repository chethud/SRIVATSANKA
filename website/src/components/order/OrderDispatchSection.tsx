import { useMemo, useState } from 'react';
import { Truck, User } from 'lucide-react';
import type { EnquiryDish, Worker } from '../../api/client';
import { updateEnquiry, updateOrderDish } from '../../api/client';
import {
  type DispatchItemStatus,
  type DispatchPhase,
  type OrderExtras,
  serializeOrderNotes,
} from '../../utils/orderNotes';

const PHASES: { id: DispatchPhase; label: string }[] = [
  { id: 'planned', label: 'Planned' },
  { id: 'preparing', label: 'Preparing' },
  { id: 'out_for_delivery', label: 'Out for delivery' },
  { id: 'completed', label: 'Completed' },
];

const ITEM_STEPS: DispatchItemStatus[] = ['pending', 'packed', 'dispatched', 'served'];

const STEP_LABEL: Record<DispatchItemStatus, string> = {
  pending: 'Pending',
  packed: 'Packed',
  dispatched: 'Dispatched',
  served: 'Served',
};

function nextStatus(current: DispatchItemStatus): DispatchItemStatus {
  const i = ITEM_STEPS.indexOf(current);
  return ITEM_STEPS[Math.min(i + 1, ITEM_STEPS.length - 1)];
}

function resolveItemStatus(
  dish: EnquiryDish,
  itemDispatch: Record<string, DispatchItemStatus>,
): DispatchItemStatus {
  if (dish.served) return 'served';
  return itemDispatch[dish.id] ?? 'pending';
}

export function OrderDispatchSection({
  orderId,
  menuItems,
  byCategory,
  colLeft,
  colRight,
  workers,
  extras,
  onRefresh,
}: {
  orderId: string;
  menuItems: EnquiryDish[];
  byCategory: Record<string, EnquiryDish[]>;
  colLeft: string[];
  colRight: string[];
  workers: Worker[];
  extras: OrderExtras;
  onRefresh: () => void;
}) {
  const [saving, setSaving] = useState(false);

  const sortedWorkers = useMemo(() => {
    return [...workers].sort((a, b) => {
      if (a.isLead && !b.isLead) return -1;
      if (!a.isLead && b.isLead) return 1;
      return a.name.localeCompare(b.name);
    });
  }, [workers]);

  const primaryWorker = workers.find((w) => w.id === extras.primaryWorkerId);

  const dispatchedCount = menuItems.filter(
    (d) => resolveItemStatus(d, extras.itemDispatch ?? {}) === 'dispatched',
  ).length;
  const servedCount = menuItems.filter(
    (d) => resolveItemStatus(d, extras.itemDispatch ?? {}) === 'served',
  ).length;

  async function saveExtras(patch: Partial<OrderExtras>) {
    setSaving(true);
    try {
      const merged = { ...extras, ...patch };
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  async function setItemStatus(dish: EnquiryDish, status: DispatchItemStatus) {
    const itemDispatch = { ...(extras.itemDispatch ?? {}), [dish.id]: status };
    if (status === 'served') {
      await updateOrderDish(orderId, dish.id, { served: true });
    } else if (dish.served) {
      await updateOrderDish(orderId, dish.id, { served: false });
    }
    await saveExtras({ itemDispatch });
  }

  function renderDispatchColumn(cats: string[]) {
    return (
      <div className="space-y-6">
        {cats.map((cat) => (
          <div key={cat}>
            <h4 className="text-sm font-semibold text-[var(--order-accent)] mb-2 tracking-wide">{cat}</h4>
            <ul className="space-y-2">
              {(byCategory[cat] ?? []).map((d) => {
                const status = resolveItemStatus(d, extras.itemDispatch ?? {});
                return (
                  <li key={d.id} className="flex flex-wrap items-center gap-2 text-sm py-1">
                    <span className="flex-1 min-w-[120px] text-[var(--foreground)]">{d.dishName}</span>
                    <span className="text-[var(--muted)] tabular-nums shrink-0">{d.quantity} pcs</span>
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => setItemStatus(d, nextStatus(status))}
                      title="Tap to advance dispatch status"
                      className={`shrink-0 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide border transition-colors ${
                        status === 'served'
                          ? 'bg-[var(--success-bg)] text-[var(--success-text)] border-transparent'
                          : status === 'dispatched'
                            ? 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30'
                            : status === 'packed'
                              ? 'bg-amber-500/15 text-amber-800 dark:text-amber-200 border-amber-500/30'
                              : 'bg-[var(--background)] text-[var(--muted)] border-[var(--border)]'
                      }`}
                    >
                      {STEP_LABEL[status]}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mb-6">
      <div className="flex flex-wrap items-center gap-2 mb-6">
        <Truck size={22} className="text-[var(--order-accent)]" />
        <h2 className="order-view-title text-xl font-semibold text-[var(--foreground)]">Dispatch management</h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="md:col-span-2">
          <label className="text-xs font-semibold text-[var(--order-accent)] uppercase tracking-wide flex items-center gap-1 mb-2">
            <User size={14} /> Primary worker (प्रधान)
          </label>
          <select
            value={extras.primaryWorkerId ?? ''}
            disabled={saving}
            onChange={(e) => saveExtras({ primaryWorkerId: e.target.value || null })}
            className="form-select w-full px-3 py-2.5 rounded-lg text-sm"
          >
            <option value="">Assign lead worker…</option>
            {sortedWorkers.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} — {w.role}{(w.isLead ?? false) ? ' ★ Lead' : ''}
              </option>
            ))}
          </select>
          {primaryWorker && (
            <p className="text-xs text-[var(--muted)] mt-1">{primaryWorker.phoneNumber}</p>
          )}
        </div>
        <div>
          <label className="text-xs font-semibold text-[var(--order-accent)] uppercase tracking-wide mb-2 block">
            Dispatch phase
          </label>
          <select
            value={extras.dispatchPhase ?? 'planned'}
            disabled={saving}
            onChange={(e) => saveExtras({ dispatchPhase: e.target.value as DispatchPhase })}
            className="form-select w-full px-3 py-2.5 rounded-lg text-sm"
          >
            {PHASES.map((p) => (
              <option key={p.id} value={p.id}>{p.label}</option>
            ))}
          </select>
        </div>
      </div>

      <p className="text-xs text-[var(--muted)] mb-4">
        Tap status on each item to advance: Pending → Packed → Dispatched → Served.
        {' '}
        <span className="tabular-nums">{servedCount}/{menuItems.length} served</span>
        {dispatchedCount > 0 && <span> · {dispatchedCount} out for delivery</span>}
      </p>

      {menuItems.length === 0 ? (
        <p className="text-sm text-[var(--muted)] py-6 text-center">Add menu items above to track dispatch.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
          {renderDispatchColumn(colLeft)}
          {renderDispatchColumn(colRight)}
        </div>
      )}
    </div>
  );
}
