import { useEffect, useState } from 'react';
import { updateEnquiry } from '../../api/client';
import { serializeOrderNotes, type OrderExtras } from '../../utils/orderNotes';
import { Button } from '../Layout';

export const REGIONAL_STYLE_PRESETS = [
  'Kerala style',
  'Tamil Nadu style',
  'Karnataka style',
  'Andhra style',
] as const;

export function OrderRegionalStyleSection({
  orderId,
  extras,
  onRefresh,
}: {
  orderId: string;
  extras: OrderExtras;
  onRefresh: () => void;
}) {
  const [value, setValue] = useState(extras.regionalStyle ?? '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setValue(extras.regionalStyle ?? '');
  }, [extras.regionalStyle]);

  async function save(next: string) {
    setSaving(true);
    try {
      const trimmed = next.trim();
      const merged: OrderExtras = {
        ...extras,
        regionalStyle: trimmed || null,
      };
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mb-6">
      <h2 className="order-view-title text-xl font-semibold text-[var(--foreground)] mb-1">
        Regional / cuisine style
      </h2>
      <p className="text-sm text-[var(--muted)] mb-4">
        Set the style the client wants — printed at the bottom of both kitchen copy and order copy.
      </p>

      <div className="flex flex-wrap gap-2 mb-4">
        {REGIONAL_STYLE_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => setValue(preset)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              value === preset
                ? 'bg-[var(--primary)] text-white border-[var(--primary)]'
                : 'bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--primary)]'
            }`}
          >
            {preset}
          </button>
        ))}
      </div>

      <label className="block text-xs font-medium text-[var(--order-accent)] mb-1">
        Style (type or pick above)
      </label>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="e.g. Kerala style, Tamil Nadu style…"
        className="form-input w-full px-3 py-2.5 rounded-lg text-base font-semibold mb-4"
      />

      <Button type="button" onClick={() => save(value)} disabled={saving} className="!py-2 !px-4 text-sm">
        {saving ? 'Saving…' : 'Save regional style'}
      </Button>
    </div>
  );
}

export function OrderRegionalStylePrint({ style }: { style: string | null | undefined }) {
  const text = style?.trim();
  if (!text) return null;

  return (
    <div className="mt-8 border border-[var(--border-strong)] overflow-hidden">
      <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
        Regional / cuisine style
      </div>
      <div className="px-4 py-4 text-center copy-client-line font-bold">{text}</div>
    </div>
  );
}
