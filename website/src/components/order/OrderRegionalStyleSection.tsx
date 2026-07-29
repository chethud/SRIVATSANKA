import { useEffect, useMemo, useState } from 'react';
import { MapPin } from 'lucide-react';
import { formatDate, updateEnquiry, type Enquiry } from '../../api/client';
import {
  eventDatesForStyles,
  expandScheduleDateRange,
  resolveStyleForDate,
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

export function OrderRegionalStyleSection({
  orderId,
  order,
  extras,
  onOrderUpdated,
}: {
  orderId: string;
  order: Enquiry;
  extras: OrderExtras;
  onOrderUpdated: (order: Enquiry) => void;
}) {
  const days = useMemo(() => {
    const scheduled = expandScheduleDateRange(extras);
    if (scheduled.length > 0) return scheduled;
    return eventDatesForStyles(extras, order.eventDate);
  }, [extras, order.eventDate]);

  const [byDate, setByDate] = useState<Record<string, string>>(() => ({
    ...(extras.regionalStylesByDate ?? {}),
  }));
  const [customByDate, setCustomByDate] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Only show styles the user saved per day — never seed every day from a global style
    setByDate({ ...(extras.regionalStylesByDate ?? {}) });
  }, [extras.regionalStylesByDate]);

  function setDayStyle(date: string, style: string) {
    setByDate((prev) => {
      const next = { ...prev };
      const trimmed = style.trim();
      if (!trimmed) delete next[date];
      else next[date] = trimmed;
      return next;
    });
  }

  async function save() {
    setSaving(true);
    try {
      const cleaned = Object.fromEntries(
        Object.entries(byDate)
          .map(([k, v]) => [k.slice(0, 10), v.trim()] as const)
          .filter(([, v]) => Boolean(v)),
      );
      const unique = [...new Set(Object.values(cleaned))];
      const merged: OrderExtras = {
        ...extras,
        regionalStylesByDate: cleaned,
        // Clear legacy globals so style is not implied for every day
        regionalStyles: unique,
        regionalStyle: null,
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
        Optional — add a style only for the days you want (e.g. Day 1 Kerala). Leave other days blank.
        Printed on kitchen and order copies under that day only.
      </p>

      <div className="space-y-4">
        {days.map((date, index) => {
          const value = byDate[date] ?? '';
          return (
            <div
              key={date}
              className={`order-style-day ${value ? 'order-style-day--set' : ''}`}
            >
              <div className="order-style-day-head">
                <p className="order-style-day-title">
                  Day {index + 1} · {formatDate(date)}
                </p>
                {value ? (
                  <button
                    type="button"
                    onClick={() => {
                      setDayStyle(date, '');
                      setCustomByDate((prev) => {
                        const next = { ...prev };
                        delete next[date];
                        return next;
                      });
                    }}
                    className="text-xs font-semibold text-[var(--muted)] hover:text-[var(--danger)]"
                  >
                    Clear
                  </button>
                ) : (
                  <span className="text-xs text-[var(--muted)]">No style</span>
                )}
              </div>
              <div className="flex flex-wrap gap-2 mb-3">
                {REGIONAL_STYLE_PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => setDayStyle(date, value === preset ? '' : preset)}
                    className={`order-preset-chip ${value === preset ? 'order-preset-chip--active' : ''}`}
                  >
                    {preset}
                  </button>
                ))}
                {value && !REGIONAL_STYLE_PRESETS.includes(value as (typeof REGIONAL_STYLE_PRESETS)[number]) && (
                  <span className="order-preset-chip order-preset-chip--active">{value}</span>
                )}
              </div>
              <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--order-accent)] mb-1.5">
                Custom style for this day (optional)
              </label>
              <input
                type="text"
                value={customByDate[date] ?? (REGIONAL_STYLE_PRESETS.includes(value as never) ? '' : value)}
                onChange={(e) => {
                  const next = e.target.value;
                  setCustomByDate((prev) => ({ ...prev, [date]: next }));
                  setDayStyle(date, next);
                }}
                placeholder="Leave blank, or e.g. Iyengar style…"
                className="form-input w-full px-3 py-2 rounded-lg text-sm font-semibold"
              />
            </div>
          );
        })}
      </div>

      <p className="text-xs text-[var(--muted)] mt-3 mb-4">
        Days come from the event schedule date range. You do not need a style on every day.
      </p>

      <Button type="button" onClick={() => void save()} disabled={saving} className="!py-2 !px-4 text-sm">
        {saving ? 'Saving…' : 'Save day styles'}
      </Button>
    </div>
  );
}

export function OrderRegionalStylePrint({
  stylesByDate,
}: {
  stylesByDate: { date: string; style: string }[];
}) {
  const list = stylesByDate.filter((row) => row.style.trim());
  if (list.length === 0) return null;

  return (
    <div className="copy-regional-style">
      <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
        Regional / cuisine style by day
      </div>
      <div className="px-4 py-3 space-y-1.5">
        {list.map((row) => (
          <p key={row.date} className="text-center copy-client-line font-bold">
            {formatDate(row.date)} — {row.style}
          </p>
        ))}
      </div>
    </div>
  );
}

export function styleLabelForCopyDate(extras: OrderExtras, date: string): string | null {
  return resolveStyleForDate(extras, date);
}
