import { useState } from 'react';
import { Pencil, Trash2, Check, X } from 'lucide-react';
import { Button } from './Layout';
import { updateOrderDish, deleteOrderDish, type EnquiryDish } from '../api/client';
import { CustomizationInput } from './order/CustomizationInput';
import { formatQuantityDisplay, normalizeQuantityUnit } from '../utils/quantityUnits';
import { QuantityUnitFields } from './order/QuantityUnitFields';

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
  const [qtyUnit, setQtyUnit] = useState<string>(normalizeQuantityUnit(dish.quantityUnit));
  const [custom, setCustom] = useState(dish.customizations ?? '');
  const [served, setServed] = useState(dish.served);
  const [saving, setSaving] = useState(false);

  function startEdit() {
    setQty(dish.quantity);
    setQtyUnit(normalizeQuantityUnit(dish.quantityUnit));
    setCustom(dish.customizations ?? '');
    setServed(dish.served);
    setEditing(true);
  }

  async function saveEdit() {
    setSaving(true);
    try {
      await updateOrderDish(orderId, dish.id, {
        quantity: qty,
        quantityUnit: qtyUnit,
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
          <div className="col-span-2 grid grid-cols-2 gap-2">
            <QuantityUnitFields
              idPrefix={`row-${dish.id}`}
              quantity={qty}
              unit={qtyUnit}
              onQuantityChange={setQty}
              onUnitChange={setQtyUnit}
              quantityClassName="w-full mt-1 px-2 py-1.5 border rounded-lg"
              unitClassName="form-select w-full mt-1 px-2 py-1.5 rounded-lg"
            />
          </div>
          <div className="col-span-2 sm:col-span-2">
            <label className="text-xs text-[var(--muted)]">Customization</label>
            <CustomizationInput
              id={`row-custom-${dish.id}`}
              value={custom}
              onChange={setCustom}
              className="form-input w-full mt-1 px-2 py-1.5 rounded-lg"
            />
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
          <button type="button" onClick={() => setEditing(false)} className="px-3 py-1.5 text-xs border border-[var(--border)] rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--foreground)]">
            <X size={14} className="inline mr-1" /> Cancel
          </button>
        </div>
      </li>
    );
  }

  return (
    <li className="flex flex-wrap items-center gap-3 py-3 px-4 bg-[var(--card)] border border-[var(--border)] rounded-xl hover:border-[var(--primary)]/40 transition-colors">
      <span className="font-semibold text-[var(--primary-dark)] min-w-[2rem] tabular-nums">
        {formatQuantityDisplay(dish.quantity, dish.quantityUnit)}
      </span>
      <span className="font-medium flex-1 min-w-[120px]">{dish.dishName}</span>
      {dish.customizations && (
        <span className="text-xs text-[var(--muted)] bg-[var(--background)] px-2 py-0.5 rounded-full max-w-[200px] truncate">
          {dish.customizations}
        </span>
      )}
      {dish.served && (
        <span className="text-xs px-2 py-0.5 rounded-full bg-[var(--success-bg)] text-[var(--success-text)]">Served</span>
      )}
      <div className="flex gap-1 ml-auto">
        <button
          type="button"
          onClick={startEdit}
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
