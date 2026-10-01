import { useMemo } from 'react';
import { formatDate, type Enquiry, type Worker } from '../api/client';
import { orderCopyBillingBase, orderCopyBillingBreakdown } from '../utils/orderBilling';
import { workerNeedsHeadcount } from '../utils/workerStaff';
import { BrandLogo } from './BrandLogo';
import {
  eventDatesForStyles,
  parseOrderNotes,
  resolveAssignedWorkerIds,
  resolveStyleForDate,
} from '../utils/orderNotes';
import {
  dishesForColumn,
  formatColumnAmount,
  formatPaxTimeLine,
  resolveMenuColumns,
} from '../utils/orderMenuGrid';
import { PREFERENCE_CATEGORIES } from '../utils/mealSessions';
import { OrderExtrasTable } from './order/OrderExtrasSection';
import { OrderRegionalStylePrint } from './order/OrderRegionalStyleSection';
import { VenueMapQrPrint } from './order/OrderVenueMapSection';
import { kitchenSpecificationNotes } from '../utils/kitchenSpecs';

export type OrderCopyKind = 'kitchen' | 'billing' | 'ours';

const AMOUNT_SCALE: Record<OrderCopyKind, number> = {
  kitchen: 1,
  billing: 1,
  ours: 0.5,
};

function scaleAmount(amount: number | null | undefined, scale: number): number | null {
  if (typeof amount !== 'number') return null;
  return Math.round(amount * scale * 100) / 100;
}

