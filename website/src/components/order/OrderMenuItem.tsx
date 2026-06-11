import { useState } from 'react';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import { updateOrderDish, deleteOrderDish, type EnquiryDish } from '../../api/client';
import { MEAL_SESSIONS } from '../../utils/mealSessions';

export function OrderMenuItem({
  orderId,
  dish,
  onUpdated,
}: {
  orderId: string;
  dish: EnquiryDish;
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [session, setSession] = useState(dish.category);
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setSession(dish.category);
    setEditing(true);
  }

  async function save() {
    setSaving(true);
    try {
      await updateOrderDish(orderId, dish.id, { category: session });
      setEditing(false);
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!confirm(`Remove ${dish.dishName} from this order?`)) return;
    setSaving(true);
    try {
      await deleteOrderDish(orderId, dish.id);
      onUpdated();
    } catch {
      alert('Could not remove this item. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <li className="py-2 border-b border-[var(--border)] last:border-0">
        <p className="text-sm font-medium text-[var(--foreground)] mb-2">{dish.dishName}</p>
        <div className="flex flex-wrap gap-2 items-end">
          <div className="min-w-[140px]">
            <label className="text-[10px] uppercase text-[var(--muted)]">Meal session</label>
            <select
              value={session}
              onChange={(e) => setSession(e.target.value)}
              className="form-select w-full mt-0.5 px-2 py-1 rounded text-sm"
            >
              {MEAL_SESSIONS.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={save}
            disabled={saving}
            className="p-2 rounded-lg bg-[var(--primary)] text-white"
            title="Save"
          >
            <Check size={16} />
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="p-2 rounded-lg border border-[var(--border)]"
            title="Cancel"
          >
            <X size={16} />
          </button>
        </div>
      </li>
    );
  }

  return (
    <li className="order-menu-item">
      <span className="order-menu-item-name">{dish.dishName}</span>
      <div className="order-menu-item-actions">
        <button
          type="button"
          onClick={startEdit}
          disabled={saving}
          className="p-1.5 rounded-lg border border-[var(--border)] hover:bg-[var(--card)] text-[var(--muted)] hover:text-[var(--primary)]"
          title="Edit meal session"
          aria-label={`Edit ${dish.dishName}`}
        >
          <Pencil size={15} />
        </button>
        <button
          type="button"
          onClick={remove}
          disabled={saving}
          className="p-1.5 rounded-lg border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 dark:border-red-900/40 dark:bg-red-950/40 dark:text-red-400"
          title="Remove from menu"
          aria-label={`Remove ${dish.dishName}`}
        >
          <Trash2 size={15} />
        </button>
      </div>
    </li>
  );
}
