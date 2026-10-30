import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Enquiry } from '../api/client';
import { confirmEnquiryPayment, formatCurrency } from '../api/client';
import {
  isOrderPaymentComplete,
  orderAmountDue,
  orderAmountPaid,
  orderBillingTotal,
} from '../utils/orderBilling';
import { Card } from './Layout';
import { PaymentRecordFields, paymentPayloadExtras, type PaymentRecordDraft } from './PaymentRecordFields';
import { defaultPaymentPaidAtLocal } from '../utils/paymentRecord';

export function PaymentReceivedModal({
  orders,
  onResolved,
  forceOrderId = null,
  onCloseForce,
  mode = 'payment',
}: {
  orders: Enquiry[];
  dishes?: unknown;
  onResolved: (updated: Enquiry) => void | Promise<void>;
  /** Open payment UI for a specific order (e.g. from order detail page). */
  forceOrderId?: string | null;
  onCloseForce?: () => void;
  /** Advance = before delivery; payment = after / settle remaining. */
  mode?: 'payment' | 'advance';
}) {
  const advanceMode = mode === 'advance';
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [splitMode, setSplitMode] = useState(false);
  const [payAmount, setPayAmount] = useState('');
  const [payerName, setPayerName] = useState('');
  const [paymentMeta, setPaymentMeta] = useState<PaymentRecordDraft>({
    paymentMode: '',
    paidAt: defaultPaymentPaidAtLocal(),
    paymentNotes: '',
    receivedAccount: '',
  });

  const pending = useMemo(
    () =>
      orders.filter(
        (o) =>
          o.status === 'CONVERTED' &&
          Boolean(o.deliveredAt) &&
          !isOrderPaymentComplete(o) &&
          orderAmountPaid(o) <= 0 &&
          !dismissed.includes(o.id),
      ),
    [orders, dismissed],
  );

  const forced = useMemo(() => {
    if (!forceOrderId) return null;
    return (
      orders.find((o) => {
        if (o.id !== forceOrderId || o.status !== 'CONVERTED' || isOrderPaymentComplete(o)) {
          return false;
        }
        if (advanceMode) {
          return !o.deliveredAt;
        }
        // Record payment: delivered orders, or any with remaining (advances already logged)
        return true;
      }) ?? null
    );
  }, [orders, forceOrderId, advanceMode]);

  const current = forced ?? (advanceMode ? null : pending[0]);
  const forcedMode = Boolean(forced);

  const billing = current ? orderBillingTotal(current) : 0;
  const paid = current ? orderAmountPaid(current) : 0;
  const remaining = current ? orderAmountDue(current) : 0;

  useEffect(() => {
    if (!current) return;
    if (advanceMode) {
      setSplitMode(true);
      setPayAmount('');
      setPaymentMeta({
        paymentMode: '',
        paidAt: defaultPaymentPaidAtLocal(),
        paymentNotes: 'Advance payment',
        receivedAccount: '',
      });
    } else {
      setPayAmount(paid > 0 ? '' : remaining > 0 ? String(Math.round(remaining * 100) / 100) : '');
      setPaymentMeta({
        paymentMode: '',
        paidAt: defaultPaymentPaidAtLocal(),
        paymentNotes: '',
        receivedAccount: '',
      });
      setSplitMode(paid > 0);
    }
    setPayerName(current.customerName || '');
    setError(null);
  }, [current?.id, forceOrderId, advanceMode]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!current) return null;
  const order = current;

  async function submit(fullPay: boolean) {
    setBusy(true);
    setError(null);
    try {
      const typed = Math.max(0, Number(payAmount) || 0);
      const amount = fullPay && !advanceMode ? remaining : typed;
      if (amount <= 0) {
        setError(
          advanceMode
            ? 'Enter the advance amount received'
            : fullPay
              ? 'Nothing left to collect on this order'
              : 'Enter the installment amount (must be less than the full balance for a partial payment)',
        );
        setBusy(false);
        return;
      }
      if (amount > remaining + 0.009) {
        setError(`Amount cannot exceed the balance due (${formatCurrency(remaining)})`);
        setBusy(false);
        return;
      }
      if (!advanceMode && !fullPay && amount >= remaining - 0.009) {
        setError('For the full balance, use Full payment instead of Split / partial');
        setBusy(false);
        return;
      }
      const noteParts = [
        advanceMode ? 'Advance payment' : null,
        paymentMeta.paymentNotes.trim() || null,
      ].filter(Boolean);
      // Avoid duplicating "Advance payment" if already in notes
      const notes =
        advanceMode && paymentMeta.paymentNotes.trim().toLowerCase().includes('advance')
          ? paymentMeta.paymentNotes.trim()
          : noteParts.join(' — ') || null;

      const updated = await confirmEnquiryPayment(order.id, {
        received: true,
        amount,
        payerName: payerName.trim() || order.customerName,
        ...paymentPayloadExtras({ ...paymentMeta, paymentNotes: notes || '' }),
        advance: advanceMode,
      });
      await onResolved(updated);
      if (forcedMode) onCloseForce?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save payment');
    } finally {
      setBusy(false);
    }
  }

  function remindLater() {
    if (forcedMode) {
      onCloseForce?.();
      return;
    }
    setDismissed((ids) => [...ids, order.id]);
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/45"
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-received-title"
    >
      <Card className="w-full max-w-md p-6 shadow-xl max-h-[90vh] overflow-y-auto">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)] mb-2">
          {advanceMode ? 'Before delivery' : 'Order payment'}
        </p>
        <h2 id="payment-received-title" className="text-xl font-semibold text-[var(--foreground)]">
          {advanceMode ? 'Record advance payment' : 'Did you receive payment?'}
        </h2>
        <p className="text-sm text-[var(--muted)] mt-2">
          <span className="font-medium text-[var(--foreground)]">{order.customerName}</span>
          {' · '}
          {order.eventType}
        </p>
        {advanceMode && (
          <p className="text-sm text-[var(--muted)] mt-2 leading-relaxed">
            Log money received before the event. It counts toward the balance and appears when you use{' '}
            <strong>Record payment</strong> later. The order stays <strong>Not yet delivered</strong>.
          </p>
        )}

        <div className="mt-4 space-y-1 text-sm">
          <div className="flex justify-between gap-3">
            <span className="text-[var(--muted)]">Order total</span>
            <span className="font-semibold tabular-nums">{formatCurrency(billing)}</span>
          </div>
          {paid > 0 && (
            <div className="flex justify-between gap-3">
              <span className="text-[var(--muted)]">
                {advanceMode ? 'Advance already paid' : 'Already paid'}
              </span>
              <span className="tabular-nums text-[var(--primary)]">{formatCurrency(paid)}</span>
            </div>
          )}
          <div className="flex justify-between gap-3">
            <span className="text-[var(--muted)]">Balance due</span>
            <span className="font-bold text-[var(--primary)] tabular-nums">{formatCurrency(remaining)}</span>
          </div>
        </div>

        {!advanceMode && (
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => {
                setSplitMode(false);
                setPayAmount(remaining > 0 ? String(Math.round(remaining * 100) / 100) : '');
              }}
              className={`flex-1 px-3 py-2 text-xs font-semibold rounded-lg border ${
                !splitMode ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'border-[var(--border)]'
              }`}
            >
              Full payment
            </button>
            <button
              type="button"
              onClick={() => {
                setSplitMode(true);
                setPayAmount('');
              }}
              className={`flex-1 px-3 py-2 text-xs font-semibold rounded-lg border ${
                splitMode ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'border-[var(--border)]'
              }`}
            >
              Split / partial
            </button>
          </div>
        )}

        <label className="block mt-3 text-sm">
          <span className="text-[var(--muted)]">
            {advanceMode
              ? 'Advance amount (₹)'
              : splitMode
                ? 'Amount received now (₹)'
                : 'Amount to record (₹)'}
          </span>
          <input
            type="number"
            min={0}
            max={remaining > 0 ? remaining : undefined}
            step="0.01"
            value={payAmount}
            onChange={(e) => setPayAmount(e.target.value)}
            className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
            placeholder={remaining > 0 ? `Up to ${Math.round(remaining * 100) / 100}` : '0'}
          />
        </label>
        <label className="block mt-3 text-sm">
          <span className="text-[var(--muted)]">Paid by</span>
          <input
            type="text"
            value={payerName}
            onChange={(e) => setPayerName(e.target.value)}
            className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
            placeholder="Customer name"
          />
        </label>
        {(advanceMode || splitMode) && remaining > 0 && (
          <p className="text-xs text-[var(--muted)] mt-1">
            {advanceMode
              ? `Enter an amount up to ${formatCurrency(remaining)} (remaining balance).`
              : `Enter less than ${formatCurrency(remaining)} to log a partial installment.`}
          </p>
        )}

        <div className="mt-4 pt-4 border-t border-[var(--border)]">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-3">
            Payment details (admin)
          </p>
          <PaymentRecordFields value={paymentMeta} onChange={setPaymentMeta} />
        </div>

        {!advanceMode && (
          <details className="mt-3 text-xs text-[var(--muted)]">
            <summary className="cursor-pointer font-semibold text-[var(--foreground)]">Full vs partial payment</summary>
            <ul className="mt-2 space-y-1.5 list-disc pl-4 leading-relaxed">
              <li>
                <strong>Full payment</strong> — records the remaining balance. When balance reaches ₹0, the order is marked paid.
              </li>
              <li>
                <strong>Split / partial</strong> — records an installment only. Prior advances are already subtracted from balance due.
              </li>
            </ul>
          </details>
        )}
        {error && <p className="text-sm text-[var(--danger)] mt-3">{error}</p>}

        <div className="flex flex-col sm:flex-row gap-2 mt-6">
          <button
            type="button"
            disabled={busy}
            onClick={() => void submit(advanceMode ? false : !splitMode)}
            className="flex-1 px-4 py-2.5 text-sm font-medium rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-60"
          >
            {advanceMode
              ? 'Save advance payment'
              : splitMode
                ? 'Save partial payment'
                : 'Yes, payment received'}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={remindLater}
            className="flex-1 px-4 py-2.5 text-sm font-medium rounded-xl border border-[var(--border)] hover:bg-[var(--sidebar-hover)] disabled:opacity-60"
          >
            {forcedMode ? 'Close' : 'Not yet'}
          </button>
        </div>
        {!forcedMode && (
          <Link
            to={`/orders/${order.id}`}
            className="block text-center text-sm text-[var(--primary)] hover:underline mt-4"
          >
            Open order
          </Link>
        )}
        {!forcedMode && !advanceMode && pending.length > 1 && (
          <p className="text-xs text-center text-[var(--muted)] mt-2">
            {pending.length - 1} more delivered order{pending.length === 2 ? '' : 's'} waiting
          </p>
        )}
      </Card>
    </div>
  );
}
