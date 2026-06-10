import type { Enquiry, EnquiryDish } from '../../api/client';
import { formatDate } from '../../api/client';
import type { OrderExtras } from '../../utils/orderNotes';
import {
  dishesForColumn,
  formatPaxTimeLine,
  resolveMenuColumns,
  type MenuColumn,
} from '../../utils/orderMenuGrid';
import { OrderMenuItem } from './OrderMenuItem';

export function OrderExcelMenuGrid({
  order,
  extras,
  menuItems,
  onRefresh,
}: {
  order: Enquiry;
  extras: OrderExtras;
  menuItems: EnquiryDish[];
  onRefresh: () => void;
}) {
  const columns = resolveMenuColumns(extras, order, menuItems);

  if (columns.length === 0) {
    return (
      <p className="text-center text-[var(--muted)] py-10 text-sm">
        No menu items yet. Choose a session, set date and time, then add dishes — columns appear like the Excel menu sheet.
      </p>
    );
  }

  return (
    <div className="excel-menu-grid overflow-x-auto -mx-2 px-2">
      <div className="min-w-max border border-[var(--border-strong)] rounded-lg overflow-hidden bg-[var(--card)]">
        <div className="grid border-b border-[var(--border-strong)] bg-[var(--table-header-bg)]" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(200px, 1fr))` }}>
          {columns.map((col) => (
            <div key={col.id} className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 text-center">
              <p className="text-xs font-bold text-[var(--foreground)]">{formatDate(col.date)}</p>
            </div>
          ))}
        </div>
        <div className="grid border-b border-[var(--border-strong)]" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(200px, 1fr))` }}>
          {columns.map((col) => (
            <ColumnHeader key={col.id} column={col} />
          ))}
        </div>
        <div className="grid border-b border-[var(--border)] bg-[var(--background-alt)]" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(200px, 1fr))` }}>
          {columns.map((col) => (
            <div key={col.id} className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 text-center">
              <p className="text-xs font-bold text-[var(--foreground)] leading-snug">
                {formatPaxTimeLine(col) || 'Set pax & time when adding items'}
              </p>
            </div>
          ))}
        </div>
        <div className="grid items-start" style={{ gridTemplateColumns: `repeat(${columns.length}, minmax(200px, 1fr))` }}>
          {columns.map((col) => (
            <ColumnDishes
              key={col.id}
              column={col}
              items={dishesForColumn(col, menuItems, extras)}
              orderId={order.id}
              onUpdated={onRefresh}
            />
          ))}
        </div>
      </div>
      <p className="text-[10px] text-[var(--muted)] mt-3">
        Layout matches wedding menu Excel: client and venue above, then date → session → pax/time → dish list per column.
      </p>
    </div>
  );
}

function ColumnHeader({ column }: { column: MenuColumn }) {
  return (
    <div className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 text-center min-h-[3rem] flex items-center justify-center">
      <p className="text-xs font-bold text-[var(--foreground)] leading-snug">{column.sessionLabel}</p>
    </div>
  );
}

function ColumnDishes({
  items,
  orderId,
  onUpdated,
}: {
  column: MenuColumn;
  items: EnquiryDish[];
  orderId: string;
  onUpdated: () => void;
}) {
  return (
    <div className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 min-h-[120px] align-top">
      {items.length === 0 ? (
        <p className="text-[10px] text-[var(--muted)] italic">—</p>
      ) : (
        <ul>
          {items.map((d) => (
            <OrderMenuItem key={d.id} orderId={orderId} dish={d} onUpdated={onUpdated} />
          ))}
        </ul>
      )}
    </div>
  );
}

export function OrderExcelHeader({ order }: { order: Enquiry }) {
  return (
    <div className="mb-6 space-y-1 border-b border-[var(--border)] pb-4">
      <p className="text-sm font-bold text-[var(--foreground)]">
        Client : {order.customerName}
        {order.eventType ? ` · ${order.eventType}` : ''}
      </p>
      <p className="text-sm font-bold text-[var(--foreground)]">{order.eventLocation}</p>
    </div>
  );
}
