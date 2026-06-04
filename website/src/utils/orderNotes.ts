export type DispatchItemStatus = 'pending' | 'packed' | 'dispatched' | 'served';
export type DispatchPhase = 'planned' | 'preparing' | 'out_for_delivery' | 'completed';

export type OrderExtras = {
  dietary: string[];
  liveCounters: string[];
  addOns: string[];
  primaryWorkerId?: string | null;
  dispatchPhase?: DispatchPhase;
  itemDispatch?: Record<string, DispatchItemStatus>;
};

const EMPTY: OrderExtras = {
  dietary: [],
  liveCounters: [],
  addOns: [],
  primaryWorkerId: null,
  dispatchPhase: 'planned',
  itemDispatch: {},
};

export function parseOrderNotes(notes: string | null | undefined): OrderExtras {
  if (!notes?.trim()) return { ...EMPTY };
  try {
    const parsed = JSON.parse(notes) as Partial<OrderExtras>;
    if (parsed && typeof parsed === 'object' && ('dietary' in parsed || 'liveCounters' in parsed)) {
      return {
        dietary: Array.isArray(parsed.dietary) ? parsed.dietary.filter(Boolean) : [],
        liveCounters: Array.isArray(parsed.liveCounters) ? parsed.liveCounters.filter(Boolean) : [],
        addOns: Array.isArray(parsed.addOns) ? parsed.addOns.filter(Boolean) : [],
        primaryWorkerId: parsed.primaryWorkerId ?? null,
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

const CATEGORY_ORDER = [
  'Snacks',
  'Snacks & Starters',
  'South Indian',
  'North Indian',
  'Chinese',
  'Multi Cuisine',
  'Desserts',
  'Beverages',
  'Cuisine Preference',
];

export function groupMenuItems(dishes: { category: string }[]): string[] {
  const cats = [...new Set(dishes.map((d) => d.category))];
  return cats.sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a);
    const ib = CATEGORY_ORDER.indexOf(b);
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
