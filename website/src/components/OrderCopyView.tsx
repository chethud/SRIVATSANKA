import { formatDate, type Enquiry } from '../api/client';
import { BrandLogo } from './BrandLogo';
import { parseOrderNotes } from '../utils/orderNotes';
import {
  dishesForColumn,
  formatColumnAmount,
  formatPaxTimeLine,
  resolveMenuColumns,
} from '../utils/orderMenuGrid';
import { PREFERENCE_CATEGORIES } from '../utils/mealSessions';

export function OrderCopyView({ enquiry, copyType }: { enquiry: Enquiry; copyType: 'kitchen' | 'billing' }) {
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);

  return (
    <div
      className="max-w-5xl mx-auto bg-white print:shadow-none excel-menu-grid"
      id="order-copy-print"
      style={{ fontFamily: 'Verdana, Geneva, Tahoma, sans-serif', fontSize: '11px' }}
    >
      <div className="-mx-8 -mt-8 mb-6 px-6 pt-6 pb-4 border-b-4 border-[var(--accent)]">
        <BrandLogo variant="card" className="mx-auto max-w-[220px]" />
        <p className="text-center text-sm font-semibold text-[var(--primary)] mt-4">{title}</p>
      </div>

      <div className="mb-6 space-y-1 border-b border-[var(--border)] pb-4">
        <p className="font-bold">
          Client : {enquiry.customerName}
          {enquiry.eventType ? ` · ${enquiry.eventType}` : ''}
        </p>
        <p className="font-bold">{enquiry.eventLocation}</p>
      </div>

      {columns.length === 0 ? (
        <p className="text-[var(--muted)]">No dishes on this order yet.</p>
      ) : (
        <div className="overflow-x-auto border border-[var(--border-strong)]">
          <div
            className="grid border-b border-[var(--border-strong)] bg-[var(--table-header-bg)]"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(180px, 1fr))` }}
          >
            {columns.map((col) => (
              <div key={col.id} className="px-2 py-2 border-r border-[var(--border)] last:border-r-0 text-center font-bold">
                {formatDate(col.date)}
              </div>
            ))}
          </div>
          <div
            className="grid border-b border-[var(--border-strong)]"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(180px, 1fr))` }}
          >
            {columns.map((col) => (
              <div key={col.id} className="px-2 py-2 border-r border-[var(--border)] last:border-r-0 text-center font-bold min-h-[2.5rem] flex items-center justify-center">
                {col.sessionLabel}
              </div>
            ))}
          </div>
          <div
            className="grid border-b border-[var(--border)] bg-[var(--background-alt)]"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(180px, 1fr))` }}
          >
            {columns.map((col) => (
              <div key={col.id} className="px-2 py-2 border-r border-[var(--border)] last:border-r-0 text-center font-bold">
                {formatPaxTimeLine(col)}
              </div>
            ))}
          </div>
          {copyType === 'billing' && (
            <div
              className="grid border-b border-[var(--border-strong)] bg-[var(--order-cream)]"
              style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(180px, 1fr))` }}
            >
              {columns.map((col) => (
                <div key={col.id} className="px-2 py-2 border-r border-[var(--border)] last:border-r-0 text-center font-bold">
                  {formatColumnAmount(col.amount) || '—'}
                </div>
              ))}
            </div>
          )}
          <div
            className="grid items-start"
            style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(180px, 1fr))` }}
          >
            {columns.map((col) => {
              const items = dishesForColumn(col, menuItems, extras);
              return (
                <div key={col.id} className="px-2 py-2 border-r border-[var(--border)] last:border-r-0 align-top min-h-[80px]">
                  {items.length === 0 ? (
                    <span className="text-[var(--muted)]">—</span>
                  ) : (
                    <ul className="space-y-1 list-none m-0 p-0">
                      {items.map((l) => (
                        <li key={l.id}>
                          {l.dishName}
                          {l.served && <span className="text-[var(--logo-forest)]"> ✓</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
