import { useMemo } from 'react';
import { formatDate, type Enquiry } from '../api/client';
import { BrandLogo } from './BrandLogo';
import { parseOrderNotes } from '../utils/orderNotes';
import {
  dishesForColumn,
  formatColumnAmount,
  formatPaxTimeLine,
  resolveMenuColumns,
  sumOrderCopyTotals,
} from '../utils/orderMenuGrid';
import { PREFERENCE_CATEGORIES } from '../utils/mealSessions';
import { OrderExtrasTable } from './order/OrderExtrasSection';
import { OrderRegionalStylePrint } from './order/OrderRegionalStyleSection';
import { VenueMapQrPrint } from './order/OrderVenueMapSection';

export function OrderCopyView({ enquiry, copyType }: { enquiry: Enquiry; copyType: 'kitchen' | 'billing' }) {
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);
  const grandTotal = useMemo(
    () => (copyType === 'billing' ? sumOrderCopyTotals(columns) : null),
    [columns, copyType],
  );

  return (
    <div
      className="max-w-3xl mx-auto bg-white print:shadow-none excel-menu-grid order-copy-print"
      id="order-copy-print"
    >
      <div className="-mx-8 -mt-8 mb-6 px-6 pt-6 pb-4 border-b-4 border-[var(--accent)]">
        <BrandLogo variant="card" className="mx-auto max-w-[220px]" />
        <p className="text-center text-lg font-semibold text-[var(--primary)] mt-4">{title}</p>
      </div>

      <div className="mb-6 space-y-1 border-b border-[var(--border)] pb-4">
        <p className="copy-client-line font-bold">
          Client : {enquiry.customerName}
          {enquiry.eventType ? ` · ${enquiry.eventType}` : ''}
        </p>
        <p className="copy-client-line font-bold">{enquiry.eventLocation}</p>
      </div>

      {columns.length === 0 ? (
        <p className="text-[var(--muted)] text-lg">No dishes on this order yet.</p>
      ) : (
        <div className="space-y-6">
          {columns.map((col) => {
            const items = dishesForColumn(col, menuItems, extras);
            return (
              <div key={col.id} className="border border-[var(--border-strong)] overflow-hidden">
                <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--table-header-bg)]">
                  {formatDate(col.date)}
                </div>
                <div className="copy-grid-meta font-bold text-center border-b border-[var(--border-strong)]">
                  {col.sessionLabel}
                </div>
                <div className="copy-grid-meta font-bold text-center border-b border-[var(--border)] bg-[var(--background-alt)]">
                  {formatPaxTimeLine(col)}
                </div>
                <div className="px-4 py-4 min-h-[80px]">
                  {items.length === 0 ? (
                    <span className="text-[var(--muted)] text-lg">—</span>
                  ) : (
                    <ul className="space-y-1 list-none m-0 p-0">
                      {items.map((l) => (
                        <li key={l.id} className="copy-dish-name">
                          {l.dishName}
                          {l.served && <span className="text-[var(--logo-forest)]"> ✓</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                {copyType === 'billing' && items.length > 0 && (
                  <div className="copy-grid-meta text-center border-t border-[var(--border-strong)] bg-[var(--order-cream)] px-4 py-3">
                    <p className="text-[10px] uppercase tracking-wider text-[var(--order-accent)] font-semibold mb-1">
                      Session total
                    </p>
                    <p className="font-bold text-lg text-[var(--foreground)]">
                      {formatColumnAmount(col.amount) || '—'}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <OrderRegionalStylePrint style={extras.regionalStyle} />

      {copyType === 'billing' && extras.extrasEnabled && (
        <OrderExtrasTable items={extras.extraItems ?? []} />
      )}

      {copyType === 'billing' && grandTotal != null && (
        <div className="mt-8 border-2 border-[var(--primary)] rounded-lg overflow-hidden bg-[var(--primary-light)]">
          <div className="px-4 py-4 text-center">
            <p className="text-xs uppercase tracking-wider text-[var(--order-accent)] font-semibold mb-1">
              Overall total
            </p>
            <p className="text-2xl font-bold text-[var(--primary-dark)]">
              {formatColumnAmount(grandTotal)}
            </p>
          </div>
        </div>
      )}

      {copyType === 'kitchen' && <VenueMapQrPrint mapLink={extras.venueMapLink} />}
    </div>
  );
}
