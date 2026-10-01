import type { Enquiry, EnquiryDish } from '../api/client';
import { normalizeDateOnly } from './dateOnly';
import { formatScheduleTime, type MenuColumn, type OrderExtras } from './orderNotes';
import { MEAL_SESSIONS, MEAL_SESSION_ORDER, PREFERENCE_CATEGORIES } from './mealSessions';

export type { MenuColumn };

function newColumnId(): string {
  return `col_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
}

export function formatPaxTimeLine(column: MenuColumn): string {
  const parts: string[] = [];
  if (column.pax != null && column.pax > 0) parts.push(`${column.pax} Pax`);
  if (column.timeFrom && column.timeTo) {
    parts.push(`${formatScheduleTime(column.timeFrom)} to ${formatScheduleTime(column.timeTo)}`);
  } else if (column.timeFrom) {
    parts.push(formatScheduleTime(column.timeFrom));
  }
  return parts.join('  ');
}

function timeSortMinutes(value: string | null | undefined): number {
  if (!value) return Number.POSITIVE_INFINITY;
  const [hRaw, mRaw] = value.split(':');
  const h = Number(hRaw);
  const m = Number(mRaw ?? 0);
  if (Number.isNaN(h) || Number.isNaN(m)) return Number.POSITIVE_INFINITY;
  return h * 60 + m;
}

/** Stack sessions top-to-bottom: date, then start time, then meal type / label. */
export function sortMenuColumns(columns: MenuColumn[]): MenuColumn[] {
  return [...columns].sort((a, b) => {
    const dateCmp = a.date.localeCompare(b.date);
    if (dateCmp !== 0) return dateCmp;

    const timeCmp = timeSortMinutes(a.timeFrom) - timeSortMinutes(b.timeFrom);
    if (timeCmp !== 0) return timeCmp;

    const ia = MEAL_SESSION_ORDER.indexOf(a.baseSession);
    const ib = MEAL_SESSION_ORDER.indexOf(b.baseSession);
    if (ia !== ib) {
      if (ia === -1) return 1;
      if (ib === -1) return -1;
      return ia - ib;
    }
    return a.sessionLabel.localeCompare(b.sessionLabel);
  });
}

function defaultDate(extras: OrderExtras, order: Enquiry): string {
  return normalizeDateOnly(extras.scheduleDateFrom ?? order.eventDate);
}

function menuItemsOnly(dishes: EnquiryDish[]): EnquiryDish[] {
  return dishes.filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
}

function mapColumn(
  c: MenuColumn,
  extras: OrderExtras,
): MenuColumn {
  return {
    id: c.id,
    date: c.date,
    sessionLabel: c.sessionLabel,
    baseSession: c.baseSession,
    pax: c.pax ?? null,
    timeFrom: c.timeFrom ?? extras.mealSchedules?.[c.baseSession]?.timeFrom ?? null,
    timeTo: c.timeTo ?? extras.mealSchedules?.[c.baseSession]?.timeTo ?? null,
    amount: c.amount ?? null,
  };
}

/** Build Excel-style columns from saved metadata or infer from existing dishes. */
export function resolveMenuColumns(
  extras: OrderExtras,
  order: Enquiry,
  dishes: EnquiryDish[],
): MenuColumn[] {
  const items = menuItemsOnly(dishes);
  const saved = extras.menuColumns ?? [];
  if (saved.length > 0) {
    return sortMenuColumns(saved.map((c) => mapColumn(c, extras)));
  }

  const fallbackDate = defaultDate(extras, order);
  const seen = new Set<string>();
  const inferred: MenuColumn[] = [];

  for (const dish of items) {
    const key = `${fallbackDate}|${dish.category}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const schedule = extras.mealSchedules?.[dish.category];
    inferred.push({
      id: `legacy_${key.replace(/\|/g, '_')}`,
      date: fallbackDate,
      sessionLabel: dish.category,
      baseSession: dish.category,
      pax: null,
      timeFrom: schedule?.timeFrom ?? null,
      timeTo: schedule?.timeTo ?? null,
      amount: null,
    });
  }

  return sortMenuColumns(inferred);
}

/** Each dish appears on at most one session column (saved map + first-match fallback). */
export function buildEffectiveDishColumnMap(
  columns: MenuColumn[],
  items: EnquiryDish[],
  extras: OrderExtras,
): Record<string, string> {
  const sorted = sortMenuColumns(columns);
  const map: Record<string, string> = { ...(extras.dishColumns ?? {}) };

  for (const dish of items) {
    if (map[dish.id]) continue;
    const match = sorted.find(
      (c) =>
        c.baseSession === dish.category ||
        c.sessionLabel === dish.category ||
        c.sessionLabel === dish.dishName,
    );
    if (match) map[dish.id] = match.id;
  }

  return map;
}

export function dishesForColumn(
  column: MenuColumn,
  items: EnquiryDish[],
  extras: OrderExtras,
  allColumns?: MenuColumn[],
): EnquiryDish[] {
  const columns = allColumns?.length
    ? allColumns
    : (extras.menuColumns ?? []).map((c) => mapColumn(c, extras));

  if (columns.length === 0) {
    return items.filter(
      (d) => d.category === column.baseSession || d.category === column.sessionLabel,
    );
  }

  const map = buildEffectiveDishColumnMap(columns, items, extras);
  if (Object.keys(map).length === 0) {
    return items.filter(
      (d) => d.category === column.baseSession || d.category === column.sessionLabel,
    );
  }

  return items.filter((d) => map[d.id] === column.id);
}

