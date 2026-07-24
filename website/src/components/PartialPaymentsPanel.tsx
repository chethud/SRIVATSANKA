import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import type { Enquiry } from '../api/client';
import { confirmEnquiryPayment, formatCurrency, formatDate } from '../api/client';
import {
  isPartialPaymentOrder,
  orderAmountDue,
  orderAmountPaid,
  orderBillingTotal,
} from '../utils/orderBilling';
import { GlassCard } from './dashboard/DashboardSections';
import { Card } from './Layout';

export function PartialPaymentsPanel({
  enquiries,
  onUpdated,
  embedded = false,
}: {
  enquiries: Enquiry[];
  onUpdated: (updated: Enquiry) => void | Promise<void>;
  /** When true, render list/empty state without an outer card (parent supplies the card). */
  embedded?: boolean;
}) {
  const [busyId, setBusyId] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, { amount: string; payer: string; discount: string }>>({});

  const partials = enquiries.filter(isPartialPaymentOrder);
  const active = partials.find((o) => o.id === activeId) ?? null;

  useEffect(() => {
    if (activeId && !partials.some((o) => o.id === activeId)) {
      setActiveId(null);
    }
  }, [activeId, partials]);

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
      if (payAll || orderAmountDue(updated) <= 0) {
        setActiveId(null);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not save payment');
    } finally {
      setBusyId(null);
    }
  }

  const emptyMessage = (
    <p className={`text-sm text-[var(--muted)] ${embedded ? '' : 'py-8 text-center'}`}>
      No open balances. Split payments will appear here until the order is fully paid.
    </p>
  );

  const list = (
    <div className="space-y-2">
      {partials.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => setActiveId(o.id)}
          className="w-full flex items-center justify-between gap-3 rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-left hover:border-[var(--primary)]/40 hover:bg-[var(--primary-light)]/40 transition-colors min-h-[3rem]"
        >
          <span className="font-semibold text-[var(--foreground)] min-w-0 break-words">{o.customerName}</span>
          <span className="shrink-0 tabular-nums font-semibold text-amber-900">
            {formatCurrency(orderAmountDue(o))}
          </span>
        </button>
      ))}
    </div>
  );

  const modal =
    active &&
    (() => {
      const d = draftFor(active);
      return (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
          role="dialog"
          aria-modal="true"
          aria-labelledby="split-payment-title"
          onClick={() => setActiveId(null)}
        >
          <div className="w-full max-w-lg max-h-[90vh]" onClick={(e) => e.stopPropagation()}>
            <Card className="flex flex-col overflow-hidden shadow-xl max-h-[90vh]">
              <div className="flex items-start justify-between gap-3 p-4 sm:p-5 border-b border-[var(--border)]">
                <div className="min-w-0">
                  <h2 id="split-payment-title" className="text-lg font-semibold break-words">
                    {active.customerName}
                  </h2>
                  <p className="text-xs text-[var(--muted)] mt-1">
                    {active.eventType} · {formatDate(active.eventDate)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveId(null)}
                  className="p-2 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--muted)] shrink-0"
                  aria-label="Close"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="overflow-y-auto p-4 sm:p-5 space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                  <div className="rounded-lg bg-[var(--background)] p-3">
                    <p className="text-[var(--muted)]">Order</p>
                    <p className="font-semibold tabular-nums text-sm">{formatCurrency(orderBillingTotal(active))}</p>
                  </div>
                  <div className="rounded-lg bg-[var(--success-bg)] p-3">
                    <p className="text-[var(--muted)]">Paid</p>
                    <p className="font-semibold tabular-nums text-sm text-[var(--success-text)]">
                      {formatCurrency(orderAmountPaid(active))}
                    </p>
                  </div>
                  <div className="rounded-lg bg-amber-50 p-3">
                    <p className="text-[var(--muted)]">Pending</p>
                    <p className="font-semibold tabular-nums text-sm text-amber-900">
                      {formatCurrency(orderAmountDue(active))}
                    </p>
                  </div>
                </div>

                {(active.payments ?? []).length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-2">
                      Payments so far
                    </p>
                    <ul className="text-sm text-[var(--muted)] space-y-1.5">
                      {active.payments!.map((p) => (
                        <li key={p.id} className="break-words">
                          {formatCurrency(p.amount)} · {p.payerName || 'Customer'} · {formatDate(p.paidAt)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <div>
                    <label className="text-xs text-[var(--muted)] mb-1 block">Amount now</label>
                    <input
                      type="number"
                      min={0}
                      className="w-full rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm min-h-[2.5rem]"
                      placeholder="Amount now"
                      value={d.amount}
                      onChange={(e) =>
                        setDrafts((prev) => ({ ...prev, [active.id]: { ...d, amount: e.target.value } }))
                      }
                    />
                  </div>
                  <div>
                    <label className="text-xs text-[var(--muted)] mb-1 block">Paid by</label>
                    <input
                      type="text"
                      className="w-full rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm min-h-[2.5rem]"
                      placeholder="Paid by"
                      value={d.payer}
                      onChange={(e) =>
                        setDrafts((prev) => ({ ...prev, [active.id]: { ...d, payer: e.target.value } }))
                      }
                    />
                  </div>
                  <div>
                    <label className="text-xs text-[var(--muted)] mb-1 block">Discount</label>
                    <input
                      type="number"
                      min={0}
                      className="w-full rounded-lg border border-[var(--border)] px-3 py-2.5 text-sm min-h-[2.5rem]"
                      placeholder="Discount"
                      value={d.discount}
                      onChange={(e) =>
                        setDrafts((prev) => ({ ...prev, [active.id]: { ...d, discount: e.target.value } }))
                      }
                    />
                  </div>
                </div>
              </div>

              <div className="p-4 sm:p-5 border-t border-[var(--border)] flex flex-wrap gap-2 justify-between">
                <Link
                  to={`/orders/${active.id}`}
                  className="inline-flex items-center text-sm text-[var(--primary)] hover:underline min-h-[2.5rem]"
                  onClick={() => setActiveId(null)}
                >
                  Open order
                </Link>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyId === active.id}
                    onClick={() => void savePartial(active, false)}
                    className="px-4 py-2.5 text-sm font-medium rounded-xl bg-[var(--primary)] text-white disabled:opacity-60 min-h-[2.5rem]"
                  >
                    Add payment
                  </button>
                  <button
                    type="button"
                    disabled={busyId === active.id}
                    onClick={() => void savePartial(active, true)}
                    className="px-4 py-2.5 text-sm font-medium rounded-xl border border-[var(--border)] disabled:opacity-60 min-h-[2.5rem]"
                  >
                    Clear balance
                  </button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      );
    })();

  const body = (
    <>
      {partials.length === 0 ? emptyMessage : list}
      {modal}
    </>
  );

  if (embedded) return body;

  if (partials.length === 0) {
    return <GlassCard title="Partial payments">{emptyMessage}</GlassCard>;
  }

  return (
    <GlassCard title="Partial payments" action={<span className="text-xs text-[var(--muted)]">{partials.length} open</span>}>
      <div className="max-h-[18rem] overflow-y-auto overscroll-contain pr-1 -mr-1">
        {list}
      </div>
      {modal}
    </GlassCard>
  );
}
