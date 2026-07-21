import { useEffect, useState } from 'react';
import { Trash2 } from 'lucide-react';
import type { Dish, Enquiry, EnquiryDish } from '../../api/client';
import {
  addOrderDish,
  deleteOrderDish,
  formatCurrency,
  formatDate,
  updateEnquiry,
} from '../../api/client';
import { DishSearchSelect } from '../DishSearchSelect';
import { AmPmTimeInput } from '../AmPmTimeInput';
import { Button } from '../Layout';
import { serializeOrderNotes, toDateInputValue, type OrderExtras } from '../../utils/orderNotes';
import { DEFAULT_MEAL_TIMES } from '../../utils/mealSessions';
import { resolveSessionTabs } from '../../utils/mealSessions';
import {
  dishesForColumn,
  findOrCreateColumn,
  removeMenuColumn,
  resolveMenuColumns,
  sessionLabelOptions,
  stripMenuColumnsForSave,
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
  activeSession,
  dishes,
  onOrderUpdated,
  onDishesCatalogUpdated,
}: {
  order: Enquiry;
  extras: OrderExtras;
  menuItems: EnquiryDish[];
  activeSession: string;
  dishes: Dish[];
  onOrderUpdated: (order: Enquiry) => void;
  onDishesCatalogUpdated?: () => Promise<void>;
}) {
  const columns = resolveMenuColumns(extras, order, menuItems);
  const sessionColumns = columns.filter((c) => c.baseSession === activeSession);

  return (
    <div className="excel-menu-grid">
      {sessionColumns.length > 0 ? (
        <div className="excel-menu-stack">
          {sessionColumns.map((col) => (
            <SessionBlock
              key={col.id}
              column={col}
              columns={columns}
              extras={extras}
              menuItems={menuItems}
              order={order}
              dishes={dishes}
              onOrderUpdated={onOrderUpdated}
              onDishesCatalogUpdated={onDishesCatalogUpdated}
            />
          ))}
        </div>
      ) : (
        <EmptySessionCard
          order={order}
          extras={extras}
          columns={columns}
          activeSession={activeSession}
          onOrderUpdated={onOrderUpdated}
        />
      )}
      <p className="excel-menu-hint">
        Save the session first (date, pax, time), then add dishes to that session.
      </p>
    </div>
  );
}

function SessionBlock({
  column,
  columns,
  extras,
  menuItems,
  order,
  dishes,
  onOrderUpdated,
  onDishesCatalogUpdated,
}: {
  column: MenuColumn;
  columns: MenuColumn[];
  extras: OrderExtras;
  menuItems: EnquiryDish[];
  order: Enquiry;
  dishes: Dish[];
  onOrderUpdated: (order: Enquiry) => void;
  onDishesCatalogUpdated?: () => Promise<void>;
}) {
  const items = dishesForColumn(column, menuItems, extras);
  const [deleting, setDeleting] = useState(false);
  const [removed, setRemoved] = useState(false);

  async function removeSession() {
    const sessionLabel = `${column.sessionLabel} · ${formatDate(column.date)}`;
    const message =
      items.length > 0
        ? `Remove ${sessionLabel} and all ${items.length} dish item(s) in this session?`
        : `Remove ${sessionLabel}?`;
    if (!confirm(message)) return;

    setRemoved(true);
    setDeleting(true);
    try {
      if (items.length > 0) {
        await Promise.all(items.map((dish) => deleteOrderDish(order.id, dish.id)));
      }
      const merged = removeMenuColumn(extras, columns, column.id);
      const updated = await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
    } catch {
      setRemoved(false);
      alert('Could not remove this session. Please try again.');
    } finally {
      setDeleting(false);
    }
  }

  if (removed) return null;

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
          orderId={order.id}
          onOrderUpdated={onOrderUpdated}
        />
        <SessionTimeField
          column={column}
          columns={columns}
          extras={extras}
          orderId={order.id}
          onOrderUpdated={onOrderUpdated}
        />
      </div>

      <SessionAddDishForm
        order={order}
        column={column}
        dishes={dishes}
        onOrderUpdated={onOrderUpdated}
        onDishesCatalogUpdated={onDishesCatalogUpdated}
      />

      <div className="excel-session-dishes">
        {items.length === 0 ? (
          <p className="excel-session-empty">No dishes yet — search above and press Enter to add</p>
        ) : (
          <ul className="excel-dish-list">
            {items.map((d) => (
              <OrderMenuItem
                key={d.id}
                orderId={order.id}
                dish={d}
                sessionOptions={resolveSessionTabs(extras.customSessions, [
                  ...menuItems.map((m) => m.category),
                  ...(extras.menuColumns ?? []).map((c) => c.baseSession),
                  ...dishes.map((x) => x.category),
                ])}
                onUpdated={onOrderUpdated}
              />
            ))}
          </ul>
        )}
      </div>

      <footer className="excel-session-total">
        <SessionAmountField
          column={column}
          columns={columns}
          extras={extras}
          orderId={order.id}
          onOrderUpdated={onOrderUpdated}
        />
      </footer>
    </article>
  );
}