export function OrderCopyView({
  enquiry,
  copyType,
  workers = [],
}: {
  enquiry: Enquiry;
  copyType: OrderCopyKind;
  workers?: Worker[];
}) {
  const title =
    copyType === 'kitchen' ? 'Kitchen Copy' : copyType === 'ours' ? 'Our Copy' : 'Order Copy';
  const showMoney = copyType === 'billing' || copyType === 'ours';
  const amountScale = AMOUNT_SCALE[copyType];
  const extras = parseOrderNotes(enquiry.notes);
  const kitchenSpecs = kitchenSpecificationNotes(extras.dietary);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);
  const billingBreakdown = useMemo(
    () => (showMoney ? orderCopyBillingBreakdown(enquiry) : null),
    [enquiry, showMoney],
  );

  const grandTotal = useMemo(() => {
    if (!showMoney) return null;
    const base = orderCopyBillingBase(enquiry);
    if (base <= 0) return null;
    return scaleAmount(base, amountScale);
  }, [amountScale, enquiry, showMoney]);

  const kitchenStaffLines = useMemo(() => {
    if (copyType !== 'kitchen' || workers.length === 0) return [];
    const ids = resolveAssignedWorkerIds(extras);
    const headcounts = extras.staffHeadcounts ?? {};
    const lines: string[] = [];
    for (const id of ids) {
      const w = workers.find((x) => x.id === id);
      if (!w) continue;
      if (workerNeedsHeadcount(w.name)) {
        const n = headcounts[id] ?? 1;
        lines.push(`${w.name}: ${n}`);
      } else {
        lines.push(w.name);
      }
    }
    return lines;
  }, [copyType, extras, workers]);

  const stylesByDate = useMemo(() => {
    return eventDatesForStyles(extras, enquiry.eventDate)
      .map((date) => ({ date, style: resolveStyleForDate(extras, date) ?? '' }))
      .filter((row) => row.style);
  }, [extras, enquiry.eventDate]);

  const shownDayStyle = useMemo(() => {
    const seen = new Set<string>();
    return columns.map((col) => {
      const key = col.date.slice(0, 10);
      if (seen.has(key)) return null;
      seen.add(key);
      return resolveStyleForDate(extras, key);
    });
  }, [columns, extras]);

  return (
    <div id="order-copy-print" className="order-copy-print">
      <header className="copy-header">
        <BrandLogo variant="card" className="copy-logo" />
        <p className="copy-doc-title">{title}</p>
      </header>

      {copyType === 'ours' && (
        <p className="copy-ours-note print:hidden">
          Amounts at 50% of the order total. GST (CGST/SGST) on Excel download is calculated on this half.
        </p>
      )}

      <div className="copy-intro">
        <div className="copy-client-block">
          <p className="copy-client-line">
            Client : {enquiry.customerName}
            {enquiry.eventType ? ` · ${enquiry.eventType}` : ''}
          </p>
          <p className="copy-client-line">{enquiry.eventLocation}</p>
        </div>

        <OrderRegionalStylePrint stylesByDate={stylesByDate} />
      </div>

      {copyType === 'kitchen' && kitchenSpecs.length > 0 && (
        <div className="copy-spec-banner" role="note">
          {kitchenSpecs.map((note) => (
            <p key={note} className="copy-spec-banner-line">
              {note}
            </p>
          ))}
        </div>
      )}

      <div className="copy-menu">
        {columns.length === 0 ? (
          <p className="copy-empty">No dishes on this order yet.</p>
        ) : (
          <div className="copy-sessions">
          {columns.map((col, index) => {
            const items = dishesForColumn(col, menuItems, extras, columns);
            const paxLine = formatPaxTimeLine(col);
            const dayStyle = shownDayStyle[index];
            const displayAmount = scaleAmount(
              typeof col.amount === 'number' ? col.amount : null,
              amountScale,
            );

            return (
              <section
                key={col.id}
                className={`copy-session-block ${copyType === 'kitchen' ? 'copy-session-kitchen' : ''}`}
              >
                <div className="copy-session-date">{formatDate(col.date)}</div>
                {dayStyle && (
                  <div className="copy-session-style font-semibold text-[var(--primary)]">
                    {dayStyle}
                  </div>
                )}
                <div className="copy-session-label">{col.sessionLabel}</div>
                {paxLine && <div className="copy-session-pax">{paxLine}</div>}

                <ul className="copy-dish-list">
                  {items.length === 0 ? (
                    <li className="copy-dish-empty">—</li>
                  ) : (
                    items.map((d) => (
                      <li key={d.id}>
                        {d.dishName}
                        {d.served && copyType === 'kitchen' ? ' ✓' : ''}
                      </li>
                    ))
                  )}
                </ul>

                {showMoney && items.length > 0 && (
                  <div className="copy-session-total">
                    <p className="copy-session-total-label">Session total</p>
                    <p className="copy-session-total-amount">
                      {formatColumnAmount(displayAmount) || '—'}
                    </p>
                  </div>
                )}
              </section>
            );
          })}
          </div>
        )}
      </div>

      {extras.extrasEnabled && (
        <OrderExtrasTable
          items={(extras.extraItems ?? []).map((item) =>
            showMoney && amountScale !== 1 && typeof item.amount === 'number'
              ? { ...item, amount: scaleAmount(item.amount, amountScale) ?? item.amount }
              : item,
          )}
          hideAmounts={copyType === 'kitchen'}
          highlightSpecs={copyType === 'kitchen'}
        />
      )}

      {showMoney && grandTotal != null && (
        <div className="copy-overall-total">
          <p className="copy-overall-total-label">
            {copyType === 'ours' ? 'Overall total (50%)' : 'Overall total'}
          </p>
          <p className="copy-overall-total-amount">{formatColumnAmount(grandTotal)}</p>
          {billingBreakdown &&
            billingBreakdown.contractTotal == null &&
            billingBreakdown.sessions > 0 &&
            billingBreakdown.extras > 0 && (
              <p className="copy-overall-total-hint text-sm text-[var(--muted)] mt-1">
                Sessions {formatColumnAmount(scaleAmount(billingBreakdown.sessions, amountScale) ?? 0)} + extras{' '}
                {formatColumnAmount(scaleAmount(billingBreakdown.extras, amountScale) ?? 0)}
              </p>
            )}
        </div>
      )}

      {copyType === 'kitchen' && kitchenStaffLines.length > 0 && (
        <div className="copy-regional-style">
          <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
            Assigned staff
          </div>
          <div className="px-4 py-3 space-y-1">
            {kitchenStaffLines.map((line) => (
              <p key={line} className="text-center copy-client-line font-semibold">{line}</p>
            ))}
          </div>
        </div>
      )}

      {copyType === 'kitchen' && (
        <footer className="copy-venue-footer">
          <VenueMapQrPrint mapLink={extras.venueMapLink} />
        </footer>
      )}
    </div>
  );
}
