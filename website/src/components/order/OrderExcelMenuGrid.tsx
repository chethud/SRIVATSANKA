import { useEffect, useState } from 'react';
import type { Enquiry, EnquiryDish } from '../../api/client';
import { formatCurrency, formatDate, updateEnquiry } from '../../api/client';
import { serializeOrderNotes, type OrderExtras } from '../../utils/orderNotes';
import {
  dishesForColumn,
  formatPaxTimeLine,
  resolveMenuColumns,
  updateColumnAmount,
  type MenuColumn,
} from '../../utils/orderMenuGrid';
import { OrderMenuItem } from './OrderMenuItem';

const gridCols = (count: number) =>
  ({ gridTemplateColumns: `repeat(${count}, minmax(240px, 1fr))` }) as const;

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
        <div className="grid border-b border-[var(--border-strong)] bg-[var(--table-header-bg)]" style={gridCols(columns.length)}>
          {columns.map((col) => (
            <div key={col.id} className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 text-center">
              <p className="text-sm font-bold text-[var(--foreground)]">{formatDate(col.date)}</p>
            </div>
          ))}
        </div>
        <div className="grid border-b border-[var(--border-strong)]" style={gridCols(columns.length)}>
          {columns.map((col) => (
            <ColumnHeader key={col.id} column={col} />
          ))}
        </div>
        <div className="grid border-b border-[var(--border)] bg-[var(--background-alt)]" style={gridCols(columns.length)}>
          {columns.map((col) => (
            <div key={col.id} className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 text-center">
              <p className="text-sm font-bold text-[var(--foreground)] leading-snug">
                {formatPaxTimeLine(col) || 'Set pax & time when adding items'}
              </p>
            </div>
          ))}
        </div>
        <div className="grid border-b border-[var(--border-strong)] bg-[var(--order-cream)]" style={gridCols(columns.length)}>
          {columns.map((col) => (
            <ColumnAmountCell
              key={col.id}
              column={col}
              columns={columns}
              extras={extras}
              orderId={order.id}
              onRefresh={onRefresh}
            />
          ))}
        </div>
        <div className="grid items-start" style={gridCols(columns.length)}>
          {columns.map((col) => (
            <ColumnDishes
              key={col.id}
              items={dishesForColumn(col, menuItems, extras)}
              orderId={order.id}
              onUpdated={onRefresh}
            />
          ))}
        </div>
      </div>
      <p className="text-xs text-[var(--muted)] mt-3">
        After adding all dishes for a session, enter the session total amount in that column (e.g. total for breakfast, total for lunch).
      </p>
    </div>
  );
}

function ColumnHeader({ column }: { column: MenuColumn }) {
  return (
    <div className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 text-center min-h-[3rem] flex items-center justify-center">
      <p className="text-sm font-bold text-[var(--foreground)] leading-snug">{column.sessionLabel}</p>
    </div>
  );
}

function ColumnAmountCell({
  column,
  columns,
  extras,
  orderId,
  onRefresh,
}: {
  column: MenuColumn;
  columns: MenuColumn[];
  extras: OrderExtras;
  orderId: string;
  onRefresh: () => void;
}) {
  const [value, setValue] = useState(column.amount != null ? String(column.amount) : '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setValue(column.amount != null ? String(column.amount) : '');
  }, [column.amount]);

  async function saveAmount() {
    const trimmed = value.trim();
    const parsed = trimmed ? Number(trimmed.replace(/,/g, '')) : null;
    if (parsed != null && (Number.isNaN(parsed) || parsed < 0)) return;
    if (parsed === column.amount || (parsed == null && column.amount == null)) return;

    setSaving(true);
    try {
      const merged = updateColumnAmount(extras, columns, column.id, parsed);
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="px-3 py-2 border-r border-[var(--border)] last:border-r-0">
      <label className="block text-[10px] uppercase tracking-wide text-[var(--order-accent)] font-semibold mb-1">
        Session total
      </label>
      <input
        type="number"
        min={0}
        step={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={saveAmount}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.currentTarget.blur();
          }
        }}
        disabled={saving}
        placeholder="e.g. 15000"
        className="form-input w-full px-2 py-1.5 rounded text-sm font-bold text-center"
      />
      {column.amount != null && column.amount > 0 && (
        <p className="text-xs text-[var(--primary)] font-semibold text-center mt-1">
          {formatCurrency(column.amount)}
        </p>
      )}
    </div>
  );
}

function ColumnDishes({
  items,
  orderId,
  onUpdated,
}: {
  items: EnquiryDish[];
  orderId: string;
  onUpdated: () => void;
}) {
  return (
    <div className="px-3 py-2 border-r border-[var(--border)] last:border-r-0 min-h-[120px] align-top">
      {items.length === 0 ? (
        <p className="text-xs text-[var(--muted)] italic">—</p>
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
      <p className="text-base font-bold text-[var(--foreground)]">
        Client : {order.customerName}
        {order.eventType ? ` · ${order.eventType}` : ''}
      </p>
      <p className="text-base font-bold text-[var(--foreground)]">{order.eventLocation}</p>
    </div>
  );
}
