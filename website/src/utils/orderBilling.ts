import type { Enquiry } from '../api/client';
import { parseOrderNotes, sumExtraItemAmounts } from './orderNotes';
import { resolveMenuColumns, sumOrderCopyTotals } from './orderMenuGrid';

/** Order-copy billing total (session amounts + extras), matching Excel/billing view. */
export function orderBillingTotal(order: Enquiry): number {
  if (typeof order.billingTotal === 'number' && order.billingTotal > 0) {
    return order.billingTotal;
  }
  const extras = parseOrderNotes(order.notes);
  const columns = resolveMenuColumns(extras, order, order.dishes ?? []);
  const sessions = sumOrderCopyTotals(columns) ?? 0;
  const extrasSum = sumExtraItemAmounts(extras.extraItems) ?? 0;
  const fromNotes = sessions + extrasSum;
  if (fromNotes > 0) return fromNotes;

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
