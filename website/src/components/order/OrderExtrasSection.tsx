import { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { updateEnquiry, type Enquiry } from '../../api/client';
import {
  activeOrderExtraItems,
  isOverallTotalExtra,
  mergeOrderExtraItems,
  serializeOrderNotes,
  type OrderExtraItem,
  type OrderExtras,
} from '../../utils/orderNotes';
import { Button } from '../Layout';
import { formatColumnAmount } from '../../utils/orderMenuGrid';
import { isKitchenSpecification } from '../../utils/kitchenSpecs';

function newCustomExtraItem(): OrderExtraItem {
  return {
    id: `extra_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`,
    title: '',
    description: '',
    quantity: '',
    amount: null,
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
      amount: row.amount != null && !Number.isNaN(row.amount) && row.amount > 0 ? row.amount : null,
      enabled: row.enabled ?? false,
      overallTotal:
        row.overallTotal === true || /\bgrand\s*total\b/i.test(row.title.trim()),
    }))
    .filter((row) => row.isCustom ? row.title || row.description || row.quantity || row.enabled : true);
}

export function OrderExtrasSection({
  orderId,
  extras,
  onOrderUpdated,
}: {
  orderId: string;
  extras: OrderExtras;
  onOrderUpdated: (order: Enquiry) => void;
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
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
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
    setItems((prev) =>
      prev.map((row) => {
        if (row.id === id) {
          const next = { ...row, ...patch };
          if (typeof patch.title === 'string' && /\bgrand\s*total\b/i.test(patch.title.trim())) {
            next.overallTotal = true;
          }
          return next;
        }
        if (patch.overallTotal === true) {
          return { ...row, overallTotal: false };
        }
        return row;
      }),
    );
  }

  function setOverallTotalLine(id: string, on: boolean) {
    setItems((prev) =>
      prev.map((row) => ({
        ...row,
        overallTotal: row.id === id ? on : on ? false : row.overallTotal,
      })),
    );
  }

  function toggleItem(id: string, checked: boolean) {
    setItems((prev) =>
      prev.map((row) =>
        row.id === id
          ? {
              ...row,
              enabled: checked,
              ...(checked ? {} : { description: '', quantity: '', amount: null }),
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
        className={`order-extra-row ${checked ? 'order-extra-row--active' : ''}`}
      >
        <div className="flex items-start gap-3">
          <label className="mt-1 shrink-0 cursor-pointer">
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => toggleItem(row.id, e.target.checked)}
              disabled={saving}
              className="h-4 w-4 rounded border-[var(--border)] text-[var(--primary)]"
              aria-label={row.title ? `Enable ${row.title}` : 'Enable custom extra'}
            />
          </label>
          <div className="flex-1 min-w-0">
            <div className="flex items-start gap-2 mb-3">
              {row.isCustom ? (
                <input
                  value={row.title}
                  onChange={(e) => updateItem(row.id, { title: e.target.value })}
                  placeholder="Extra item name"
                  disabled={saving}
                  className="order-extra-title-input flex-1 min-w-0"
                />
              ) : (
                <span className="text-sm font-semibold text-[var(--foreground)] flex-1 pt-0.5">
                  {row.title}
                </span>
              )}
              {row.isCustom && (
                <button
                  type="button"
                  onClick={() => removeCustomRow(row.id)}
                  disabled={saving}
                  className="p-1.5 rounded-md text-[var(--muted)] hover:text-red-600 hover:bg-red-50 shrink-0"
                  title="Remove custom extra"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>

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
                <div className="lg:col-span-4 flex flex-col gap-3">
                  <div>
                    <label className="text-xs font-medium text-[var(--order-accent)] mb-1 block">Quantity</label>
                    <input
                      value={row.quantity}
                      onChange={(e) => updateItem(row.id, { quantity: e.target.value })}
                      placeholder="e.g. 50 Box, 300 pax"
                      disabled={saving}
                      className="form-input w-full px-3 py-2 rounded-lg text-sm font-semibold"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-[var(--order-accent)] mb-1 block">Amount</label>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm text-[var(--muted)] pointer-events-none">
                        ₹
                      </span>
                      <input
                        type="text"
                        inputMode="numeric"
                        value={row.amount != null ? String(row.amount) : ''}
                        onChange={(e) => {
                          const digits = e.target.value.replace(/[^\d]/g, '');
                          updateItem(row.id, { amount: digits ? Number(digits) : null });
                        }}
                        placeholder="Enter amount"
                        disabled={saving}
                        className="form-input w-full pl-8 pr-3 py-2 rounded-lg text-sm font-semibold"
                      />
                    </div>
                    <label className="flex items-start gap-2 mt-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={row.overallTotal === true || isOverallTotalExtra(row)}
                        onChange={(e) => setOverallTotalLine(row.id, e.target.checked)}
                        disabled={saving || !row.amount}
                        className="mt-0.5 h-4 w-4 rounded border-[var(--border)] text-[var(--primary)] shrink-0"
                      />
                      <span className="text-xs text-[var(--muted)] leading-snug">
                        This amount is the <strong>overall total</strong> on order copy (not added with session
                        totals). Or title the row <strong>Grand Total</strong>.
                      </span>
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="order-section">
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
                Check each extra the client wants, then add description, quantity, and amount — like your Excel extras sheet.
              </p>

              <div className="space-y-3">
                {items.map(renderExtraRow)}
              </div>

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
  hideAmounts = false,
  highlightSpecs = false,
}: {
  items: OrderExtraItem[];
  className?: string;
  /** Kitchen copy: list extras without ₹ amounts */
  hideAmounts?: boolean;
  /** Kitchen copy: Garlands / allergy-style titles in red */
  highlightSpecs?: boolean;
}) {
  const rows = activeOrderExtraItems(items);
  if (rows.length === 0) return null;

  return (
    <div className={`mt-8 ${className}`}>
      <p className="copy-grid-meta font-bold mb-2">Extras</p>
      <div className="border border-[var(--border-strong)] overflow-x-auto">
        <table className="w-full border-collapse text-left min-w-[32rem]">
          <thead>
            <tr className="bg-[var(--table-header-bg)] border-b border-[var(--border-strong)]">
              <th className="p-3 font-bold border-r border-[var(--border)] w-[22%]">Item</th>
              <th className="p-3 font-bold border-r border-[var(--border)]">Description</th>
              <th className={`p-3 font-bold ${hideAmounts ? '' : 'border-r border-[var(--border)]'} w-[18%]`}>
                Quantity
              </th>
              {!hideAmounts && <th className="p-3 font-bold w-[16%] text-right">Amount</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const titleSpec = highlightSpecs && isKitchenSpecification(row.title);
              const descSpec = highlightSpecs && isKitchenSpecification(row.description);
              return (
                <tr key={row.id} className="border-b border-[var(--border)] last:border-0 align-top">
                  <td
                    className={`p-3 font-semibold border-r border-[var(--border)] ${titleSpec ? 'copy-spec-text' : ''}`}
                  >
                    {row.title}
                  </td>
                  <td
                    className={`p-3 border-r border-[var(--border)] whitespace-pre-wrap ${descSpec ? 'copy-spec-text' : ''}`}
                  >
                    {row.description}
                  </td>
                  <td
                    className={`p-3 font-semibold text-center ${hideAmounts ? '' : 'border-r border-[var(--border)]'}`}
                  >
                    {row.quantity}
                  </td>
                  {!hideAmounts && (
                    <td className="p-3 font-semibold text-right">
                      {formatColumnAmount(row.amount) || '—'}
                      {isOverallTotalExtra(row) && (
                        <span className="block text-[10px] font-bold uppercase tracking-wide text-[var(--primary)] mt-1">
                          Overall total
                        </span>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
