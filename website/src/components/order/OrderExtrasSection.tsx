import { useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { updateEnquiry } from '../../api/client';
import { serializeOrderNotes, type OrderExtraItem, type OrderExtras } from '../../utils/orderNotes';
import { Button } from '../Layout';

function newExtraItem(): OrderExtraItem {
  return {
    id: `extra_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    title: '',
    description: '',
    quantity: '',
  };
}

function cleanItems(items: OrderExtraItem[]): OrderExtraItem[] {
  return items
    .map((row) => ({
      ...row,
      title: row.title.trim(),
      description: row.description.trim(),
      quantity: row.quantity.trim(),
    }))
    .filter((row) => row.title || row.description || row.quantity);
}

export function OrderExtrasSection({
  orderId,
  extras,
  onRefresh,
}: {
  orderId: string;
  extras: OrderExtras;
  onRefresh: () => void;
}) {
  const enabled = extras.extrasEnabled ?? false;
  const [activeTab, setActiveTab] = useState<'extra'>('extra');
  const [items, setItems] = useState<OrderExtraItem[]>(extras.extraItems ?? []);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setItems(extras.extraItems ?? []);
  }, [extras.extraItems]);

  async function persist(next: Partial<OrderExtras>) {
    setSaving(true);
    try {
      const merged: OrderExtras = { ...extras, ...next };
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  async function toggleEnabled(checked: boolean) {
    if (checked) {
      const starter = extras.extraItems?.length ? extras.extraItems : [];
      setItems(starter);
      await persist({ extrasEnabled: true, extraItems: starter });
    } else {
      await persist({ extrasEnabled: false });
    }
  }

  function updateItem(id: string, patch: Partial<OrderExtraItem>) {
    setItems((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  function addNewExtra() {
    setItems((prev) => [...prev, newExtraItem()]);
  }

  function removeRow(id: string) {
    setItems((prev) => prev.filter((row) => row.id !== id));
  }

  async function saveItems() {
    const cleaned = cleanItems(items);
    await persist({ extrasEnabled: true, extraItems: cleaned });
    setItems(cleaned);
  }

  const savedCount = cleanItems(extras.extraItems ?? []).length;

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mt-6">
      <label className="flex items-start gap-3 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => toggleEnabled(e.target.checked)}
          disabled={saving}
          className="mt-1 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)]"
        />
        <span>
          <span className="text-base font-semibold text-[var(--foreground)] block">
            Add extras for this order
          </span>
          <span className="text-sm text-[var(--muted)]">
            Optional — paniyaram box, thambula, sweet box, kobri design, etc. Shown on{' '}
            <strong>order copy only</strong>, not kitchen copy.
          </span>
        </span>
      </label>

      {enabled && (
        <div className="mt-6 border-t border-[var(--border)] pt-6">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4 border-b border-[var(--border)] pb-3">
            <button
              type="button"
              onClick={() => setActiveTab('extra')}
              className={`px-4 py-2 text-sm font-semibold border-b-2 -mb-[13px] transition-colors ${
                activeTab === 'extra'
                  ? 'border-[var(--primary)] text-[var(--primary)]'
                  : 'border-transparent text-[var(--muted)] hover:text-[var(--foreground)]'
              }`}
            >
              Extra {savedCount > 0 ? `(${savedCount})` : ''}
            </button>
            <Button
              type="button"
              onClick={addNewExtra}
              disabled={saving}
              className="!py-2 !px-4 text-sm inline-flex items-center gap-1.5"
            >
              <Plus size={16} /> Add new extra item
            </Button>
          </div>

          {activeTab === 'extra' && (
            <div className="space-y-4">
              {items.length === 0 ? (
                <div className="text-center py-10 rounded-xl border border-dashed border-[var(--border)] bg-[var(--background)]">
                  <p className="text-sm text-[var(--muted)] mb-4">
                    No extra items yet. Click below to add paniyaram, thambula, or any other extra.
                  </p>
                  <Button type="button" onClick={addNewExtra} className="inline-flex items-center gap-1.5">
                    <Plus size={16} /> Add new extra item
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto border border-[var(--border-strong)] rounded-lg">
                  <table className="w-full text-sm border-collapse">
                    <thead>
                      <tr className="bg-[var(--table-header-bg)] border-b border-[var(--border-strong)]">
                        <th className="text-left p-3 font-bold w-[28%]">Item</th>
                        <th className="text-left p-3 font-bold">Description</th>
                        <th className="text-left p-3 font-bold w-[18%]">Quantity</th>
                        <th className="w-10" />
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((row) => (
                        <tr key={row.id} className="border-b border-[var(--border)] last:border-0 align-top">
                          <td className="p-2">
                            <input
                              value={row.title}
                              onChange={(e) => updateItem(row.id, { title: e.target.value })}
                              placeholder="Tat Paniyaram"
                              className="form-input w-full px-2 py-2 rounded text-sm font-semibold"
                            />
                          </td>
                          <td className="p-2">
                            <textarea
                              rows={2}
                              value={row.description}
                              onChange={(e) => updateItem(row.id, { description: e.target.value })}
                              placeholder="Chakli, Muchore, Thenkol…"
                              className="form-input w-full px-2 py-2 rounded text-sm min-h-[4rem]"
                            />
                          </td>
                          <td className="p-2">
                            <input
                              value={row.quantity}
                              onChange={(e) => updateItem(row.id, { quantity: e.target.value })}
                              placeholder="50 Box"
                              className="form-input w-full px-2 py-2 rounded text-sm font-semibold text-center"
                            />
                          </td>
                          <td className="p-2">
                            <button
                              type="button"
                              onClick={() => removeRow(row.id)}
                              className="p-2 rounded-md text-[var(--muted)] hover:text-red-600 hover:bg-red-50"
                              title="Remove"
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={addNewExtra}
                  className="inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-[var(--border)] hover:bg-[var(--sidebar-hover)]"
                >
                  <Plus size={16} /> Add another extra item
                </button>
                <Button type="button" onClick={saveItems} disabled={saving} className="!py-2 !px-4 text-sm">
                  {saving ? 'Saving…' : 'Save extras'}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {!enabled && savedCount > 0 && (
        <p className="text-xs text-[var(--muted)] mt-3">
          {savedCount} saved extra item(s) — tick the box to edit. They appear on order copy only.
        </p>
      )}
    </div>
  );
}

export function OrderExtrasTable({
  items,
  className = '',
}: {
  items: OrderExtraItem[];
  className?: string;
}) {
  const rows = cleanItems(items);
  if (rows.length === 0) return null;

  return (
    <div className={`mt-8 ${className}`}>
      <p className="copy-grid-meta font-bold mb-2">Extras</p>
      <div className="border border-[var(--border-strong)] overflow-hidden">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="bg-[var(--table-header-bg)] border-b border-[var(--border-strong)]">
              <th className="p-3 font-bold border-r border-[var(--border)] w-[30%]">Item</th>
              <th className="p-3 font-bold border-r border-[var(--border)]">Description</th>
              <th className="p-3 font-bold w-[20%]">Quantity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-b border-[var(--border)] last:border-0 align-top">
                <td className="p-3 font-semibold border-r border-[var(--border)]">{row.title}</td>
                <td className="p-3 border-r border-[var(--border)] whitespace-pre-wrap">{row.description}</td>
                <td className="p-3 font-semibold text-center">{row.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
