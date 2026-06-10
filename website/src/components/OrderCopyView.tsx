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

const gridCols = (count: number) =>
  ({ gridTemplateColumns: `repeat(${count}, minmax(220px, 1fr))` }) as const;

export function OrderCopyView({ enquiry, copyType }: { enquiry: Enquiry; copyType: 'kitchen' | 'billing' }) {
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';
  const extras = parseOrderNotes(enquiry.notes);
  const menuItems = (enquiry.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category));
  const columns = resolveMenuColumns(extras, enquiry, menuItems);

  return (
    <div
      className="max-w-5xl mx-auto bg-white print:shadow-none excel-menu-grid order-copy-print"
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
        <div className="overflow-x-auto border border-[var(--border-strong)]">
          <div className="grid border-b border-[var(--border-strong)] bg-[var(--table-header-bg)] copy-grid-meta font-bold" style={gridCols(columns.length)}>
            {columns.map((col) => (
              <div key={col.id} className="border-r border-[var(--border)] last:border-r-0 text-center">
                {formatDate(col.date)}
              </div>
            ))}
          </div>
          <div className="grid border-b border-[var(--border-strong)] copy-grid-meta font-bold" style={gridCols(columns.length)}>
            {columns.map((col) => (
              <div key={col.id} className="border-r border-[var(--border)] last:border-r-0 text-center min-h-[2.75rem] flex items-center justify-center">
                {col.sessionLabel}
              </div>
            ))}
          </div>
          <div className="grid border-b border-[var(--border)] bg-[var(--background-alt)] copy-grid-meta font-bold" style={gridCols(columns.length)}>
            {columns.map((col) => (
              <div key={col.id} className="border-r border-[var(--border)] last:border-r-0 text-center">
                {formatPaxTimeLine(col)}
              </div>
            ))}
          </div>
          {copyType === 'billing' && (
            <div className="grid border-b border-[var(--border-strong)] bg-[var(--order-cream)] copy-grid-meta font-bold" style={gridCols(columns.length)}>
              {columns.map((col) => (
                <div key={col.id} className="border-r border-[var(--border)] last:border-r-0 text-center">
                  {formatColumnAmount(col.amount) || '—'}
                </div>
              ))}
            </div>
          )}
          <div className="grid items-start" style={gridCols(columns.length)}>
            {columns.map((col) => {
              const items = dishesForColumn(col, menuItems, extras);
              return (
                <div key={col.id} className="px-4 py-4 border-r border-[var(--border)] last:border-r-0 align-top min-h-[100px]">
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
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