export function findOrCreateColumn(
  columns: MenuColumn[],
  draft: {
    date: string;
    baseSession: string;
    sessionLabel: string;
    pax: number | null;
    timeFrom: string;
    timeTo: string;
  },
): { columns: MenuColumn[]; columnId: string } {
  const label = draft.sessionLabel.trim() || draft.baseSession;
  const existing = columns.find(
    (c) =>
      c.date === draft.date &&
      c.baseSession === draft.baseSession &&
      c.sessionLabel === label,
  );
  if (existing) {
    const updated = columns.map((c) =>
      c.id === existing.id
        ? {
            ...c,
            pax: draft.pax ?? c.pax,
            timeFrom: draft.timeFrom || c.timeFrom,
            timeTo: draft.timeTo || c.timeTo,
          }
        : c,
    );
    return { columns: updated, columnId: existing.id };
  }

  const col: MenuColumn = {
    id: newColumnId(),
    date: draft.date,
    sessionLabel: label,
    baseSession: draft.baseSession,
    pax: draft.pax,
    timeFrom: draft.timeFrom || null,
    timeTo: draft.timeTo || null,
    amount: null,
  };
  return { columns: [...columns, col], columnId: col.id };
}

export function assignDishColumn(
  extras: OrderExtras,
  dishItemId: string,
  columnId: string,
): OrderExtras {
  return {
    ...extras,
    dishColumns: { ...(extras.dishColumns ?? {}), [dishItemId]: columnId },
  };
}

export function updateColumnAmount(
  extras: OrderExtras,
  columns: MenuColumn[],
  columnId: string,
  amount: number | null,
): OrderExtras {
  const updated = columns.map((c) => (c.id === columnId ? { ...c, amount } : c));
  return {
    ...extras,
    menuColumns: stripMenuColumnsForSave(updated),
  };
}

export function updateColumnPax(
  extras: OrderExtras,
  columns: MenuColumn[],
  columnId: string,
  pax: number | null,
): OrderExtras {
  const updated = columns.map((c) => (c.id === columnId ? { ...c, pax } : c));
  return {
    ...extras,
    menuColumns: stripMenuColumnsForSave(updated),
  };
}

export function updateColumnTime(
  extras: OrderExtras,
  columns: MenuColumn[],
  columnId: string,
  timeFrom: string | null,
  timeTo: string | null,
): OrderExtras {
  const updated = columns.map((c) =>
    c.id === columnId ? { ...c, timeFrom: timeFrom || null, timeTo: timeTo || null } : c,
  );
  return {
    ...extras,
    menuColumns: stripMenuColumnsForSave(updated),
  };
}

export function removeMenuColumn(
  extras: OrderExtras,
  columns: MenuColumn[],
  columnId: string,
): OrderExtras {
  const updatedColumns = columns.filter((c) => c.id !== columnId);
  const dishColumns = { ...(extras.dishColumns ?? {}) };
  for (const [dishId, colId] of Object.entries(dishColumns)) {
    if (colId === columnId) delete dishColumns[dishId];
  }

  return {
    ...extras,
    menuColumns: stripMenuColumnsForSave(updatedColumns),
    dishColumns: Object.keys(dishColumns).length > 0 ? dishColumns : {},
  };
}

export function findColumnForSession(
  columns: MenuColumn[],
  date: string,
  baseSession: string,
  sessionLabel?: string,
): MenuColumn | undefined {
  const label = (sessionLabel?.trim() || sessionLabelOptions(baseSession));
  return columns.find(
    (c) => c.date === date && c.baseSession === baseSession && c.sessionLabel === label,
  );
}

export function sessionLabelOptions(baseSession: string): string {
  const match = MEAL_SESSIONS.find((s) => s.id === baseSession);
  return match?.label ?? baseSession;
}

export function stripMenuColumnsForSave(columns: MenuColumn[]): MenuColumn[] {
  return columns.map(
    ({ id, date, sessionLabel, baseSession, pax, timeFrom, timeTo, amount }) => ({
      id,
      date,
      sessionLabel,
      baseSession,
      pax,
      timeFrom,
      timeTo,
      amount: amount ?? null,
    }),
  );
}

export function formatColumnAmount(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return '';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

export function sumOrderCopyTotals(columns: MenuColumn[]): number | null {
  const amounts = columns
    .map((c) => c.amount)
    .filter((a): a is number => a != null && !Number.isNaN(a));
  if (amounts.length === 0) return null;
  return amounts.reduce((sum, amount) => sum + amount, 0);
}

/** Sum session amounts only for columns that have dishes (matches order copy / billing view). */
export function sumBillableSessionTotals(
  columns: MenuColumn[],
  menuItems: EnquiryDish[],
  extras: OrderExtras,
): number | null {
  const seen = new Set<string>();
  let total = 0;
  let found = false;

  for (const col of columns) {
    const items = dishesForColumn(col, menuItems, extras, columns);
    if (items.length === 0 || col.amount == null || Number.isNaN(col.amount)) continue;
    const dishKey = items.map((d) => d.id).sort().join(',');
    const signature = `${dishKey}|${Math.round(col.amount)}`;
    if (seen.has(signature)) continue;
    seen.add(signature);
    total += col.amount;
    found = true;
  }

  return found ? total : null;
}
