import { formatCurrency, formatDateTime, type Enquiry } from '../../api/client';
import { paymentModeLabel } from '../../utils/paymentRecord';
import {
  orderAmountDue,
  orderAmountPaid,
  orderBillingTotal,
  orderDiscount,
  isPartialPaymentOrder,
} from '../../utils/orderBilling';

export function OrderPaymentSection({
  order,
  onRecordPayment,
  onMarkNotReceived,
  markNotReceivedBusy = false,
}: {
  order: Enquiry;
  onRecordPayment?: () => void;
  onMarkNotReceived?: () => void;
  markNotReceivedBusy?: boolean;
}) {
  const billing = orderBillingTotal(order);
  const discount = orderDiscount(order);
  const paid = orderAmountPaid(order);
  const due = orderAmountDue(order);
  const payments = order.payments ?? [];
  const partial = isPartialPaymentOrder(order);

  return (
    <div className="order-section">
      <div className="order-section-head">
        <div className="order-section-title">Payments</div>
        <div className="flex flex-wrap gap-2">
          {onMarkNotReceived && (
            <button
              type="button"
              disabled={markNotReceivedBusy}
              onClick={onMarkNotReceived}
              className="order-hero__btn order-hero__btn--secondary !text-xs !py-1.5 !px-3"
            >
              {markNotReceivedBusy ? 'Saving…' : 'Mark payment not received'}
            </button>
          )}
          {onRecordPayment && !order.paymentReceived && order.deliveredAt && (
            <button type="button" onClick={onRecordPayment} className="order-hero__btn order-hero__btn--primary !text-xs !py-1.5 !px-3">
              Record payment
            </button>
          )}
        </div>
      </div>
      <p className="order-section-sub">
        <strong>Booked total</strong> is the order value (menu + extras, minus discount).{' '}
        <strong>Received</strong> is cash logged — partial payments count only what you record until the balance is cleared.
      </p>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-sm">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-alt)] p-3">
          <dt className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Booked total</dt>
          <dd className="font-bold tabular-nums mt-1">{formatCurrency(billing)}</dd>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-alt)] p-3">
          <dt className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Discount</dt>
          <dd className="font-bold tabular-nums mt-1">{formatCurrency(discount)}</dd>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-alt)] p-3">
          <dt className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Received</dt>
          <dd className="font-bold tabular-nums mt-1 text-[var(--primary)]">{formatCurrency(paid)}</dd>
        </div>
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-alt)] p-3">
          <dt className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Balance due</dt>
          <dd className={`font-bold tabular-nums mt-1 ${due > 0 ? 'text-amber-800' : ''}`}>
            {formatCurrency(due)}
          </dd>
        </div>
      </dl>

      {partial && (
        <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
          Partial payment — {formatCurrency(due)} still due. Use Record payment or the Dashboard → Partial payments tab.
        </p>
      )}

      {payments.length === 0 ? (
        <p className="text-sm text-[var(--muted)]">No payments recorded yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
          <table className="w-full text-sm">
            <thead className="bg-[var(--table-header-bg)] text-left text-xs uppercase tracking-wide text-[var(--muted)]">
              <tr>
                <th className="p-3 font-semibold">Date</th>
                <th className="p-3 font-semibold">Mode</th>
                <th className="p-3 font-semibold">Account</th>
                <th className="p-3 font-semibold">Paid by</th>
                <th className="p-3 font-semibold text-right">Amount</th>
                <th className="p-3 font-semibold">Notes</th>
              </tr>
            </thead>
            <tbody>
              {payments.map((p) => (
                <tr key={p.id} className="border-t border-[var(--border)]">
                  <td className="p-3 tabular-nums whitespace-nowrap">{formatDateTime(p.paidAt)}</td>
                  <td className="p-3">{paymentModeLabel(p.paymentMode)}</td>
                  <td className="p-3 break-words">{p.receivedAccount || '—'}</td>
                  <td className="p-3">{p.payerName || '—'}</td>
                  <td className="p-3 text-right font-semibold tabular-nums">{formatCurrency(p.amount)}</td>
                  <td className="p-3 text-[var(--muted)]">{p.notes || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
