import { useEffect, useState } from 'react';
import { MapPin } from 'lucide-react';
import { updateEnquiry, type Enquiry } from '../../api/client';
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
  onOrderUpdated,
}: {
  orderId: string;
  extras: OrderExtras;
  onOrderUpdated: (order: Enquiry) => void;
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
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="order-section">
      <div className="order-section-head">
        <div className="order-section-title">
          <span className="order-section-icon order-section-icon--gold">
            <MapPin size={18} />
          </span>
          Regional / cuisine style
        </div>
      </div>
      <p className="order-section-sub">
        Set the style the client wants — printed on the kitchen copy after client details and before the menu.
      </p>

      <div className="flex flex-wrap gap-2 mb-4">
        {REGIONAL_STYLE_PRESETS.map((preset) => (
          <button
            key={preset}
            type="button"
            onClick={() => setValue(preset)}
            className={`order-preset-chip ${value === preset ? 'order-preset-chip--active' : ''}`}
          >
            {preset}
          </button>
        ))}
      </div>

      <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)] mb-1.5">
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
    <div className="copy-regional-style">
      <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
        Regional / cuisine style
      </div>
      <div className="px-4 py-4 text-center copy-client-line font-bold">{text}</div>
    </div>
  );
}
