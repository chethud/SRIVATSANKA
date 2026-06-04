import { useState } from 'react';
import { Pencil, Trash2, Check, X } from 'lucide-react';
import { Button } from './Layout';
import { updateOrderDish, deleteOrderDish, formatCurrency, type EnquiryDish } from '../api/client';

const CUSTOMIZATION_OPTIONS = [
  'No Milk', 'No Onion', 'No Garlic', 'Less Spice', 'Less Sweet', 'Extra Vegetables',
];

export function OrderDishRow({
  orderId,
  dish,
  onUpdated,
}: {
  orderId: string;
  dish: EnquiryDish;
  onUpdated: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [qty, setQty] = useState(dish.quantity);
  const [price, setPrice] = useState(dish.unitPrice ?? 0);
  const [custom, setCustom] = useState(dish.customizations ?? '');
  const [served, setServed] = useState(dish.served);
  const [saving, setSaving] = useState(false);

  async function saveEdit() {
    setSaving(true);
    try {
      await updateOrderDish(orderId, dish.id, {
        quantity: Math.max(1, qty),
        unitPrice: price,
        customizations: custom || undefined,
        served,
      });
      setEditing(false);
      onUpdated();
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!confirm(`Remove ${dish.dishName}?`)) return;
    await deleteOrderDish(orderId, dish.id);
    onUpdated();
  }

  if (editing) {
    return (
      <li className="p-4 border border-[var(--primary)] rounded-xl bg-[var(--primary-light)]/30 space-y-3">
        <p className="font-medium text-sm">Edit — {dish.dishName}</p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
          <div>
            <label className="text-xs text-[var(--muted)]">Quantity</label>
            <input type="number" min={1} value={qty} onChange={(e) => setQty(Number(e.target.value))} className="w-full mt-1 px-2 py-1.5 border rounded-lg" />
          </div>
          <div>
            <label className="text-xs text-[var(--muted)]">Unit price (₹)</label>
            <input type="number" min={0} value={price} onChange={(e) => setPrice(Number(e.target.value))} className="w-full mt-1 px-2 py-1.5 border rounded-lg" />
          </div>
          <div className="col-span-2">
            <label className="text-xs text-[var(--muted)]">Customization</label>
            <select value={custom} onChange={(e) => setCustom(e.target.value)} className="w-full mt-1 px-2 py-1.5 border rounded-lg">
              <option value="">None</option>
              {CUSTOMIZATION_OPTIONS.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={served} onChange={(e) => setServed(e.target.checked)} />
          Mark as served
        </label>
        <div className="flex gap-2">
          <Button type="button" onClick={saveEdit} disabled={saving} className="!py-1.5 !px-3 text-xs">
            <Check size={14} className="inline mr-1" /> Save
          </Button>
          <button type="button" onClick={() => setEditing(false)} className="px-3 py-1.5 text-xs border rounded-lg hover:bg-white">
            <X size={14} className="inline mr-1" /> Cancel
          </button>
        </div>
      </li>
    );
  }

  const lineTotal = (dish.unitPrice ?? 0) * (dish.quantity || 1);

  return (
    <li className="flex flex-wrap items-center gap-3 py-3 px-4 bg-[var(--card)] border border-[var(--border)] rounded-xl hover:border-[var(--primary)]/40 transition-colors">
      <span className="font-semibold text-[var(--primary-dark)] min-w-[2rem]">{dish.quantity}×</span>
      <span className="font-medium flex-1 min-w-[120px]">{dish.dishName}</span>
      {dish.customizations && (
        <span className="text-xs text-[var(--muted)] bg-[var(--background)] px-2 py-0.5 rounded-full max-w-[200px] truncate">
          {dish.customizations}
        </span>
      )}
      <span className="text-sm font-medium">{formatCurrency(lineTotal)}/unit</span>
      {dish.served && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--success-bg)] text-[var(--success-text)]">Served</span>
      )}
      <div className="flex gap-1 ml-auto">
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="p-2 rounded-lg hover:bg-[var(--background)] text-[var(--muted)] hover:text-[var(--primary)]"
          title="Edit"
        >
          <Pencil size={16} />
        </button>
        <button
          type="button"
          onClick={remove}
          className="p-2 rounded-lg hover:bg-red-50 text-[var(--muted)] hover:text-red-600"
          title="Remove"
        >
          <Trash2 size={16} />
        </button>
      </div>
    </li>
  );
}
