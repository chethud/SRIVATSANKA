const DATE_ONLY_RE = /^(\d{4})-(\d{2})-(\d{2})/;

const MONTHS_SHORT = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
];

/** Calendar YYYY-MM-DD from API / form values — never shifts by timezone. */
export function normalizeDateOnly(value: string | null | undefined): string {
  if (!value?.trim()) return '';
  const m = DATE_ONLY_RE.exec(value.trim());
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '';
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
}

/** Local noon — safe for ExcelJS date cells (avoids UTC-midnight off-by-one). */
export function parseDateOnlyLocal(value: string): Date | null {
  const iso = normalizeDateOnly(value);
  if (!iso) return null;
  const [y, mo, d] = iso.split('-').map(Number);
  return new Date(y, mo - 1, d, 12, 0, 0, 0);
}

export function todayDateOnlyLocal(): string {
  const d = new Date();
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
}

/** en-IN display: 18 Jan 2025 */
export function formatDateOnlyDisplay(value: string): string {
  const d = parseDateOnlyLocal(value);
  if (!d) return value;
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

/** Tax invoice: dd/mm/yyyy */
export function formatInvoiceDateOnly(value: string): string {
  const iso = normalizeDateOnly(value);
  if (!iso) return value;
  const [y, mo, d] = iso.split('-');
  return `${d}/${mo}/${y}`;
}

/** Menu sheet row 3 — dd-mmm-yy text (matches reference Excels). */
export function formatMenuExcelDateText(value: string): string {
  const iso = normalizeDateOnly(value);
  if (!iso) return value;
  const [y, mo, d] = iso.split('-').map(Number);
  const yy = String(y).slice(-2);
  return `${String(d).padStart(2, '0')}-${MONTHS_SHORT[mo - 1]}-${yy}`;
}

/** Client header for multi-day events: "Jan 17-18-19, 2025" */
export function formatEventDateRangeLabel(dates: string[]): string {
  const normalized = [...new Set(dates.map(normalizeDateOnly).filter(Boolean))].sort();
  if (normalized.length === 0) return '';
  if (normalized.length === 1) return formatDateOnlyDisplay(normalized[0]);

  const first = normalized[0];
  const last = normalized[normalized.length - 1];
  const [y1, mo1] = first.split('-').map(Number);
  const [y2, mo2] = last.split('-').map(Number);
  const m1 = MONTHS_SHORT[mo1 - 1];

  if (y1 === y2 && mo1 === mo2) {
    const days = normalized.map((d) => Number(d.split('-')[2]));
    return `${m1} ${days.join('-')}, ${y2}`;
  }

  return `${formatDateOnlyDisplay(first)} – ${formatDateOnlyDisplay(last)}`;
}
