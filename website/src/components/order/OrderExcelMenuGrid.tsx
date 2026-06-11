import { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { Enquiry, EnquiryDish } from '../../api/client';
import { deleteOrderDish, formatCurrency, formatDate, updateEnquiry } from '../../api/client';
import { serializeOrderNotes, type OrderExtras } from '../../utils/orderNotes';
import {
  dishesForColumn,
  removeMenuColumn,
  resolveMenuColumns,
  updateColumnAmount,
  updateColumnPax,
  updateColumnTime,
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
    <div className="excel-menu-grid">
      <div className="excel-menu-stack">
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
      <p className="excel-menu-hint">
        Each meal session stacks below the previous one. Enter the session total after all dishes are added.
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
  const [deleting, setDeleting] = useState(false);

  async function removeSession() {
    const sessionLabel = `${column.sessionLabel} · ${formatDate(column.date)}`;
    const message =
      items.length > 0
        ? `Remove ${sessionLabel} and all ${items.length} dish item(s) in this session?`
        : `Remove ${sessionLabel}?`;
    if (!confirm(message)) return;

    setDeleting(true);
    try {
      for (const dish of items) {
        await deleteOrderDish(orderId, dish.id);
      }
      const merged = removeMenuColumn(extras, columns, column.id);
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } catch {
      alert('Could not remove this session. Please try again.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <article className="excel-session-block">
      <header className="excel-session-head">
        <button
          type="button"
          onClick={() => void removeSession()}
          disabled={deleting}
          className="excel-session-delete"
          title="Remove session"
          aria-label={`Remove ${column.sessionLabel} session`}
        >
          <Trash2 size={15} />
        </button>
        <p className="excel-session-date">{formatDate(column.date)}</p>
        <h3 className="excel-session-title">{column.sessionLabel}</h3>
      </header>

      <div className="excel-session-meta">
        <SessionPaxField
          column={column}
          columns={columns}
          extras={extras}
          orderId={orderId}
          onRefresh={onRefresh}
        />
        <SessionTimeField
          column={column}
          columns={columns}
          extras={extras}
          orderId={orderId}
          onRefresh={onRefresh}
        />
      </div>

      <div className="excel-session-dishes">
        {items.length === 0 ? (
          <p className="excel-session-empty">No dishes yet for this session</p>
        ) : (
          <ul className="excel-dish-list">
            {items.map((d) => (
              <OrderMenuItem key={d.id} orderId={orderId} dish={d} onUpdated={onRefresh} />
            ))}
          </ul>
        )}
      </div>

      {items.length > 0 && (
        <footer className="excel-session-total">
          <SessionAmountField
            column={column}
            columns={columns}
            extras={extras}
            orderId={orderId}
            onRefresh={onRefresh}
          />
        </footer>
      )}
    </article>
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
    <div className="excel-meta-field">
      <label className="excel-meta-label" htmlFor={`pax-${column.id}`}>
        Pax
      </label>
      <input
        id={`pax-${column.id}`}
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
        placeholder="—"
        className="excel-meta-input"
      />
    </div>
  );
}

function SessionTimeField({
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
  const [timeFrom, setTimeFrom] = useState(column.timeFrom ?? '');
  const [timeTo, setTimeTo] = useState(column.timeTo ?? '');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setTimeFrom(column.timeFrom ?? '');
    setTimeTo(column.timeTo ?? '');
  }, [column.timeFrom, column.timeTo]);

  async function saveTime(nextFrom: string, nextTo: string) {
    const from = nextFrom.trim() || null;
    const to = nextTo.trim() || null;
    if (from === column.timeFrom && to === column.timeTo) return;
    if ((from && !to) || (!from && to)) return;

    setSaving(true);
    try {
      const merged = updateColumnTime(extras, columns, column.id, from, to);
      await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  function handleBlur() {
    void saveTime(timeFrom, timeTo);
  }

  return (
    <div className="excel-meta-field excel-meta-field--time">
      <span className="excel-meta-label">Time</span>
      <div className="excel-meta-time-row">
        <input
          id={`time-from-${column.id}`}
          type="time"
          value={timeFrom}
          onChange={(e) => setTimeFrom(e.target.value)}
          onBlur={handleBlur}
          disabled={saving}
          className="excel-meta-time-input"
          aria-label={`Start time for ${column.sessionLabel}`}
        />
        <span className="excel-meta-time-sep" aria-hidden>
          –
        </span>
        <input
          id={`time-to-${column.id}`}
          type="time"
          value={timeTo}
          onChange={(e) => setTimeTo(e.target.value)}
          onBlur={handleBlur}
          disabled={saving}
          className="excel-meta-time-input"
          aria-label={`End time for ${column.sessionLabel}`}
        />
      </div>
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
  const [rawValue, setRawValue] = useState(column.amount != null ? String(column.amount) : '');
  const [focused, setFocused] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setRawValue(column.amount != null ? String(column.amount) : '');
  }, [column.amount]);

  const displayValue = focused
    ? rawValue
    : rawValue.trim() && !Number.isNaN(Number(rawValue.replace(/,/g, '')))
      ? formatCurrency(Number(rawValue.replace(/,/g, '')))
      : rawValue;

  async function saveAmount() {
    const trimmed = rawValue.trim();
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

  function handleChange(next: string) {
    setRawValue(next.replace(/[^\d]/g, ''));
  }

  function handleFocus() {
    setFocused(true);
  }

  function handleBlur() {
    setFocused(false);
    void saveAmount();
  }

  return (
    <div className="excel-session-amount">
      <label className="excel-meta-label" htmlFor={`amount-${column.id}`}>
        Session total
      </label>
      <div className="excel-session-amount-wrap">
        {!focused && displayValue.startsWith('₹') ? null : (
          <span className="excel-session-amount-prefix" aria-hidden>
            ₹
          </span>
        )}
        <input
          id={`amount-${column.id}`}
          type="text"
          inputMode="numeric"
          value={displayValue}
          onChange={(e) => handleChange(e.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={(e) => {
            if (e.key === 'Enter') e.currentTarget.blur();
          }}
          disabled={saving}
          placeholder="Enter amount"
          className="excel-session-amount-input"
        />
      </div>
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
