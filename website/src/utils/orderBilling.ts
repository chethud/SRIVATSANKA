import type { Enquiry } from '../api/client';
import { PREFERENCE_CATEGORIES } from './mealSessions';
import {
  overallTotalFromExtras,
  parseOrderNotes,
  sumBillableExtraItemAmounts,
} from './orderNotes';
import { resolveMenuColumns, sumBillableSessionTotals } from './orderMenuGrid';

/** Session totals + extras exactly as shown on order / our copy (unscaled). */
export function orderCopyBillingBase(order: Enquiry): number {
  const extras = parseOrderNotes(order.notes);
  const overall = overallTotalFromExtras(extras);
  if (overall != null) return overall;

  const menuItems = (order.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, order, menuItems);
  const sessions = sumBillableSessionTotals(columns, menuItems, extras) ?? 0;
  const extrasSum = extras.extrasEnabled ? (sumBillableExtraItemAmounts(extras.extraItems) ?? 0) : 0;
  return sessions + extrasSum;
}

export function orderCopyBillingBreakdown(order: Enquiry): {
  sessions: number;
  extras: number;
  contractTotal: number | null;
} {
  const extras = parseOrderNotes(order.notes);
  const contractTotal = overallTotalFromExtras(extras);
  const menuItems = (order.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, order, menuItems);
  const sessions = sumBillableSessionTotals(columns, menuItems, extras) ?? 0;
  const extrasSum = extras.extrasEnabled ? (sumBillableExtraItemAmounts(extras.extraItems) ?? 0) : 0;
  return { sessions, extras: extrasSum, contractTotal };
}

/** Order-copy billing total (session amounts + extras), matching Excel/billing view. */
export function orderBillingTotal(order: Enquiry): number {
  const fromNotes = orderCopyBillingBase(order);
  if (fromNotes > 0) return fromNotes;

  if (typeof order.billingTotal === 'number' && order.billingTotal > 0) {
    return order.billingTotal;
  }

  const perGuest = (order.dishes ?? []).reduce(
    (s, d) => s + (d.unitPrice ?? 0) * Math.max(1, d.quantity || 1),
    0,
  );
  return perGuest * Math.max(1, order.guestCount || 1);
}

export function orderAmountPaid(order: Enquiry): number {
  if (typeof order.amountPaid === 'number') return order.amountPaid;
  return (order.payments ?? []).reduce((s, p) => s + (p.amount || 0), 0);
}

export function orderDiscount(order: Enquiry): number {
  return Math.max(0, order.discountAmount ?? 0);
}

export function orderAmountDue(order: Enquiry): number {
  if (typeof order.amountDue === 'number') return Math.max(0, order.amountDue);
  return Math.max(0, orderBillingTotal(order) - orderDiscount(order) - orderAmountPaid(order));
}

export function isPartialPaymentOrder(order: Enquiry): boolean {
  if (order.status !== 'CONVERTED') return false;
  if (order.paymentReceived) return false;
  const paid = orderAmountPaid(order);
  const due = orderAmountDue(order);
  return paid > 0 && due > 0.009;
}
