import { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
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
import {
  eventDatesForStyles,
  expandScheduleDateRange,
  serializeOrderNotes,
  toDateInputValue,
  type OrderExtras,
} from '../../utils/orderNotes';
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
  sessionTabs,
  dishes,
  onOrderUpdated,
  onDishesCatalogUpdated,
  onAddCustomSession,
  customSessionName,
  onCustomSessionNameChange,
  addingCustomSession,
  onAddingCustomSessionChange,
  customSessionSaving,
}: {
  order: Enquiry;
  extras: OrderExtras;
  menuItems: EnquiryDish[];
  sessionTabs: { id: string; label: string }[];
  dishes: Dish[];
  onOrderUpdated: (order: Enquiry) => void;
  onDishesCatalogUpdated?: () => Promise<void>;
  onAddCustomSession: () => void | Promise<void>;
  customSessionName: string;
  onCustomSessionNameChange: (value: string) => void;
  addingCustomSession: boolean;
  onAddingCustomSessionChange: (value: boolean) => void;
  customSessionSaving: boolean;
}) {
  const columns = resolveMenuColumns(extras, order, menuItems);
  const columnsByDate = useMemo(() => {
    const map = new Map<string, MenuColumn[]>();
    for (const col of columns) {
      const list = map.get(col.date) ?? [];
      list.push(col);
      map.set(col.date, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [columns]);

  return (
    <div className="excel-menu-grid">
      <SessionBatchCreator
        order={order}
        extras={extras}
        columns={columns}
        sessionTabs={sessionTabs}
        onOrderUpdated={onOrderUpdated}
        onAddCustomSession={onAddCustomSession}
        customSessionName={customSessionName}
        onCustomSessionNameChange={onCustomSessionNameChange}
        addingCustomSession={addingCustomSession}
        onAddingCustomSessionChange={onAddingCustomSessionChange}
        customSessionSaving={customSessionSaving}
      />

      {columns.length > 0 && (
        <div className="excel-saved-sessions">
          <h4 className="excel-saved-sessions-title">
            Saved sessions ({columns.length})
          </h4>
          <div className="excel-menu-stack">
            {columnsByDate.map(([date, dayColumns]) => (
              <div key={date} className="space-y-3">
                <p className="text-xs font-bold uppercase tracking-wide text-[var(--primary)] px-1">
                  {formatDate(date)}
                </p>
                {dayColumns.map((col) => (
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
            ))}
          </div>
        </div>
      )}

      <p className="excel-menu-hint">
        For a 3-day event: choose Day 1, select Lunch + Dinner together, create them, then add dishes and times.
        Switch to Day 2 / Day 3 and repeat.
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
  const items = dishesForColumn(column, menuItems, extras, columns);
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
    <article id={`session-block-${column.id}`} className="excel-session-block">
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
        <SessionTimeField
          column={column}
          columns={columns}
          extras={extras}
          orderId={order.id}
          onOrderUpdated={onOrderUpdated}
        />
        <SessionPaxField
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
        sessionItems={items}
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

function SessionBatchCreator({
  order,
  extras,
  columns,
  sessionTabs,
  onOrderUpdated,
  onAddCustomSession,
  customSessionName,
  onCustomSessionNameChange,
  addingCustomSession,
  onAddingCustomSessionChange,
  customSessionSaving,
}: {
  order: Enquiry;
  extras: OrderExtras;
  columns: MenuColumn[];
  sessionTabs: { id: string; label: string }[];
  onOrderUpdated: (order: Enquiry) => void;
  onAddCustomSession: () => void | Promise<void>;
  customSessionName: string;
  onCustomSessionNameChange: (value: string) => void;
  addingCustomSession: boolean;
  onAddingCustomSessionChange: (value: boolean) => void;
  customSessionSaving: boolean;
}) {
  const eventDays = useMemo(() => {
    const scheduled = expandScheduleDateRange(extras);
    if (scheduled.length > 0) return scheduled;
    return eventDatesForStyles(extras, order.eventDate);
  }, [extras, order.eventDate]);
  const defaultDate = eventDays[0] ?? extras.scheduleDateFrom ?? toDateInputValue(order.eventDate) ?? '';
  const [columnDate, setColumnDate] = useState(defaultDate);
  const [selectedSessions, setSelectedSessions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const alreadyOnDate = useMemo(() => {
    const set = new Set<string>();
    for (const col of columns) {
      if (col.date === columnDate) set.add(col.baseSession);
    }
    return set;
  }, [columns, columnDate]);

  useEffect(() => {
    const preferred = eventDays[0] ?? '';
    setColumnDate((current) => (current && eventDays.includes(current) ? current : preferred));
    setError('');
  }, [eventDays]);

  useEffect(() => {
    setSelectedSessions((current) => current.filter((id) => !alreadyOnDate.has(id)));
  }, [columnDate, alreadyOnDate]);

  function toggleSession(sessionId: string) {
    if (alreadyOnDate.has(sessionId)) return;
    setSelectedSessions((current) =>
      current.includes(sessionId) ? current.filter((id) => id !== sessionId) : [...current, sessionId],
    );
  }

  async function saveSessions() {
    setError('');
    if (!columnDate) {
      setError('Pick the service date for these sessions.');
      return;
    }
    if (selectedSessions.length === 0) {
      setError('Select at least one session to create for this day.');
      return;
    }

    setSaving(true);
    try {
      let nextColumns = columns;
      for (const sessionId of selectedSessions) {
        const label = sessionLabelOptions(sessionId);
        nextColumns = findOrCreateColumn(nextColumns, {
          date: columnDate,
          baseSession: sessionId,
          sessionLabel: label,
          pax: null,
          timeFrom: '',
          timeTo: '',
        }).columns;
      }
      const merged: OrderExtras = {
        ...extras,
        menuColumns: stripMenuColumnsForSave(nextColumns),
        scheduleDateFrom: extras.scheduleDateFrom || columnDate,
        scheduleDateTo: extras.scheduleDateTo || columnDate,
      };
      const updated = await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });
      onOrderUpdated(updated);
      setSelectedSessions([]);
      setError('');
    } catch {
      setError('Could not create sessions. Please try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <article className="excel-session-block excel-session-block--active">
      <header className="excel-session-head">
        <p className="excel-session-date">{columnDate ? formatDate(columnDate) : 'Choose a day'}</p>
        <h3 className="excel-session-title">Create sessions for a day</h3>
      </header>

      <div className="excel-session-meta excel-session-meta--draft flex-col !items-stretch gap-4">
        <div className="excel-meta-field w-full">
          <span className="excel-meta-label">Event day</span>
          <div className="flex flex-wrap gap-2 mt-1">
            {eventDays.map((day, index) => {
              const chosen = columnDate === day;
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => setColumnDate(day)}
                  className={`order-session-tab ${chosen ? 'order-session-tab--active' : ''}`}
                >
                  Day {index + 1} · {formatDate(day)}
                </button>
              );
            })}
          </div>
          <div className="mt-2">
            <label className="excel-meta-label" htmlFor="draft-session-date">
              Or pick another date
            </label>
            <input
              id="draft-session-date"
              type="date"
              value={columnDate}
              onChange={(e) => setColumnDate(e.target.value)}
              className="excel-meta-input excel-meta-input--date mt-1"
            />
          </div>
        </div>

        <div className="excel-meta-field w-full">
          <span className="excel-meta-label">Sessions for this day (select multiple)</span>
          <div className="flex flex-wrap gap-2 mt-1">
            {sessionTabs.map((session) => {
              const exists = alreadyOnDate.has(session.id);
              const chosen = selectedSessions.includes(session.id);
              return (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => toggleSession(session.id)}
                  disabled={exists}
                  title={exists ? 'Already created for this day' : `Add ${session.label}`}
                  className={`order-session-tab ${chosen ? 'order-session-tab--active' : ''} ${exists ? 'order-session-tab--saved opacity-70' : ''}`}
                >
                  {exists ? `✓ ${session.label}` : session.label}
                </button>
              );
            })}
            {!addingCustomSession ? (
              <button
                type="button"
                onClick={() => onAddingCustomSessionChange(true)}
                className="order-session-tab order-session-tab--add"
              >
                <Plus size={14} /> Custom session
              </button>
            ) : (
              <div className="order-session-add-form">
                <input
                  autoFocus
                  value={customSessionName}
                  onChange={(e) => onCustomSessionNameChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void onAddCustomSession();
                    if (e.key === 'Escape') {
                      onAddingCustomSessionChange(false);
                      onCustomSessionNameChange('');
                    }
                  }}
                  placeholder="e.g. High Tea"
                  className="order-session-add-input"
                  maxLength={40}
                />
                <button
                  type="button"
                  onClick={() => void onAddCustomSession()}
                  disabled={customSessionSaving || !customSessionName.trim()}
                  className="order-session-tab order-session-tab--active"
                >
                  {customSessionSaving ? '…' : 'Add'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onAddingCustomSessionChange(false);
                    onCustomSessionNameChange('');
                  }}
                  className="order-session-tab"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="excel-session-save">
        <Button
          type="button"
          onClick={() => void saveSessions()}
          disabled={saving || selectedSessions.length === 0}
          className="!py-2.5 !px-5 text-sm"
        >
          {saving
            ? 'Creating…'
            : selectedSessions.length > 1
              ? `Create ${selectedSessions.length} sessions for this day`
              : selectedSessions.length === 1
                ? 'Create 1 session for this day'
                : 'Select sessions to create'}
        </Button>
        <p className="excel-session-empty">
          Example: Day 1 → select Lunch + Dinner → Create. Then open each saved block below to add dishes, pax, and time.
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
  sessionItems,
  onOrderUpdated,
  onDishesCatalogUpdated,
}: {
  order: Enquiry;
  column: MenuColumn;
  dishes: Dish[];
  sessionItems: EnquiryDish[];
  onOrderUpdated: (order: Enquiry) => void;
  onDishesCatalogUpdated?: () => Promise<void>;
}) {
  const [dishId, setDishId] = useState('');
  const [customDishName, setCustomDishName] = useState('');
  const [saveToCatalog, setSaveToCatalog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const usedCatalogIds = new Set(
    sessionItems.map((d) => d.dishId).filter((id): id is string => Boolean(id)),
  );
  const usedNames = new Set(sessionItems.map((d) => d.dishName.trim().toLowerCase()).filter(Boolean));

  const availableDishes = dishes.filter((d) => {
    if (usedCatalogIds.has(d.id)) return false;
    if (usedNames.has(d.name.trim().toLowerCase())) return false;
    return true;
  });

  function isAlreadyInSession(opts: { dishId?: string; dishName?: string }): boolean {
    if (opts.dishId && usedCatalogIds.has(opts.dishId)) return true;
    const name = opts.dishName?.trim().toLowerCase();
    if (name && usedNames.has(name)) return true;
    if (opts.dishId) {
      const catalog = dishes.find((d) => d.id === opts.dishId);
      if (catalog && usedNames.has(catalog.name.trim().toLowerCase())) return true;
    }
    return false;
  }

  async function handleAdd(opts?: { dishIdOverride?: string; dishNameOverride?: string }) {
    setError('');
    const resolvedDishId = opts?.dishIdOverride ?? dishId;
    const customName = (opts?.dishNameOverride ?? customDishName).trim();
    if (!resolvedDishId && !customName) {
      setError('Select a menu item or type a dish name.');
      return;
    }

    if (
      isAlreadyInSession({
        dishId: resolvedDishId || undefined,
        dishName: customName || undefined,
      })
    ) {
      setError('This dish is already in this session.');
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
      <div className="excel-session-add-row">
        <DishSearchSelect
          dishes={availableDishes}
          value={dishId}
          customName={customDishName}
          sessionCategory={column.baseSession}
          blockedNames={[...usedNames]}
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
          onChange={(next) => {
            setTimeFrom(next);
            void saveTime(next, timeTo);
          }}
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
          onChange={(next) => {
            setTimeTo(next);
            void saveTime(timeFrom, next);
          }}
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
        Client: {order.customerName}
        {order.eventType ? ` · ${order.eventType}` : ''}
      </p>
      {order.eventLocation ? <p>{order.eventLocation}</p> : null}
    </div>
  );
}