function EmptySessionCard({
  order,
  extras,
  columns,
  activeSession,
  onOrderUpdated,
}: {
  order: Enquiry;
  extras: OrderExtras;
  columns: MenuColumn[];
  activeSession: string;
  onOrderUpdated: (order: Enquiry) => void;
}) {
  const defaultDate = extras.scheduleDateFrom ?? toDateInputValue(order.eventDate);
  const defaultTimes = extras.mealSchedules?.[activeSession] ?? DEFAULT_MEAL_TIMES[activeSession] ?? {
    timeFrom: '',
    timeTo: '',
  };
  const [columnDate, setColumnDate] = useState(defaultDate);
  const [columnPax, setColumnPax] = useState('');
  const [sessionTimeFrom, setSessionTimeFrom] = useState(defaultTimes.timeFrom ?? '');
  const [sessionTimeTo, setSessionTimeTo] = useState(defaultTimes.timeTo ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    setColumnDate(extras.scheduleDateFrom ?? toDateInputValue(order.eventDate));
    const times = extras.mealSchedules?.[activeSession] ?? DEFAULT_MEAL_TIMES[activeSession] ?? {
      timeFrom: '',
      timeTo: '',
    };
    setSessionTimeFrom(times.timeFrom ?? '');
    setSessionTimeTo(times.timeTo ?? '');
    setColumnPax('');
    setError('');
  }, [activeSession, extras, order.eventDate]);

  async function saveSession() {
    setError('');
    if (!columnDate) {
      setError('Pick the service date for this session.');
      return;
    }
    const paxNum = columnPax.trim() ? Number(columnPax) : null;
    if (paxNum == null || Number.isNaN(paxNum) || paxNum < 1) {
      setError('Enter pax for this session (e.g. 100).');
      return;
    }
    const from = sessionTimeFrom.trim();
    const to = sessionTimeTo.trim();
    if ((from && !to) || (!from && to)) {
      setError('Enter both start and end time, or leave both empty.');
      return;
    }

    setSaving(true);
    try {
      const label = sessionLabelOptions(activeSession);
      const { columns: nextColumns } = findOrCreateColumn(columns, {
        date: columnDate,
        baseSession: activeSession,
        sessionLabel: label,
        pax: paxNum,
        timeFrom: from,
        timeTo: to,
      });
      const merged: OrderExtras = {
        ...extras,
        menuColumns: stripMenuColumnsForSave(nextColumns),
        mealSchedules: {
          ...(extras.mealSchedules ?? {}),
          [activeSession]: {
            timeFrom: from || null,
            timeTo: to || null,
          },
        },
      };
      const updated = await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
    } catch {
      setError('Could not save session. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="excel-session-block">
      <header className="excel-session-head">
        <p className="excel-session-date">{columnDate ? formatDate(columnDate) : 'Set date below'}</p>
        <h3 className="excel-session-title">{sessionLabelOptions(activeSession)}</h3>
      </header>

      <div className="excel-session-meta excel-session-meta--draft">
        <div className="excel-meta-field">
          <label className="excel-meta-label" htmlFor={`draft-date-${activeSession}`}>
            Date
          </label>
          <input
            id={`draft-date-${activeSession}`}
            type="date"
            value={columnDate}
            onChange={(e) => setColumnDate(e.target.value)}
            className="excel-meta-input excel-meta-input--date"
          />
        </div>
        <div className="excel-meta-field">
          <label className="excel-meta-label" htmlFor={`draft-pax-${activeSession}`}>
            Pax
          </label>
          <input
            id={`draft-pax-${activeSession}`}
            type="number"
            min={1}
            value={columnPax}
            onChange={(e) => setColumnPax(e.target.value)}
            placeholder="e.g. 100"
            className="excel-meta-input"
          />
        </div>
        <div className="excel-meta-field excel-meta-field--time">
          <span className="excel-meta-label">Time</span>
          <div className="excel-meta-time-row">
            <AmPmTimeInput
              value={sessionTimeFrom}
              onChange={setSessionTimeFrom}
              className="excel-meta-ampm"
              aria-label={`${activeSession} from`}
            />
            <span className="excel-meta-time-sep" aria-hidden>
              –
            </span>
            <AmPmTimeInput
              value={sessionTimeTo}
              onChange={setSessionTimeTo}
              className="excel-meta-ampm"
              aria-label={`${activeSession} to`}
            />
          </div>
        </div>
      </div>

      <div className="excel-session-save">
        <Button
          type="button"
          onClick={() => void saveSession()}
          disabled={saving}
          className="!py-2.5 !px-5 text-sm"
        >
          {saving ? 'Saving…' : 'Save session'}
        </Button>
        <p className="excel-session-empty">
          Save this session first. You can add dishes after it appears.
        </p>
        {error && <p className="excel-session-add-error">{error}</p>}
      </div>
    </article>
  );
}

function SessionAddDishForm({
  order,
  column,
  dishes,
  onOrderUpdated,
  onDishesCatalogUpdated,
}: {
  order: Enquiry;
  column: MenuColumn;
  dishes: Dish[];
  onOrderUpdated: (order: Enquiry) => void;
  onDishesCatalogUpdated?: () => Promise<void>;
}) {
  const [dishId, setDishId] = useState('');
  const [customDishName, setCustomDishName] = useState('');
  const [saveToCatalog, setSaveToCatalog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleAdd(opts?: { dishIdOverride?: string; dishNameOverride?: string }) {
    setError('');
    const resolvedDishId = opts?.dishIdOverride ?? dishId;
    const customName = (opts?.dishNameOverride ?? customDishName).trim();
    if (!resolvedDishId && !customName) {
      setError('Select a menu item or type a dish name.');
      return;
    }

    setSaving(true);
    try {
      const updated = await addOrderDish(order.id, {
        ...(resolvedDishId
          ? { dishId: resolvedDishId }
          : { dishName: customName, saveToCatalog }),
        category: column.baseSession,
        menuColumnId: column.id,
      });

      setDishId('');
      setCustomDishName('');
      onOrderUpdated(updated);

      // Catalog refresh can wait — don't block the UI
      if (customName && saveToCatalog) {
        void onDishesCatalogUpdated?.();
      }
    } catch {
      setError('Could not add item.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="excel-session-add">
      <DishSearchSelect
        dishes={dishes}
        value={dishId}
        customName={customDishName}
        onChange={setDishId}
        onCustomNameChange={setCustomDishName}
        onConfirmCustom={(name) => {
          void handleAdd({ dishNameOverride: name });
        }}
        onConfirmDish={(d) => {
          void handleAdd({ dishIdOverride: d.id });
        }}
      />
      <div className="excel-session-add-actions">
        <Button
          type="button"
          onClick={() => void handleAdd()}
          disabled={saving || (!dishId && !customDishName.trim())}
          className="!py-2 !px-4 text-sm"
        >
          {saving ? 'Adding…' : 'Add dish'}
        </Button>
      </div>
      {!!customDishName.trim() && !dishId && (
        <label className="excel-session-add-catalog flex items-center gap-2 text-sm text-[var(--foreground)] cursor-pointer">
          <input
            type="checkbox"
            checked={saveToCatalog}
            onChange={(e) => setSaveToCatalog(e.target.checked)}
            className="rounded border-[var(--border)]"
          />
          Also save this dish to the menu catalog
        </label>
      )}
      {error && <p className="excel-session-add-error">{error}</p>}
    </div>
  );
}

function SessionPaxField({
  column,
  columns,
  extras,
  orderId,
  onOrderUpdated,
}: {
  column: MenuColumn;
  columns: MenuColumn[];
  extras: OrderExtras;
  orderId: string;
  onOrderUpdated: (order: Enquiry) => void;
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
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
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
  onOrderUpdated,
}: {
  column: MenuColumn;
  columns: MenuColumn[];
  extras: OrderExtras;
  orderId: string;
  onOrderUpdated: (order: Enquiry) => void;
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
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
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
        <AmPmTimeInput
          id={`time-from-${column.id}`}
          value={timeFrom}
          onChange={setTimeFrom}
          onBlur={handleBlur}
          disabled={saving}
          className="excel-meta-ampm"
          aria-label={`Start time for ${column.sessionLabel}`}
        />
        <span className="excel-meta-time-sep" aria-hidden>
          –
        </span>
        <AmPmTimeInput
          id={`time-to-${column.id}`}
          value={timeTo}
          onChange={setTimeTo}
          onBlur={handleBlur}
          disabled={saving}
          className="excel-meta-ampm"
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
  onOrderUpdated,
}: {
  column: MenuColumn;
  columns: MenuColumn[];
  extras: OrderExtras;
  orderId: string;
  onOrderUpdated: (order: Enquiry) => void;
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
      const updated = await updateEnquiry(orderId, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
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
