import { useEffect, useMemo, useState } from 'react';
import { MapPin } from 'lucide-react';
import { formatDate, updateEnquiry, type Enquiry } from '../../api/client';
import { normalizeDateOnly } from '../../utils/dateOnly';
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

function isPresetStyle(value: string): boolean {
  return REGIONAL_STYLE_PRESETS.includes(value as (typeof REGIONAL_STYLE_PRESETS)[number]);
}

function normalizeStyleMap(map: Record<string, string> | undefined): Record<string, string> {
  if (!map) return {};
  return Object.fromEntries(
    Object.entries(map)
      .map(([k, v]) => [normalizeDateOnly(k), v.trim()] as const)
      .filter(([k, v]) => Boolean(k) && Boolean(v)),
  );
}

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

  const [byDate, setByDate] = useState<Record<string, string>>(() =>
    normalizeStyleMap(extras.regionalStylesByDate),
  );
  const [customByDate, setCustomByDate] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setByDate(normalizeStyleMap(extras.regionalStylesByDate));
  }, [order.notes]);

  function dayKey(date: string): string {
    return normalizeDateOnly(date);
  }

  function styleForDay(date: string): string {
    return byDate[dayKey(date)] ?? '';
  }

  function setDayStyle(date: string, style: string) {
    const key = dayKey(date);
    setByDate((prev) => {
      const next = { ...prev };
      const trimmed = style.trim();
      if (!trimmed) delete next[key];
      else next[key] = trimmed;
      return next;
    });
  }

  async function save() {
    setSaving(true);
    try {
      const cleaned = normalizeStyleMap(byDate);
      const unique = [...new Set(Object.values(cleaned))];
      const merged: OrderExtras = {
        ...extras,
        regionalStylesByDate: cleaned,
        regionalStyles: unique,
        regionalStyle: null,
      };
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not save day styles. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  const styledCount = days.filter((d) => Boolean(styleForDay(d))).length;

  return (
    <div className="order-section order-section--compact">
      <div className="order-section-head order-section-head--tight">
        <div className="order-section-title">
          <span className="order-section-icon order-section-icon--gold">
            <MapPin size={16} />
          </span>
          Regional / cuisine style
          {styledCount > 0 && (
            <span className="order-section-count">{styledCount} day{styledCount === 1 ? '' : 's'}</span>
          )}
        </div>
        <Button type="button" onClick={() => void save()} disabled={saving} className="!py-1.5 !px-3 text-xs shrink-0">
          {saving ? 'Saving…' : 'Save'}
        </Button>
      </div>
      <p className="order-section-sub order-section-sub--compact">
        Optional per day — shown on kitchen copies for that day only.
      </p>

      <div className="order-style-list">
        {days.map((date, index) => {
          const value = styleForDay(date);
          const key = dayKey(date);
          return (
            <div
              key={key}
              className={`order-style-day order-style-day--compact ${value ? 'order-style-day--set' : ''}`}
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
                        delete next[key];
                        return next;
                      });
                    }}
                    className="text-xs font-semibold text-[var(--muted)] hover:text-[var(--danger)] shrink-0"
                  >
                    Clear
                  </button>
                ) : (
                  <span className="text-xs text-[var(--muted)] shrink-0">Optional</span>
                )}
              </div>
              <div className="order-style-day-body order-style-day-body--always">
                <div className="order-style-presets">
                  {REGIONAL_STYLE_PRESETS.map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      onClick={() => setDayStyle(date, value === preset ? '' : preset)}
                      className={`order-preset-chip order-preset-chip--sm ${value === preset ? 'order-preset-chip--active' : ''}`}
                    >
                      {preset.replace(' style', '')}
                    </button>
                  ))}
                  {value && !isPresetStyle(value) && (
                    <span className="order-preset-chip order-preset-chip--sm order-preset-chip--active">{value}</span>
                  )}
                </div>
                <input
                  type="text"
                  value={customByDate[key] ?? (isPresetStyle(value) ? '' : value)}
                  onChange={(e) => {
                    const next = e.target.value;
                    setCustomByDate((prev) => ({ ...prev, [key]: next }));
                    setDayStyle(date, next);
                  }}
                  placeholder="Other style (optional)"
                  className="form-input order-style-custom w-full px-2.5 py-1.5 rounded-lg text-sm"
                />
              </div>
            </div>
          );
        })}
      </div>
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
