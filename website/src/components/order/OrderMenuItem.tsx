import { useState } from 'react';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import { updateOrderDish, deleteOrderDish, type EnquiryDish } from '../../api/client';
import { CustomizationInput } from './CustomizationInput';
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
  const [custom, setCustom] = useState(dish.customizations ?? '');
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setSession(dish.category);
    setCustom(dish.customizations ?? '');
    setEditing(true);
  }

  async function save() {
    setSaving(true);
    try {
      await updateOrderDish(orderId, dish.id, {
        category: session,
        customizations: custom || undefined,
      });
      setEditing(false);
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!confirm(`Remove ${dish.dishName} from this order?`)) return;
    await deleteOrderDish(orderId, dish.id);
    onUpdated();
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
          <div className="flex-1 min-w-[140px]">
            <label className="text-[10px] uppercase text-[var(--muted)]">Customization</label>
            <CustomizationInput
              id={`edit-custom-${dish.id}`}
              value={custom}
              onChange={setCustom}
              className="form-input w-full mt-0.5 px-2 py-1 rounded text-sm"
            />
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
    <li className="flex items-center gap-2 py-1.5 text-sm group">
      <span className="flex-1 text-[var(--foreground)] min-w-0">
        {dish.dishName}
        {dish.customizations && (
          <span className="block text-xs text-[var(--muted)] truncate">{dish.customizations}</span>
        )}
      </span>
      <div className="flex gap-0.5 opacity-70 group-hover:opacity-100 shrink-0">
        <button
          type="button"
          onClick={startEdit}
          className="p-1.5 rounded-md hover:bg-[var(--sidebar-hover)] text-[var(--muted)] hover:text-[var(--primary)]"
          title="Edit item"
        >
          <Pencil size={14} />
        </button>
        <button
          type="button"
          onClick={remove}
          className="p-1.5 rounded-md hover:bg-red-500/10 text-[var(--muted)] hover:text-red-600"
          title="Remove item"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </li>
  );
}
