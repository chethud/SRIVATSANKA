import { DEFAULT_MEAL_TIMES, MEAL_SESSION_ORDER, PREFERENCE_CATEGORIES } from './mealSessions';

export type DispatchItemStatus = 'pending' | 'packed' | 'dispatched' | 'served';
export type DispatchPhase = 'planned' | 'preparing' | 'out_for_delivery' | 'completed';

export type MealSessionSchedule = {
  timeFrom: string | null;
  timeTo: string | null;
};

export type OrderExtraItem = {
  id: string;
  title: string;
  description: string;
  quantity: string;
  /** Client selected this extra — checkbox on order page */
  enabled?: boolean;
  /** User-added row (not from preset list) */
  isCustom?: boolean;
};

/** Preset extras from wedding Excel sheets — each has its own checkbox on the order. */
export const DEFAULT_ORDER_EXTRA_PRESETS = [
  'Tat Paniyaram',
  'Vratha Paniyaram Box',
  'Kobri Design',
  'Gopura',
  'Theratti Paal',
  'Sweet Box',
  'Thambula',
  'Banana for Varapooje',
  'Thambula for Gents',
] as const;

function extraItemEnabled(row: OrderExtraItem): boolean {
  if (row.enabled === true) return true;
  if (row.enabled === false) return false;
  return Boolean(row.description.trim() || row.quantity.trim());
}

export function mergeOrderExtraItems(saved: OrderExtraItem[] | undefined): OrderExtraItem[] {
  const savedRows = saved ?? [];
  const byTitle = new Map(savedRows.map((row) => [row.title.trim().toLowerCase(), row]));
  const presetTitles = new Set(DEFAULT_ORDER_EXTRA_PRESETS.map((t) => t.toLowerCase()));

  const presets = DEFAULT_ORDER_EXTRA_PRESETS.map((title, index) => {
    const existing = byTitle.get(title.toLowerCase());
    if (existing) {
      return {
        ...existing,
        title,
        enabled: extraItemEnabled(existing),
        isCustom: false,
      };
    }
    return {
      id: `preset_${index}`,
      title,
      description: '',
      quantity: '',
      enabled: false,
      isCustom: false,
    };
  });

  const custom = savedRows
    .filter((row) => !presetTitles.has(row.title.trim().toLowerCase()))
    .map((row) => ({
      ...row,
      enabled: extraItemEnabled(row),
      isCustom: true,
    }));

  return [...presets, ...custom];
}

export function activeOrderExtraItems(items: OrderExtraItem[] | undefined): OrderExtraItem[] {
  return mergeOrderExtraItems(items).filter((row) => row.enabled && row.title.trim());
}

export type MenuColumn = {
  id: string;
  date: string;
  sessionLabel: string;
  baseSession: string;
  pax: number | null;
  timeFrom: string | null;
  timeTo: string | null;
  /** Total amount for this session column (not per dish). */
  amount: number | null;
};

export type OrderExtras = {
  dietary: string[];
  liveCounters: string[];
  addOns: string[];
  scheduleDateFrom?: string | null;
  scheduleDateTo?: string | null;
  /** @deprecated use mealSchedules */
  scheduleTimeFrom?: string | null;
  /** @deprecated use mealSchedules */
  scheduleTimeTo?: string | null;
  mealSchedules?: Record<string, MealSessionSchedule>;
  /** Excel-style columns: date + session label + pax/time per column */
  menuColumns?: MenuColumn[];
  /** Maps enquiry dish line id → menu column id */
  dishColumns?: Record<string, string>;
  /** Optional wedding extras (paniyaram, thambula, sweet box, etc.) */
  extrasEnabled?: boolean;
  extraItems?: OrderExtraItem[];
  /** Regional cuisine style — printed on kitchen and billing copies */
  regionalStyle?: string | null;
  /** @deprecated use assignedWorkerIds */
  primaryWorkerId?: string | null;
  assignedWorkerIds?: string[];
  dispatchPhase?: DispatchPhase;
  itemDispatch?: Record<string, DispatchItemStatus>;
};

export function resolveAssignedWorkerIds(extras: OrderExtras): string[] {
  const ids = Array.isArray(extras.assignedWorkerIds)
    ? extras.assignedWorkerIds.filter(Boolean)
    : [];
  if (ids.length === 0 && extras.primaryWorkerId) {
    return [extras.primaryWorkerId];
  }
  return ids;
}

const EMPTY: OrderExtras = {
  dietary: [],
  liveCounters: [],
  addOns: [],
  scheduleDateFrom: null,
  scheduleDateTo: null,
  scheduleTimeFrom: null,
  scheduleTimeTo: null,
  mealSchedules: {},
  primaryWorkerId: null,
  assignedWorkerIds: [],
  dispatchPhase: 'planned',
  itemDispatch: {},
};

function hasStructuredNotes(parsed: Partial<OrderExtras>): boolean {
  return (
    'dietary' in parsed ||
    'liveCounters' in parsed ||
    'addOns' in parsed ||
    'scheduleDateFrom' in parsed ||
    'scheduleDateTo' in parsed ||
    'scheduleTimeFrom' in parsed ||
    'scheduleTimeTo' in parsed ||
    'mealSchedules' in parsed ||
    'menuColumns' in parsed ||
    'dishColumns' in parsed ||
    'extrasEnabled' in parsed ||
    'extraItems' in parsed ||
    'regionalStyle' in parsed ||
    'primaryWorkerId' in parsed ||
    'assignedWorkerIds' in parsed ||
    'dispatchPhase' in parsed ||
    'itemDispatch' in parsed
  );
}

