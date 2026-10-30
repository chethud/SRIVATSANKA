import { useState } from 'react';
import { formatCurrency, formatDateTime, updateEnquiry, type Enquiry } from '../../api/client';
import { paymentModeLabel } from '../../utils/paymentRecord';
import {
  orderAmountDue,
  orderAmountPaid,
  orderBillingTotal,
  orderCopyBillingBase,
  isOrderPaymentComplete,
  isPartialPaymentOrder,
} from '../../utils/orderBilling';
import { parseOrderNotes, serializeOrderNotes } from '../../utils/orderNotes';

export function OrderPaymentSection({
  order,
  onOrderUpdated,
  onRecordPayment,
  onAdvancePayment,
  onMarkNotReceived,
  markNotReceivedBusy = false,
}: {
  order: Enquiry;
  onOrderUpdated?: (order: Enquiry) => void;
  onRecordPayment?: () => void;
  onAdvancePayment?: () => void;
  onMarkNotReceived?: () => void;
  markNotReceivedBusy?: boolean;
}) {
  const billing = orderBillingTotal(order);
  const paid = orderAmountPaid(order);
  const due = orderAmountDue(order);
  const payments = order.payments ?? [];
  const partial = isPartialPaymentOrder(order);
  const extras = parseOrderNotes(order.notes);
  const menuBooked = orderCopyBillingBase({
    ...order,
    notes: serializeOrderNotes({ ...extras, bookedTotalOverride: null }),
  });

  const [editing, setEditing] = useState(false);
  const [saveBusy, setSaveBusy] = useState(false);
  const [editError, setEditError] = useState('');
  const [draftBooked, setDraftBooked] = useState('');
  const [useBookedOverride, setUseBookedOverride] = useState(false);

  function openEdit() {
    setEditError('');
    const override = extras.bookedTotalOverride;
    if (typeof override === 'number' && override > 0) {
      setUseBookedOverride(true);
      setDraftBooked(String(override));
    } else {
      setUseBookedOverride(false);
      setDraftBooked(menuBooked > 0 ? String(menuBooked) : '');
    }
    setEditing(true);
  }

  async function saveEdit() {
    if (!onOrderUpdated) return;
    setSaveBusy(true);
    setEditError('');
    try {
      let nextExtras = extras;
      if (useBookedOverride) {
        const booked = Math.max(0, Number(draftBooked) || 0);
        if (booked <= 0) {
          setEditError('Enter a booked total greater than zero, or turn off manual booked total.');
          return;
        }
        nextExtras = { ...extras, bookedTotalOverride: booked };
      } else {
        nextExtras = { ...extras, bookedTotalOverride: null };
      }

      const notesChanged =
        nextExtras.bookedTotalOverride !== extras.bookedTotalOverride ||
        (nextExtras.bookedTotalOverride == null && extras.bookedTotalOverride != null);

      let latest = order;
      if (notesChanged) {
        latest = await updateEnquiry(order.id, { notes: serializeOrderNotes(nextExtras) });
      }

      onOrderUpdated(latest);
      setEditing(false);
    } catch (err) {
      setEditError(err instanceof Error ? err.message : 'Could not save payment details');
    } finally {
      setSaveBusy(false);
    }
  }

  const canEdit = order.status === 'CONVERTED' && Boolean(onOrderUpdated);
  const canAdvance =
    Boolean(onAdvancePayment) &&
    !isOrderPaymentComplete(order) &&
    order.status === 'CONVERTED' &&
    !order.deliveredAt;
  const canRecord =
    Boolean(onRecordPayment) &&
    !isOrderPaymentComplete(order) &&
    order.status === 'CONVERTED' &&
    Boolean(order.deliveredAt);

  return (
    <div className="order-section">
      <div className="order-section-head">
        <div className="order-section-title">Payments</div>
        <div className="flex flex-wrap gap-2">
          {canEdit && !editing && (
            <button
              type="button"
              onClick={openEdit}
              className="order-hero__btn order-hero__btn--secondary !text-xs !py-1.5 !px-3"
            >
              Edit payment details
            </button>
          )}
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
          {canAdvance && (
            <button
              type="button"
              onClick={onAdvancePayment}
              className="order-hero__btn order-hero__btn--secondary !text-xs !py-1.5 !px-3"
            >
              Advance payment
            </button>
          )}
          {canRecord && (
            <button type="button" onClick={onRecordPayment} className="order-hero__btn order-hero__btn--primary !text-xs !py-1.5 !px-3">
              Record payment
            </button>
          )}
        </div>
      </div>
      <p className="order-section-sub">
        <strong>Booked total</strong> matches the order copy overall total (session totals + extras).{' '}
        <strong>Balance due</strong> is booked total minus received (including advances). Use{' '}
        <strong>Advance payment</strong> before delivery; after delivery use <strong>Record payment</strong> for the rest.
      </p>

      {editing && (
        <div className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--background-alt)] p-4 space-y-3">
          <p className="text-sm font-semibold">Edit payment details</p>
          {menuBooked > 0 && !useBookedOverride && (
            <p className="text-xs text-[var(--muted)]">
              From menu: {formatCurrency(menuBooked)} — enable manual booked total only if you need to override.
            </p>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={useBookedOverride}
              onChange={(e) => setUseBookedOverride(e.target.checked)}
            />
            Set booked total manually
          </label>
          {useBookedOverride && (
            <div>
              <label className="text-xs text-[var(--muted)] block mb-1">Booked total (₹)</label>
              <input
                type="number"
                min={0}
                step={1}
                value={draftBooked}
                onChange={(e) => setDraftBooked(e.target.value)}
                className="form-input w-full max-w-xs px-3 py-2 rounded-lg"
              />
            </div>
          )}
          {editError && <p className="text-sm text-red-700">{editError}</p>}
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={saveBusy}
              onClick={() => void saveEdit()}
              className="order-hero__btn order-hero__btn--primary !text-xs !py-1.5 !px-3"
            >
              {saveBusy ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              disabled={saveBusy}
              onClick={() => setEditing(false)}
              className="order-hero__btn order-hero__btn--secondary !text-xs !py-1.5 !px-3"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      <dl className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4 text-sm">
        <div className="rounded-lg border border-[var(--border)] bg-[var(--background-alt)] p-3">
          <dt className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Booked total</dt>
          <dd className="font-bold tabular-nums mt-1">{formatCurrency(billing)}</dd>
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
              {payments.map((p) => {
                const isAdvance = /\badvance\b/i.test(p.notes || '');
                return (
                  <tr key={p.id} className="border-t border-[var(--border)]">
                    <td className="p-3 tabular-nums whitespace-nowrap">{formatDateTime(p.paidAt)}</td>
                    <td className="p-3">
                      {paymentModeLabel(p.paymentMode)}
                      {isAdvance && (
                        <span className="ml-2 text-[10px] font-bold uppercase tracking-wide text-amber-800 bg-amber-50 border border-amber-200 rounded px-1.5 py-0.5">
                          Advance
                        </span>
                      )}
                    </td>
                    <td className="p-3 break-words">{p.receivedAccount || '—'}</td>
                    <td className="p-3">{p.payerName || '—'}</td>
                    <td className="p-3 text-right font-semibold tabular-nums">{formatCurrency(p.amount)}</td>
                    <td className="p-3 text-[var(--muted)]">{p.notes || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
