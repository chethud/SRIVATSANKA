import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Dish, Enquiry } from '../api/client';
import { confirmEnquiryPayment, formatCurrency } from '../api/client';
import { Card } from './Layout';

function orderTotal(order: Enquiry, dishes: Dish[]): number {
  const menu = Object.fromEntries(dishes.map((d) => [d.id, d.price]));
  const lineSum = (order.dishes ?? []).reduce((sum, item) => {
    const unit = item.unitPrice ?? (item.dishId ? menu[item.dishId] ?? 0 : 0);
    return sum + unit * Math.max(1, item.quantity || 1);
  }, 0);
  return lineSum * Math.max(1, order.guestCount || 1);
}

export function PaymentReceivedModal({
  orders,
  dishes,
  onResolved,
}: {
  orders: Enquiry[];
  dishes: Dish[];
  onResolved: (updated: Enquiry) => void | Promise<void>;
}) {
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pending = useMemo(
    () =>
      orders.filter(
        (o) =>
          o.status === 'CONVERTED' &&
          Boolean(o.deliveredAt) &&
          !o.paymentReceived &&
          !dismissed.includes(o.id),
      ),
    [orders, dismissed],
  );

  const current = pending[0];
  if (!current) return null;

  const amount = orderTotal(current, dishes);

  async function confirmYes() {
    setBusy(true);
    setError(null);
    try {
      const updated = await confirmEnquiryPayment(current.id, true);
      await onResolved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save payment status');
    } finally {
      setBusy(false);
    }
  }

  function remindLater() {
    setDismissed((ids) => [...ids, current.id]);
  }

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/45"
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-received-title"
    >
      <Card className="w-full max-w-md p-6 shadow-xl">
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
        <p className="text-2xl font-bold text-[var(--primary)] mt-4">{formatCurrency(amount)}</p>
        <p className="text-xs text-[var(--muted)] mt-1">
          If you confirm, this amount is added to dashboard revenue.
        </p>
        {error && <p className="text-sm text-[var(--danger)] mt-3">{error}</p>}
        <div className="flex flex-col sm:flex-row gap-2 mt-6">
          <button
            type="button"
            disabled={busy}
            onClick={() => void confirmYes()}
            className="flex-1 px-4 py-2.5 text-sm font-medium rounded-xl bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-60"
          >
            Yes, payment received
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={remindLater}
            className="flex-1 px-4 py-2.5 text-sm font-medium rounded-xl border border-[var(--border)] hover:bg-[var(--sidebar-hover)] disabled:opacity-60"
          >
            Not yet
          </button>
        </div>
        <Link
          to={`/orders/${current.id}`}
          className="block text-center text-sm text-[var(--primary)] hover:underline mt-4"
        >
          Open order
        </Link>
        {pending.length > 1 && (
          <p className="text-xs text-center text-[var(--muted)] mt-2">
            {pending.length - 1} more delivered order{pending.length === 2 ? '' : 's'} waiting
          </p>
        )}
      </Card>
    </div>
  );
}
