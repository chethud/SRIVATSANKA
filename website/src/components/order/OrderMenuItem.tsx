import { useState } from 'react';
import { Check, Pencil, Trash2, X } from 'lucide-react';
import { updateOrderDish, deleteOrderDish, type Enquiry, type EnquiryDish } from '../../api/client';
import { MEAL_SESSIONS } from '../../utils/mealSessions';

export function OrderMenuItem({
  orderId,
  dish,
  onUpdated,
}: {
  orderId: string;
  dish: EnquiryDish;
  onUpdated: (order: Enquiry) => void;
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
      const updated = await updateOrderDish(orderId, dish.id, { category: session });
      setEditing(false);
      onUpdated(updated);
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!confirm(`Remove ${dish.dishName} from this order?`)) return;
    setSaving(true);
    try {
      const updated = await deleteOrderDish(orderId, dish.id);
      onUpdated(updated);
    } catch {
      alert('Could not remove this item. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <li className="order-menu-item order-menu-item--editing">
        <p className="order-menu-item-name">{dish.dishName}</p>
        <div className="order-menu-item-edit">
          <div className="order-menu-item-edit-field">
            <label className="excel-meta-label">Meal session</label>
            <select
              value={session}
              onChange={(e) => setSession(e.target.value)}
              className="form-select excel-meta-input excel-meta-input--wide"
            >
              {MEAL_SESSIONS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>
          <div className="order-menu-item-actions">
            <button
              type="button"
              onClick={save}
              disabled={saving}
              className="order-menu-action order-menu-action--primary"
              title="Save"
            >
              <Check size={15} />
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="order-menu-action"
              title="Cancel"
            >
              <X size={15} />
            </button>
          </div>
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
          className="order-menu-action"
          title="Edit meal session"
          aria-label={`Edit ${dish.dishName}`}
        >
          <Pencil size={14} />
        </button>
        <button
          type="button"
          onClick={remove}
          disabled={saving}
          className="order-menu-action order-menu-action--danger"
          title="Remove from menu"
          aria-label={`Remove ${dish.dishName}`}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </li>
  );
}
