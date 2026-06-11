import { useEffect, useState } from 'react';
import type { Enquiry, EnquiryDish } from '../../api/client';
import { formatCurrency, formatDate, updateEnquiry } from '../../api/client';
import { formatScheduleTime, serializeOrderNotes, type OrderExtras } from '../../utils/orderNotes';
import {
  dishesForColumn,
  resolveMenuColumns,
  updateColumnAmount,
  updateColumnPax,
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
        No menu items yet. Choose a session, set date and time, then add dishes.
      </p>
    );
  }

  return (
    <div className="excel-menu-grid -mx-2 px-2">
      <div className="space-y-6">
        {columns.map((col) => (
          <SessionBlock
            key={col.id}
            column={col}
            columns={columns}
            extras={extras}
            menuItems={menuItems}
            orderId={order.id}
            onRefresh={onRefresh}
          />
        ))}
      </div>
      <p className="text-xs text-[var(--muted)] mt-4">
        Each meal session stacks below the previous one. After all dishes are added, enter the session total at the bottom of that block.
      </p>
    </div>
  );
}

function SessionBlock({
  column,
  columns,
  extras,
  menuItems,
  orderId,
  onRefresh,
}: {
  column: MenuColumn;
  columns: MenuColumn[];
  extras: OrderExtras;
  menuItems: EnquiryDish[];
  orderId: string;
  onRefresh: () => void;
}) {
  const items = dishesForColumn(column, menuItems, extras);

  return (
    <div className="border border-[var(--border-strong)] rounded-lg overflow-hidden bg-[var(--card)] excel-session-block">
      <div className="excel-session-date">{formatDate(column.date)}</div>
      <div className="excel-session-label">{column.sessionLabel}</div>
      <div className="excel-session-meta">
        <SessionPaxField
          column={column}
          columns={columns}
          extras={extras}
          orderId={orderId}
          onRefresh={onRefresh}
        />
        {column.timeFrom && column.timeTo && (
          <p className="text-sm font-bold text-[var(--foreground)]">
            {formatScheduleTime(column.timeFrom)} – {formatScheduleTime(column.timeTo)}
          </p>
        )}
      </div>
      <div className="excel-session-dishes">
        {items.length === 0 ? (
          <p className="text-sm text-[var(--muted)] italic text-center py-6">No dishes yet for this session</p>
        ) : (
          <ul>
            {items.map((d) => (
              <OrderMenuItem key={d.id} orderId={orderId} dish={d} onUpdated={onRefresh} />
            ))}
          </ul>
        )}
      </div>
      {items.length > 0 && (
        <div className="excel-session-total">
          <SessionAmountField
            column={column}
            columns={columns}
            extras={extras}
            orderId={orderId}
            onRefresh={onRefresh}
          />
        </div>
      )}
    </div>
  );
}

function SessionPaxField({
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
  const [value, setValue] = useState(column.pax != null ? String(column.pax) : '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setValue(column.pax != null ? String(column.pax) : '');
  }, [column.pax]);

  async function savePax() {
    const trimmed = value.trim();
    const parsed = trimmed ? Number(trimmed.replace(/,/g, '')) : null;
    if (parsed != null && (Number.isNaN(parsed) || parsed < 1)) return;
    if (parsed === column.pax || (parsed == null && column.pax == null)) return;

    setSaving(true);
    try {
      const merged = updateColumnPax(extras, columns, column.id, parsed);
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="min-w-[120px]">
      <label className="block text-xs uppercase tracking-wide text-[var(--order-accent)] font-semibold mb-1">
        Pax
      </label>
      <input
        type="number"
        min={1}
        step={1}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={savePax}
        onKeyDown={(e) => {
          if (e.key === 'Enter') e.currentTarget.blur();
        }}
        disabled={saving}
        placeholder="e.g. 60"
        className="form-input w-full px-3 py-2 rounded text-base font-bold text-center"
      />
    </div>
  );
}

function SessionAmountField({
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
    <div className="max-w-xs mx-auto">
      <label className="block text-xs uppercase tracking-wide text-[var(--order-accent)] font-semibold mb-1.5 text-center">
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
          if (e.key === 'Enter') e.currentTarget.blur();
        }}
        disabled={saving}
        placeholder="e.g. 15000"
        className="form-input w-full px-3 py-2 rounded text-base font-bold text-center"
      />
      {column.amount != null && column.amount > 0 && (
        <p className="text-sm text-[var(--primary)] font-semibold text-center mt-2">
          {formatCurrency(column.amount)}
        </p>
      )}
    </div>
  );
}

export function OrderExcelHeader({ order }: { order: Enquiry }) {
  return (
    <div className="order-client-header">
      <p>
        Client : {order.customerName}
        {order.eventType ? ` · ${order.eventType}` : ''}
      </p>
      <p>{order.eventLocation}</p>
    </div>
  );
}
