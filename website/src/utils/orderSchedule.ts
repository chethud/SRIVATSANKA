import type { Enquiry } from '../api/client';

export type OrderScheduleKind = 'completed' | 'today' | 'urgent' | 'upcoming' | 'none';

export interface OrderScheduleInfo {
  kind: OrderScheduleKind;
  label: string;
  daysUntil: number;
}

function startOfDay(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

/** Calendar days from today until the event date (negative = past). */
export function daysUntilEvent(eventDate: string): number {
  const today = startOfDay(new Date());
  const event = startOfDay(new Date(eventDate));
  return Math.round((event.getTime() - today.getTime()) / (24 * 60 * 60 * 1000));
}

export function isOrderCompleted(eventDate: string): boolean {
  return daysUntilEvent(eventDate) < 0;
}

export function getOrderScheduleInfo(eventDate: string): OrderScheduleInfo {
  const daysUntil = daysUntilEvent(eventDate);

  if (daysUntil < 0) {
    return { kind: 'completed', label: 'Completed', daysUntil };
  }
  if (daysUntil === 0) {
    return { kind: 'today', label: 'Today', daysUntil };
  }
  if (daysUntil === 1) {
    return { kind: 'urgent', label: 'Upcoming in 1 day', daysUntil };
  }
  if (daysUntil === 2) {
    return { kind: 'urgent', label: 'Upcoming in 2 days', daysUntil };
  }
  if (daysUntil <= 7) {
    return { kind: 'upcoming', label: `Upcoming in ${daysUntil} days`, daysUntil };
  }
  return { kind: 'none', label: '', daysUntil };
}

export function sortOrdersBySchedule(orders: Enquiry[]): Enquiry[] {
  return [...orders].sort((a, b) => {
    const aDone = isOrderCompleted(a.eventDate);
    const bDone = isOrderCompleted(b.eventDate);
    if (aDone !== bDone) return aDone ? 1 : -1;

    const aDays = daysUntilEvent(a.eventDate);
    const bDays = daysUntilEvent(b.eventDate);
    if (!aDone) return aDays - bDays;
    return bDays - aDays;
  });
}
