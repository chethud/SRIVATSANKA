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

function parseHHmm(value: string): { hour12: number; minute: number; period: 'AM' | 'PM' } {
  const match = /^(\d{1,2}):(\d{2})$/.exec(value.trim());
  if (!match) return { hour12: 12, minute: 0, period: 'AM' };
  let hour24 = Number(match[1]);
  const minute = Number(match[2]);
  if (Number.isNaN(hour24) || Number.isNaN(minute)) return { hour12: 12, minute: 0, period: 'AM' };
  hour24 = Math.min(23, Math.max(0, hour24));
  const period: 'AM' | 'PM' = hour24 >= 12 ? 'PM' : 'AM';
  let hour12 = hour24 % 12;
  if (hour12 === 0) hour12 = 12;
  return { hour12, minute: Math.min(59, Math.max(0, minute)), period };
}

function toHHmm(hour12: number, minute: number, period: 'AM' | 'PM'): string {
  let h = hour12 % 12;
  if (period === 'PM') h += 12;
  if (period === 'AM' && hour12 === 12) h = 0;
  return `${String(h).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
}

const HOURS = Array.from({ length: 12 }, (_, i) => i + 1);
const MINUTES = Array.from({ length: 12 }, (_, i) => i * 5); // 0,5,...,55

/** Time picker with explicit Hour / Minute / AM·PM (stores HH:MM 24h). */
export function AmPmTimeInput({
  id,
  value,
  onChange,
  onBlur,
  disabled,
  className = '',
  'aria-label': ariaLabel,
}: Props) {
  const parts = parseHHmm(value);
  const minuteOptions = MINUTES.includes(parts.minute)
    ? MINUTES
    : [...MINUTES, parts.minute].sort((a, b) => a - b);

  function emit(next: { hour12: number; minute: number; period: 'AM' | 'PM' }) {
    onChange(toHHmm(next.hour12, next.minute, next.period));
  }

  return (
    <div
      className={`ampm-time ${className}`.trim()}
      role="group"
      aria-label={ariaLabel || (value ? formatScheduleTime(value) : 'Time')}
    >
      <select
        id={id}
        value={parts.hour12}
        disabled={disabled}
        onChange={(e) => emit({ ...parts, hour12: Number(e.target.value) })}
        onBlur={onBlur}
        className="form-input ampm-time-select"
        aria-label="Hour"
      >
        {HOURS.map((h) => (
          <option key={h} value={h}>
            {h}
          </option>
        ))}
      </select>
      <span className="ampm-time-sep" aria-hidden>
        :
      </span>
      <select
        value={parts.minute}
        disabled={disabled}
        onChange={(e) => emit({ ...parts, minute: Number(e.target.value) })}
        onBlur={onBlur}
        className="form-input ampm-time-select"
        aria-label="Minute"
      >
        {minuteOptions.map((m) => (
          <option key={m} value={m}>
            {String(m).padStart(2, '0')}
          </option>
        ))}
      </select>
      <select
        value={parts.period}
        disabled={disabled}
        onChange={(e) => emit({ ...parts, period: e.target.value as 'AM' | 'PM' })}
        onBlur={onBlur}
        className="form-input ampm-time-select ampm-time-period"
        aria-label="AM or PM"
      >
        <option value="AM">AM</option>
        <option value="PM">PM</option>
      </select>
    </div>
  );
}
