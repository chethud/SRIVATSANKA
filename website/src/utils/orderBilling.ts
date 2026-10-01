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

  const override = extras.bookedTotalOverride;
  if (typeof override === 'number' && override > 0) return override;

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
  const rows = order.payments ?? [];
  const fromRows = rows.reduce((s, p) => s + (Number(p.amount) || 0), 0);
  if (rows.length > 0) return fromRows;
  if (typeof order.amountPaid === 'number' && order.amountPaid > 0) return order.amountPaid;
  return 0;
}

export function orderDiscount(order: Enquiry): number {
  return Math.max(0, order.discountAmount ?? 0);
}

/** Balance due — always from order-copy billing math (not stale API amountDue). */
export function orderAmountDue(order: Enquiry): number {
  const billing = orderBillingTotal(order);
  const discount = orderDiscount(order);
  const paid = orderAmountPaid(order);
  return Math.max(0, billing - discount - paid);
}

/** Some cash logged and a balance still due (ignores stale paymentReceived flag). */
export function isPartialPaymentOrder(order: Enquiry): boolean {
  if (order.status !== 'CONVERTED') return false;
  const paid = orderAmountPaid(order);
  if (paid <= 0) return false;
  return orderAmountDue(order) > 0.009;
}

/** Paid in full by ledger + order-copy billing (use for UI, not API paymentReceived alone). */
export function isOrderPaymentComplete(order: Enquiry): boolean {
  if (order.status !== 'CONVERTED') return false;
  return orderAmountPaid(order) > 0 && orderAmountDue(order) <= 0.009;
}
