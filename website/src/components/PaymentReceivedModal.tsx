import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Enquiry } from '../api/client';
import { confirmEnquiryPayment, formatCurrency } from '../api/client';
import {
  orderAmountPaid,
  orderBillingTotal,
  orderDiscount,
} from '../utils/orderBilling';
import { Card } from './Layout';

export function PaymentReceivedModal({
  orders,
  onResolved,
  forceOrderId = null,
  onCloseForce,
}: {
  orders: Enquiry[];
  dishes?: unknown;
  onResolved: (updated: Enquiry) => void | Promise<void>;
  /** Open payment UI for a specific order (e.g. from order detail page). */
  forceOrderId?: string | null;
  onCloseForce?: () => void;
}) {
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [splitMode, setSplitMode] = useState(false);
  const [discount, setDiscount] = useState('');
  const [payAmount, setPayAmount] = useState('');
  const [payerName, setPayerName] = useState('');

  const pending = useMemo(
    () =>
      orders.filter(
        (o) =>
          o.status === 'CONVERTED' &&
          Boolean(o.deliveredAt) &&
          !o.paymentReceived &&
          orderAmountPaid(o) <= 0 &&
          !dismissed.includes(o.id),
      ),
    [orders, dismissed],
  );

  const forced = useMemo(() => {
    if (!forceOrderId) return null;
    return (
      orders.find(
        (o) =>
          o.id === forceOrderId &&
          o.status === 'CONVERTED' &&
          Boolean(o.deliveredAt) &&
          !o.paymentReceived,
      ) ?? null
    );
  }, [orders, forceOrderId]);

  const current = forced ?? pending[0];
  const forcedMode = Boolean(forced);

  const billing = current ? orderBillingTotal(current) : 0;
  const existingDiscount = current ? orderDiscount(current) : 0;
  const paid = current ? orderAmountPaid(current) : 0;
  const discountNum = Math.max(0, Number(discount) || 0);
  const effectiveDiscount = discount.trim() === '' ? existingDiscount : discountNum;
  const remaining = Math.max(0, billing - effectiveDiscount - paid);

  useEffect(() => {
    if (!current) return;
    setDiscount(existingDiscount > 0 ? String(existingDiscount) : '');
    setPayAmount(remaining > 0 ? String(Math.round(remaining * 100) / 100) : '');
    setPayerName(current.customerName || '');
    setSplitMode(paid > 0);
    setError(null);
  }, [current?.id, forceOrderId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!current) return null;

  async function submit(fullPay: boolean) {
    setBusy(true);
    setError(null);
    try {
      const typed = Math.max(0, Number(payAmount) || 0);
      const amount = fullPay ? (typed > 0 ? typed : remaining) : typed;
      if (amount <= 0) {
        setError('Enter a payment amount greater than 0');
        setBusy(false);
        return;
      }
      const updated = await confirmEnquiryPayment(current.id, {
        received: true,
        amount,
        payerName: payerName.trim() || current.customerName,
        discountAmount: effectiveDiscount,
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
    setDismissed((ids) => [...ids, current.id]);
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
          Order delivered
        </p>
        <h2 id="payment-received-title" className="text-xl font-semibold text-[var(--foreground)]">
          Did you receive payment?
        </h2>
        <p className="text-sm text-[var(--muted)] mt-2">
          <span className="font-medium text-[var(--foreground)]">{current.customerName}</span>
          {' · '}
          {current.eventType}
        </p>

        <div className="mt-4 space-y-1 text-sm">
          <div className="flex justify-between gap-3">
            <span className="text-[var(--muted)]">Order total</span>
            <span className="font-semibold tabular-nums">{formatCurrency(billing)}</span>
          </div>
          {paid > 0 && (
            <div className="flex justify-between gap-3">
              <span className="text-[var(--muted)]">Already paid</span>
              <span className="tabular-nums">{formatCurrency(paid)}</span>
            </div>
          )}
          <div className="flex justify-between gap-3">
            <span className="text-[var(--muted)]">Balance due</span>
            <span className="font-bold text-[var(--primary)] tabular-nums">{formatCurrency(remaining)}</span>
          </div>
        </div>

        <label className="block mt-4 text-sm">
          <span className="text-[var(--muted)]">Discount (₹)</span>
          <input
            type="number"
            min={0}
            step="0.01"
            value={discount}
            onChange={(e) => setDiscount(e.target.value)}
            className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
            placeholder="0"
          />
        </label>

        <div className="mt-3 flex gap-2">
          <button
            type="button"
            onClick={() => {
              setSplitMode(false);
              setPayAmount(String(Math.round(remaining * 100) / 100));
            }}
            className={`flex-1 px-3 py-2 text-xs font-semibold rounded-lg border ${
              !splitMode ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'border-[var(--border)]'
            }`}
          >
            Full payment
          </button>
          <button
            type="button"
            onClick={() => setSplitMode(true)}
            className={`flex-1 px-3 py-2 text-xs font-semibold rounded-lg border ${
              splitMode ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'border-[var(--border)]'
            }`}
          >
            Split / partial
          </button>
        </div>

        <label className="block mt-3 text-sm">
          <span className="text-[var(--muted)]">
            {splitMode ? 'Amount received now (₹)' : 'Amount to record (₹)'}
          </span>
          <input
            type="number"
            min={0}
            step="0.01"
            value={payAmount}
            onChange={(e) => setPayAmount(e.target.value)}
            className="mt-1 w-full rounded-xl border border-[var(--border)] bg-[var(--background)] px-3 py-2"
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

        <p className="text-xs text-[var(--muted)] mt-3">
          Confirmed amounts are added to dashboard revenue. Partial balances stay under Partial payments until cleared.
        </p>
        {error && <p className="text-sm text-[var(--danger)] mt-3">{error}</p>}

        <div className="flex flex-col sm:flex-row gap-2 mt-6">
          <button
            type="button"
            disabled={busy}
            onClick={() => void submit(!splitMode)}
            className="flex-1 px-4 py-2.5 text-sm font-medium rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-60"
          >
            {splitMode ? 'Save partial payment' : 'Yes, payment received'}
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
            to={`/orders/${current.id}`}
            className="block text-center text-sm text-[var(--primary)] hover:underline mt-4"
          >
            Open order
          </Link>
        )}
        {!forcedMode && pending.length > 1 && (
          <p className="text-xs text-center text-[var(--muted)] mt-2">
            {pending.length - 1} more delivered order{pending.length === 2 ? '' : 's'} waiting
          </p>
        )}
      </Card>
    </div>
  );
}
