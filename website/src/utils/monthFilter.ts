export const MONTH_FILTERS = [
  { id: 'ALL', label: 'All months' },
  { id: 'THIS_MONTH', label: 'This month' },
  { id: 'LAST_MONTH', label: 'Last month' },
  { id: 'LAST_3_MONTHS', label: 'Last 3 months' },
];

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function endOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0, 23, 59, 59, 999);
}

export function matchesMonthFilter(createdAt: string, filter: string): boolean {
  if (filter === 'ALL') return true;

  const created = new Date(createdAt);
  const now = new Date();

  if (filter === 'THIS_MONTH') {
    return created >= startOfMonth(now) && created <= endOfMonth(now);
  }

  if (filter === 'LAST_MONTH') {
    const last = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    return created >= startOfMonth(last) && created <= endOfMonth(last);
  }

  if (filter === 'LAST_3_MONTHS') {
    const from = new Date(now.getFullYear(), now.getMonth() - 2, 1);
    return created >= startOfMonth(from);
  }

  return true;
}
