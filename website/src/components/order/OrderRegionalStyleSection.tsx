import { useEffect, useState } from 'react';
import { MapPin, Plus, X } from 'lucide-react';
import { updateEnquiry, type Enquiry } from '../../api/client';
import {
  resolveRegionalStyles,
  serializeOrderNotes,
  type OrderExtras,
} from '../../utils/orderNotes';
import { Button } from '../Layout';

export const REGIONAL_STYLE_PRESETS = [
  'Kerala style',
  'Tamil Nadu style',
  'Karnataka style',
  'Andhra style',
] as const;

function persistStyles(styles: string[]): Pick<OrderExtras, 'regionalStyles' | 'regionalStyle'> {
  const unique = [...new Set(styles.map((s) => s.trim()).filter(Boolean))];
  return {
    regionalStyles: unique,
    regionalStyle: unique[0] ?? null,
  };
}

export function OrderRegionalStyleSection({
  orderId,
  extras,
  onOrderUpdated,
}: {
  orderId: string;
  extras: OrderExtras;
  onOrderUpdated: (order: Enquiry) => void;
}) {
  const [selected, setSelected] = useState<string[]>(() => resolveRegionalStyles(extras));
  const [custom, setCustom] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setSelected(resolveRegionalStyles(extras));
  }, [extras]);

  async function save(next: string[]) {
    setSaving(true);
    try {
      const merged: OrderExtras = {
        ...extras,
        ...persistStyles(next),
      };
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
    } finally {
      setSaving(false);
    }
  }

  function togglePreset(preset: string) {
    setSelected((prev) =>
      prev.includes(preset) ? prev.filter((s) => s !== preset) : [...prev, preset],
    );
  }

  function removeStyle(style: string) {
    setSelected((prev) => prev.filter((s) => s !== style));
  }

  function addCustom() {
    const name = custom.trim();
    if (!name) return;
    setSelected((prev) => (prev.includes(name) ? prev : [...prev, name]));
    setCustom('');
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
        Select one or more styles for this order — shown on kitchen and order copies. Use this when one
        booking needs different cuisines (e.g. Tamil Nadu + Kerala).
      </p>

      <div className="flex flex-wrap gap-2 mb-4">
        {REGIONAL_STYLE_PRESETS.map((preset) => {
          const active = selected.includes(preset);
          return (
            <button
              key={preset}
              type="button"
              onClick={() => togglePreset(preset)}
              className={`order-preset-chip ${active ? 'order-preset-chip--active' : ''}`}
            >
              {preset}
            </button>
          );
        })}
      </div>

      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {selected.map((style) => (
            <span
              key={style}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold bg-[var(--primary)]/10 text-[var(--primary)] border border-[var(--primary)]/30"
            >
              {style}
              <button
                type="button"
                onClick={() => removeStyle(style)}
                className="hover:opacity-70"
                aria-label={`Remove ${style}`}
              >
                <X size={14} />
              </button>
            </span>
          ))}
        </div>
      )}

      <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)] mb-1.5">
        Add custom style
      </label>
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          type="text"
          value={custom}
          onChange={(e) => setCustom(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addCustom();
            }
          }}
          placeholder="e.g. Iyengar style, Chettinad…"
          className="form-input flex-1 min-w-[200px] px-3 py-2.5 rounded-lg text-base font-semibold"
        />
        <Button
          type="button"
          onClick={addCustom}
          disabled={!custom.trim()}
          className="!py-2 !px-3 text-sm inline-flex items-center gap-1"
        >
          <Plus size={16} /> Add
        </Button>
      </div>

      <Button
        type="button"
        onClick={() => void save(selected)}
        disabled={saving}
        className="!py-2 !px-4 text-sm"
      >
        {saving ? 'Saving…' : 'Save styles'}
      </Button>
    </div>
  );
}

export function OrderRegionalStylePrint({ styles }: { styles: string[] }) {
  const list = styles.map((s) => s.trim()).filter(Boolean);
  if (list.length === 0) return null;

  return (
    <div className="copy-regional-style">
      <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
        Regional / cuisine style{list.length > 1 ? 's' : ''}
      </div>
      <div className="px-4 py-4 text-center copy-client-line font-bold">
        {list.join(' · ')}
      </div>
    </div>
  );
}