export function parseOrderNotes(notes: string | null | undefined): OrderExtras {
  if (!notes?.trim()) return { ...EMPTY };
  try {
    const parsed = JSON.parse(notes) as Partial<OrderExtras>;
    if (parsed && typeof parsed === 'object' && hasStructuredNotes(parsed)) {
      return {
        dietary: Array.isArray(parsed.dietary) ? parsed.dietary.filter(Boolean) : [],
        liveCounters: Array.isArray(parsed.liveCounters) ? parsed.liveCounters.filter(Boolean) : [],
        addOns: Array.isArray(parsed.addOns) ? parsed.addOns.filter(Boolean) : [],
        scheduleDateFrom: parsed.scheduleDateFrom ?? null,
        scheduleDateTo: parsed.scheduleDateTo ?? null,
        scheduleTimeFrom: parsed.scheduleTimeFrom ?? null,
        scheduleTimeTo: parsed.scheduleTimeTo ?? null,
        mealSchedules: parsed.mealSchedules ?? {},
        menuColumns: parsed.menuColumns ?? [],
        dishColumns: parsed.dishColumns ?? {},
        extrasEnabled: parsed.extrasEnabled ?? false,
        extraItems: Array.isArray(parsed.extraItems) ? parsed.extraItems : [],
        regionalStyle: parsed.regionalStyle ?? null,
        primaryWorkerId: parsed.primaryWorkerId ?? null,
        assignedWorkerIds: Array.isArray(parsed.assignedWorkerIds)
          ? parsed.assignedWorkerIds.filter(Boolean)
          : parsed.primaryWorkerId
            ? [parsed.primaryWorkerId]
            : [],
        dispatchPhase: parsed.dispatchPhase ?? 'planned',
        itemDispatch: parsed.itemDispatch ?? {},
      };
    }
  } catch {
    /* plain text fallback */
  }
  return {
    dietary: notes.split('\n').map((l) => l.trim()).filter(Boolean),
    liveCounters: [],
    addOns: [],
  };
}

export function serializeOrderNotes(extras: OrderExtras): string {
  return JSON.stringify(extras);
}

export function formatOrderId(id: string): string {
  const tail = id.replace(/\W/g, '').slice(-6).toUpperCase();
  return `ORD-${tail || '000'}`;
}

export function toDateInputValue(isoOrDate: string | null | undefined): string {
  if (!isoOrDate) return '';
  return isoOrDate.slice(0, 10);
}

export function formatScheduleTime(value: string | null | undefined): string {
  if (!value) return '';
  const [h, m] = value.split(':');
  const hour = Number(h);
  if (Number.isNaN(hour)) return value;
  const suffix = hour >= 12 ? 'PM' : 'AM';
  const h12 = hour % 12 || 12;
  return `${h12}:${m ?? '00'} ${suffix}`;
}

export function formatMealTimeRange(schedule: MealSessionSchedule | null | undefined): string {
  if (!schedule?.timeFrom || !schedule?.timeTo) return '';
  return `${formatScheduleTime(schedule.timeFrom)} – ${formatScheduleTime(schedule.timeTo)}`;
}

export function resolveMealSchedules(extras: OrderExtras): Record<string, MealSessionSchedule> {
  const merged: Record<string, MealSessionSchedule> = {};
  for (const [session, defaults] of Object.entries(DEFAULT_MEAL_TIMES)) {
    merged[session] = {
      timeFrom: defaults.timeFrom,
      timeTo: defaults.timeTo,
    };
  }
  if (extras.mealSchedules) {
    for (const [session, slot] of Object.entries(extras.mealSchedules)) {
      merged[session] = {
        timeFrom: slot.timeFrom ?? merged[session]?.timeFrom ?? null,
        timeTo: slot.timeTo ?? merged[session]?.timeTo ?? null,
      };
    }
  }
  if (extras.scheduleTimeFrom && extras.scheduleTimeTo && !extras.mealSchedules?.Breakfast) {
    merged.Breakfast = {
      timeFrom: extras.scheduleTimeFrom,
      timeTo: extras.scheduleTimeTo,
    };
  }
  return merged;
}

export function mealSchedulesForSave(
  sessions: Record<string, { timeFrom: string; timeTo: string }>,
): Record<string, MealSessionSchedule> {
  const out: Record<string, MealSessionSchedule> = {};
  for (const [session, slot] of Object.entries(sessions)) {
    if (slot.timeFrom || slot.timeTo) {
      out[session] = { timeFrom: slot.timeFrom || null, timeTo: slot.timeTo || null };
    }
  }
  return out;
}

export function groupMenuItems(dishes: { category: string }[]): string[] {
  const cats = [...new Set(dishes.map((d) => d.category))].filter(
    (c) => !PREFERENCE_CATEGORIES.has(c),
  );
  return cats.sort((a, b) => {
    const ia = MEAL_SESSION_ORDER.indexOf(a);
    const ib = MEAL_SESSION_ORDER.indexOf(b);
    if (ia === -1 && ib === -1) return a.localeCompare(b);
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });
}

export function statusLabel(status: string): string {
  switch (status) {
    case 'CONVERTED':
      return 'Confirmed';
    case 'CONTACTED':
      return 'In progress';
    case 'CLOSED':
      return 'Closed';
    default:
      return 'New';
  }
}
