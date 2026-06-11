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
    <div id="order-copy-print" className="order-copy-print">
      <header className="copy-header">
        <BrandLogo variant="card" className="copy-logo" />
        <p className="copy-doc-title">{title}</p>
      </header>

      <div className="copy-client-block">
        <p className="copy-client-line">
          Client : {enquiry.customerName}
          {enquiry.eventType ? ` · ${enquiry.eventType}` : ''}
        </p>
        <p className="copy-client-line">{enquiry.eventLocation}</p>
      </div>

      {columns.length === 0 ? (
        <p className="copy-empty">No dishes on this order yet.</p>
      ) : (
        <div className="copy-sessions">
          {columns.map((col) => {
            const items = dishesForColumn(col, menuItems, extras);
            const paxLine = formatPaxTimeLine(col);

            return (
              <section key={col.id} className="copy-session-block">
                <div className="copy-session-date">{formatDate(col.date)}</div>
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

                {copyType === 'billing' && items.length > 0 && (
                  <div className="copy-session-total">
                    <p className="copy-session-total-label">Session total</p>
                    <p className="copy-session-total-amount">{formatColumnAmount(col.amount) || '—'}</p>
                  </div>
                )}
              </section>
            );
          })}
        </div>
      )}

      <OrderRegionalStylePrint style={extras.regionalStyle} />

      {copyType === 'billing' && extras.extrasEnabled && (
        <OrderExtrasTable items={extras.extraItems ?? []} />
      )}

      {copyType === 'billing' && grandTotal != null && (
        <div className="copy-overall-total">
          <p className="copy-overall-total-label">Overall total</p>
          <p className="copy-overall-total-amount">{formatColumnAmount(grandTotal)}</p>
        </div>
      )}

      {copyType === 'kitchen' && <VenueMapQrPrint mapLink={extras.venueMapLink} />}
    </div>
  );
}
