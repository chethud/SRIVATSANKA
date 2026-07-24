import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Enquiry } from '../api/client';
import { confirmEnquiryPayment, formatCurrency, formatDate } from '../api/client';
import {
  isPartialPaymentOrder,
  orderAmountDue,
  orderAmountPaid,
  orderBillingTotal,
} from '../utils/orderBilling';
import { GlassCard } from './dashboard/DashboardSections';

export function PartialPaymentsPanel({
  enquiries,
  onUpdated,
}: {
  enquiries: Enquiry[];
  onUpdated: (updated: Enquiry) => void | Promise<void>;
}) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, { amount: string; payer: string; discount: string }>>({});

  const partials = enquiries.filter(isPartialPaymentOrder);

  function draftFor(o: Enquiry) {
    return (
      drafts[o.id] ?? {
        amount: String(Math.round(orderAmountDue(o) * 100) / 100),
        payer: o.customerName,
        discount: String(o.discountAmount ?? 0),
      }
    );
  }

  async function savePartial(o: Enquiry, payAll: boolean) {
    const d = draftFor(o);
    setBusyId(o.id);
    try {
      const remaining = orderAmountDue(o);
      const amount = payAll ? remaining : Math.max(0, Number(d.amount) || 0);
      const updated = await confirmEnquiryPayment(o.id, {
        received: true,
        amount,
        payerName: d.payer.trim() || o.customerName,
        discountAmount: Math.max(0, Number(d.discount) || 0),
      });
      await onUpdated(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not save payment');
    } finally {
      setBusyId(null);
    }
  }

  if (partials.length === 0) {
    return (
      <GlassCard title="Partial payments">
        <p className="text-sm text-[var(--muted)] py-8 text-center">
          No open balances. Split payments will appear here until the order is fully paid.
        </p>
      </GlassCard>
    );
  }

  return (
    <GlassCard title="Partial payments" action={<span className="text-xs text-[var(--muted)]">{partials.length} open</span>}>
      <div className="space-y-4">
        {partials.map((o) => {
          const d = draftFor(o);
          return (
            <div key={o.id} className="rounded-xl border border-[var(--border)] p-4 space-y-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="font-semibold">{o.customerName}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {o.eventType} · {formatDate(o.eventDate)}
                  </p>
                </div>
                <Link to={`/orders/${o.id}`} className="text-xs text-[var(--primary)] hover:underline">
                  Open order
                </Link>
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className="rounded-lg bg-[var(--background)] p-2">
                  <p className="text-[var(--muted)]">Order</p>
                  <p className="font-semibold tabular-nums">{formatCurrency(orderBillingTotal(o))}</p>
                </div>
                <div className="rounded-lg bg-[var(--success-bg)] p-2">
                  <p className="text-[var(--muted)]">Paid</p>
                  <p className="font-semibold tabular-nums text-[var(--success-text)]">{formatCurrency(orderAmountPaid(o))}</p>
                </div>
                <div className="rounded-lg bg-amber-50 p-2">
                  <p className="text-[var(--muted)]">Pending</p>
                  <p className="font-semibold tabular-nums text-amber-900">{formatCurrency(orderAmountDue(o))}</p>
                </div>
              </div>
              {(o.payments ?? []).length > 0 && (
                <ul className="text-xs text-[var(--muted)] space-y-1">
                  {o.payments!.map((p) => (
                    <li key={p.id}>
                      {formatCurrency(p.amount)} · {p.payerName || 'Customer'} · {formatDate(p.paidAt)}
                    </li>
                  ))}
                </ul>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input
                  type="number"
                  min={0}
                  className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
                  placeholder="Amount now"
                  value={d.amount}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [o.id]: { ...d, amount: e.target.value } }))}
                />
                <input
                  type="text"
                  className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
                  placeholder="Paid by"
                  value={d.payer}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [o.id]: { ...d, payer: e.target.value } }))}
                />
                <input
                  type="number"
                  min={0}
                  className="rounded-lg border border-[var(--border)] px-3 py-2 text-sm"
                  placeholder="Discount"
                  value={d.discount}
                  onChange={(e) => setDrafts((prev) => ({ ...prev, [o.id]: { ...d, discount: e.target.value } }))}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busyId === o.id}
                  onClick={() => void savePartial(o, false)}
                  className="px-3 py-2 text-sm font-medium rounded-xl bg-[var(--primary)] text-white disabled:opacity-60"
                >
                  Add payment
                </button>
                <button
                  type="button"
                  disabled={busyId === o.id}
                  onClick={() => void savePartial(o, true)}
                  className="px-3 py-2 text-sm font-medium rounded-xl border border-[var(--border)] disabled:opacity-60"
                >
                  Clear balance
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </GlassCard>
  );
}
