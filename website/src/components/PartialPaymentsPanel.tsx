import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X } from 'lucide-react';
import type { Enquiry } from '../api/client';
import { confirmEnquiryPayment, formatCurrency, formatDate } from '../api/client';
import {
  isOrderPaymentComplete,
  isPartialPaymentOrder,
  orderAmountDue,
  orderAmountPaid,
  orderBillingTotal,
} from '../utils/orderBilling';
import { GlassCard } from './dashboard/DashboardSections';
import { Card } from './Layout';
import { PaymentRecordFields, paymentPayloadExtras, type PaymentRecordDraft } from './PaymentRecordFields';
import { defaultPaymentPaidAtLocal, paymentModeLabel } from '../utils/paymentRecord';

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
  type Draft = {
    amount: string;
    payer: string;
    discount: string;
    payment: PaymentRecordDraft;
  };
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});

  const partials = enquiries.filter(isPartialPaymentOrder);
  const settledOrders = enquiries.filter(
    (e) => e.status === 'CONVERTED' && isOrderPaymentComplete(e),
  );
  const totalReceivedOpen = partials.reduce((sum, o) => sum + orderAmountPaid(o), 0);
  const totalDueOpen = partials.reduce((sum, o) => sum + orderAmountDue(o), 0);
  const active = partials.find((o) => o.id === activeId) ?? null;

  useEffect(() => {
    if (activeId && !partials.some((o) => o.id === activeId)) {
      setActiveId(null);
    }
  }, [activeId, partials]);

  function draftFor(o: Enquiry) {
    return (
      drafts[o.id] ?? {
        amount: '',
        payer: o.customerName,
        discount: String(o.discountAmount ?? 0),
        payment: {
          paymentMode: '',
          paidAt: defaultPaymentPaidAtLocal(),
          paymentNotes: '',
          receivedAccount: '',
        },
      }
    );
  }

  async function savePartial(o: Enquiry, payAll: boolean) {
    const d = draftFor(o);
    setBusyId(o.id);
    try {
      const remaining = orderAmountDue(o);
      let amount: number;
      if (payAll) {
        amount = remaining;
      } else {
        amount = Math.max(0, Number(d.amount) || 0);
        if (amount <= 0) {
          alert('Enter the installment amount to record');
          return;
        }
        if (amount >= remaining - 0.009) {
          alert('For the remaining balance, use Clear balance (or enter an amount less than the due total)');
          return;
        }
        if (amount > remaining) {
          alert('Installment cannot exceed the balance due');
          return;
        }
      }
      if (amount <= 0) {
        alert('No balance left to collect');
        return;
      }
      const updated = await confirmEnquiryPayment(o.id, {
        received: true,
        amount,
        payerName: d.payer.trim() || o.customerName,
        discountAmount: Math.max(0, Number(d.discount) || 0),
        ...paymentPayloadExtras(d.payment),
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

  const helpBlurb = (
    <div className="mb-4 space-y-3">
      <p className="text-sm text-[var(--muted)] leading-relaxed">
        <strong className="text-[var(--foreground)]">Partial payments</strong> are orders with some cash recorded but a balance still due.
        Record each installment from here or from the order page.
      </p>
      {partials.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
          <div className="rounded-lg border border-[var(--border)] bg-[var(--success-bg)] px-3 py-2.5">
            <p className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Received (open orders)</p>
            <p className="font-bold tabular-nums text-[var(--success-text)] mt-0.5">
              {formatCurrency(totalReceivedOpen)}
            </p>
          </div>
          <div className="rounded-lg border border-[var(--border)] bg-amber-50 px-3 py-2.5">
            <p className="text-xs text-[var(--muted)] font-semibold uppercase tracking-wide">Still due</p>
            <p className="font-bold tabular-nums text-amber-900 mt-0.5">{formatCurrency(totalDueOpen)}</p>
          </div>
        </div>
      )}
    </div>
  );

  const emptyMessage = (
    <p className={`text-sm text-[var(--muted)] ${embedded ? '' : 'py-4 text-center'}`}>
      No open balances. Log a <strong>partial</strong> installment (less than the full due) and the order will appear here until
      the balance is cleared.
    </p>
  );

  const settledSection =
    settledOrders.length > 0 ? (
      <div className="mt-6 pt-6 border-t border-[var(--border)]">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-3">
          Fully received ({settledOrders.length})
        </p>
        <ul className="space-y-2 max-h-[14rem] overflow-y-auto overscroll-contain pr-1">
          {settledOrders.map((o) => (
            <li
              key={o.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border)] bg-[var(--background)] px-3 py-2"
            >
              <Link
                to={`/orders/${o.id}`}
                className="font-semibold text-[var(--foreground)] hover:text-[var(--primary)] min-w-0 break-words"
              >
                {o.customerName}
              </Link>
              <span className="tabular-nums font-semibold text-[var(--success-text)] shrink-0">
                {formatCurrency(orderAmountPaid(o))}
              </span>
            </li>
          ))}
        </ul>
      </div>
    ) : null;

  const list = (
    <div className="space-y-2">
      {partials.map((o) => (
        <button
          key={o.id}
          type="button"
          onClick={() => setActiveId(o.id)}
          className="w-full flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-xl border border-[var(--border)] bg-[var(--background)] px-4 py-3 text-left hover:border-[var(--primary)]/40 hover:bg-[var(--primary-light)]/40 transition-colors"
        >
          <span className="font-semibold text-[var(--foreground)] min-w-0 break-words">{o.customerName}</span>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm shrink-0">
            <span className="tabular-nums text-[var(--success-text)] font-semibold">
              Received {formatCurrency(orderAmountPaid(o))}
            </span>
            <span className="tabular-nums text-amber-900 font-semibold">
              Due {formatCurrency(orderAmountDue(o))}
            </span>
          </div>
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
                          {formatCurrency(p.amount)} · {paymentModeLabel(p.paymentMode)} ·{' '}
                          {p.receivedAccount || '—'} · {p.payerName || 'Customer'} · {formatDate(p.paidAt)}
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
                      placeholder={`Partial amount (due ${formatCurrency(orderAmountDue(active))})`}
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

                <div className="mt-4 pt-4 border-t border-[var(--border)]">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)] mb-3">
                    Payment details (admin)
                  </p>
                  <PaymentRecordFields
                    compact
                    value={d.payment}
                    onChange={(payment) =>
                      setDrafts((prev) => ({ ...prev, [active.id]: { ...d, payment } }))
                    }
                  />
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
      {settledSection}
      {modal}
    </>
  );

  if (embedded) return body;

  return (
    <GlassCard
      title="Partial payments"
      action={
        partials.length > 0 ? (
          <span className="text-xs text-[var(--muted)]">{partials.length} open</span>
        ) : undefined
      }
    >
      {helpBlurb}
      {partials.length > 0 ? (
        <div className="max-h-[18rem] overflow-y-auto overscroll-contain pr-1 -mr-1">{list}</div>
      ) : (
        emptyMessage
      )}
      {settledSection}
      {modal}
    </GlassCard>
  );
}
