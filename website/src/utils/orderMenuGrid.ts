import type { Enquiry, EnquiryDish } from '../api/client';
import { formatScheduleTime, type MenuColumn, type OrderExtras } from './orderNotes';
import { MEAL_SESSIONS, PREFERENCE_CATEGORIES } from './mealSessions';

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

function defaultDate(extras: OrderExtras, order: Enquiry): string {
  return extras.scheduleDateFrom ?? order.eventDate.slice(0, 10);
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
    return saved.map((c) => mapColumn(c, extras));
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
      pax: order.guestCount || null,
      timeFrom: schedule?.timeFrom ?? null,
      timeTo: schedule?.timeTo ?? null,
      amount: null,
    });
  }

  return inferred;
}

export function dishesForColumn(
  column: MenuColumn,
  items: EnquiryDish[],
  extras: OrderExtras,
): EnquiryDish[] {
  const map = extras.dishColumns ?? {};
  const hasAssignments = Object.keys(map).length > 0;

  if (hasAssignments) {
    return items.filter((d) => map[d.id] === column.id);
  }

  return items.filter(
    (d) => d.category === column.baseSession || d.category === column.sessionLabel,
  );
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
