import { useEffect, useState } from 'react';
import { formatScheduleTime } from '../utils/orderNotes';

type Props = {
  id?: string;
  value: string; // HH:MM 24h or ''
  onChange: (hhmm: string) => void;
  onBlur?: () => void;
  disabled?: boolean;
  className?: string;
  'aria-label'?: string;
};

const MINUTE_OPTIONS = Array.from({ length: 12 }, (_, i) => String(i * 5).padStart(2, '0'));

function parseHHmm(value: string): { hour12: string; minute: string; period: 'AM' | 'PM' } {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
  if (!match) return { hour12: '', minute: '', period: 'AM' };
  let hour24 = Number(match[1]);
  const minute = Number(match[2]);
  if (Number.isNaN(hour24) || Number.isNaN(minute)) return { hour12: '', minute: '', period: 'AM' };
  hour24 = Math.min(23, Math.max(0, hour24));
  const period: 'AM' | 'PM' = hour24 >= 12 ? 'PM' : 'AM';
  let hour12 = hour24 % 12;
  if (hour12 === 0) hour12 = 12;
  return {
    hour12: String(hour12),
    minute: String(minute).padStart(2, '0'),
    period,
  };
}

function toHHmm(hour12Raw: string, minuteRaw: string, period: 'AM' | 'PM'): string | null {
  if (!hour12Raw.trim() || minuteRaw.trim() === '') return null;
  const hour12 = Number(hour12Raw);
  const minute = Number(minuteRaw);
  if (Number.isNaN(hour12) || Number.isNaN(minute)) return null;
  if (hour12 < 1 || hour12 > 12) return null;
  if (minute < 0 || minute > 59) return null;
  let h = hour12 % 12;
  if (period === 'PM') h += 12;
  if (period === 'AM' && hour12 === 12) h = 0;
  return `${String(h).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

/** Typeable time: hour · minute · AM/PM (stores HH:MM 24h). */
export function AmPmTimeInput({
  id,
  value,
  onChange,
  onBlur,
  disabled,
  className = '',
  'aria-label': ariaLabel,
}: Props) {
  const parsed = parseHHmm(value);
  const [hour, setHour] = useState(parsed.hour12);
  const [minute, setMinute] = useState(parsed.minute);
  const [period, setPeriod] = useState<'AM' | 'PM'>(parsed.period);

  useEffect(() => {
    const next = parseHHmm(value);
    setHour(next.hour12);
    setMinute(next.minute);
    setPeriod(next.period);
  }, [value]);

  function commit(nextHour: string, nextMinute: string, nextPeriod: 'AM' | 'PM') {
    const hhmm = toHHmm(nextHour, nextMinute, nextPeriod);
    if (hhmm) onChange(hhmm);
  }

  function handleBlur() {
    if (hour.trim() && minute.trim() !== '') {
      const normalizedMinute = minute.padStart(2, '0');
      if (normalizedMinute !== minute) setMinute(normalizedMinute);
      commit(hour, normalizedMinute, period);
    }
    onBlur?.();
  }

  const minuteChoices =
    minute && !MINUTE_OPTIONS.includes(minute)
      ? [...MINUTE_OPTIONS, minute].sort((a, b) => Number(a) - Number(b))
      : MINUTE_OPTIONS;

  return (
    <div
      className={`ampm-time ${className}`.trim()}
      role="group"
      aria-label={ariaLabel || (value ? formatScheduleTime(value) : 'Time')}
    >
      <input
        id={id}
        type="text"
        inputMode="numeric"
        disabled={disabled}
        value={hour}
        placeholder="hh"
        maxLength={2}
        onChange={(e) => {
          const next = e.target.value.replace(/\D/g, '').slice(0, 2);
          setHour(next);
          if (next && minute.trim() !== '') commit(next, minute, period);
        }}
        onBlur={handleBlur}
        className="form-input ampm-time-input"
        aria-label="Hour"
      />
      <span className="ampm-time-sep" aria-hidden>
        :
      </span>
      <select
        disabled={disabled}
        value={minute}
        onChange={(e) => {
          const next = e.target.value;
          setMinute(next);
          if (hour.trim() && next !== '') commit(hour, next, period);
        }}
        onBlur={handleBlur}
        className="form-select ampm-time-input ampm-time-minute"
        aria-label="Minute"
      >
        <option value="">mm</option>
        {minuteChoices.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      <select
        disabled={disabled}
        value={period}
        onChange={(e) => {
          const next = e.target.value === 'PM' ? 'PM' : 'AM';
          setPeriod(next);
          if (hour.trim() && minute.trim() !== '') commit(hour, minute, next);
        }}
        onBlur={handleBlur}
        className="form-select ampm-time-input ampm-time-period"
        aria-label="AM or PM"
      >
        <option value="AM">AM</option>
        <option value="PM">PM</option>
      </select>
    </div>
  );
}
