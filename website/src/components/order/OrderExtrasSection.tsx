import { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { updateEnquiry } from '../../api/client';
import {
  activeOrderExtraItems,
  mergeOrderExtraItems,
  serializeOrderNotes,
  type OrderExtraItem,
  type OrderExtras,
} from '../../utils/orderNotes';
import { Button } from '../Layout';

function newCustomExtraItem(): OrderExtraItem {
  return {
    id: `extra_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    title: '',
    description: '',
    quantity: '',
    enabled: true,
    isCustom: true,
  };
}

function normalizeForSave(items: OrderExtraItem[]): OrderExtraItem[] {
  return items
    .map((row) => ({
      ...row,
      title: row.title.trim(),
      description: row.description.trim(),
      quantity: row.quantity.trim(),
      enabled: row.enabled ?? false,
    }))
    .filter((row) => row.isCustom ? row.title || row.description || row.quantity || row.enabled : true);
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
  const [items, setItems] = useState<OrderExtraItem[]>(() => mergeOrderExtraItems(extras.extraItems));
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setItems(mergeOrderExtraItems(extras.extraItems));
  }, [extras.extraItems]);

  const savedActiveCount = useMemo(
    () => activeOrderExtraItems(extras.extraItems).length,
    [extras.extraItems],
  );

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

  async function toggleSection(checked: boolean) {
    if (checked) {
      const starter = mergeOrderExtraItems(extras.extraItems);
      setItems(starter);
      await persist({ extrasEnabled: true, extraItems: normalizeForSave(starter) });
    } else {
      await persist({ extrasEnabled: false });
    }
  }

  function updateItem(id: string, patch: Partial<OrderExtraItem>) {
    setItems((prev) => prev.map((row) => (row.id === id ? { ...row, ...patch } : row)));
  }

  function toggleItem(id: string, checked: boolean) {
    setItems((prev) =>
      prev.map((row) =>
        row.id === id
          ? {
              ...row,
              enabled: checked,
              ...(checked ? {} : { description: '', quantity: '' }),
            }
          : row,
      ),
    );
  }

  function addCustomExtra() {
    setItems((prev) => [...prev, newCustomExtraItem()]);
  }

  function removeCustomRow(id: string) {
    setItems((prev) => prev.filter((row) => row.id !== id));
  }

  async function saveItems() {
    const cleaned = normalizeForSave(items);
    const hasActive = cleaned.some((row) => row.enabled);
    await persist({
      extrasEnabled: hasActive || enabled,
      extraItems: cleaned,
    });
    setItems(mergeOrderExtraItems(cleaned));
  }

  function renderExtraRow(row: OrderExtraItem) {
    const checked = row.enabled ?? false;

    return (
      <div
        key={row.id}
        className={`rounded-xl border p-4 transition-colors ${
          checked
            ? 'border-[var(--primary)]/40 bg-[var(--background)]'
            : 'border-[var(--border)] bg-[var(--card)]'
        }`}
      >
        <label className="flex items-start gap-3 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => toggleItem(row.id, e.target.checked)}
            disabled={saving}
            className="mt-1 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)] shrink-0"
          />
          <div className="flex-1 min-w-0">
            {row.isCustom ? (
              <input
                value={row.title}
                onChange={(e) => updateItem(row.id, { title: e.target.value })}
                placeholder="Extra item name"
                disabled={!checked || saving}
                className="form-input w-full px-3 py-2 rounded-lg text-sm font-semibold mb-3 disabled:opacity-50"
              />
            ) : (
              <span className="text-sm font-semibold text-[var(--foreground)] block mb-3">{row.title}</span>
            )}

            {checked && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
                <div className="lg:col-span-8">
                  <label className="text-xs font-medium text-[var(--order-accent)] mb-1 block">
                    Brief description (what the client needs)
                  </label>
                  <textarea
                    rows={3}
                    value={row.description}
                    onChange={(e) => updateItem(row.id, { description: e.target.value })}
                    placeholder="e.g. Chakli, Muchore, Thenkol, Spl Boondhi Ladoo…"
                    disabled={saving}
                    className="form-input w-full px-3 py-2 rounded-lg text-sm min-h-[5rem]"
                  />
                </div>
                <div className="lg:col-span-4">
                  <label className="text-xs font-medium text-[var(--order-accent)] mb-1 block">Quantity</label>
                  <input
                    value={row.quantity}
                    onChange={(e) => updateItem(row.id, { quantity: e.target.value })}
                    placeholder="e.g. 50 Box, 300 pax"
                    disabled={saving}
                    className="form-input w-full px-3 py-2 rounded-lg text-sm font-semibold"
                  />
                </div>
              </div>
            )}
          </div>
          {row.isCustom && (
            <button
              type="button"
              onClick={() => removeCustomRow(row.id)}
              disabled={saving}
              className="p-2 rounded-md text-[var(--muted)] hover:text-red-600 hover:bg-red-50 shrink-0"
              title="Remove custom extra"
            >
              <Trash2 size={16} />
            </button>
          )}
        </label>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mb-6">
      <label className="flex items-start gap-3 cursor-pointer select-none">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => toggleSection(e.target.checked)}
          disabled={saving}
          className="mt-1 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)]"
        />
        <span>
          <span className="text-base font-semibold text-[var(--foreground)] block">
            Add extras for this order
          </span>
          <span className="text-sm text-[var(--muted)]">
            Tick only what the client needs — paniyaram, thambula, sweet box, kobri design, etc. Shown on{' '}
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
              Extra {savedActiveCount > 0 ? `(${savedActiveCount})` : ''}
            </button>
            <Button
              type="button"
              onClick={addCustomExtra}
              disabled={saving}
              className="!py-2 !px-4 text-sm inline-flex items-center gap-1.5"
            >
              <Plus size={16} /> Add new extra item
            </Button>
          </div>

          {activeTab === 'extra' && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--muted)]">
                Check each extra the client wants, then type the brief description and quantity — like your Excel extras sheet.
              </p>

              <div className="space-y-3">
                {items.filter((row) => !row.isCustom).map(renderExtraRow)}
              </div>

              {items.some((row) => row.isCustom) && (
                <div className="pt-4 border-t border-dashed border-[var(--border)] space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)]">
                    Custom extras
                  </p>
                  {items.filter((row) => row.isCustom).map(renderExtraRow)}
                </div>
              )}

              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  type="button"
                  onClick={addCustomExtra}
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

      {!enabled && savedActiveCount > 0 && (
        <p className="text-xs text-[var(--muted)] mt-3">
          {savedActiveCount} saved extra item(s) — tick the box above to edit. They appear on order copy only.
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
  const rows = activeOrderExtraItems(items);
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
