import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, ChefHat, Clock, MapPin, Phone, Plus, Pencil, FileText, UtensilsCrossed, Calendar,
} from 'lucide-react';
import type { Dish, Enquiry, EnquiryDish, Worker } from '../../api/client';
import {
  addOrderDish,
  formatDate,
  formatDateTime,
  updateEnquiry,
} from '../../api/client';
import { DishSearchSelect } from '../DishSearchSelect';
import { Button } from '../Layout';
import { OrderDispatchSection } from './OrderDispatchSection';
import { OrderExtrasSection } from './OrderExtrasSection';
import { OrderRegionalStyleSection } from './OrderRegionalStyleSection';
import { OrderExcelHeader, OrderExcelMenuGrid } from './OrderExcelMenuGrid';
import {
  formatOrderId,
  formatMealTimeRange,
  groupMenuItems,
  mealSchedulesForSave,
  parseOrderNotes,
  serializeOrderNotes,
  statusLabel,
  toDateInputValue,
  type OrderExtras,
} from '../../utils/orderNotes';
import { MEAL_SESSIONS, PREFERENCE_CATEGORIES } from '../../utils/mealSessions';
import {
  assignDishColumn,
  findOrCreateColumn,
  resolveMenuColumns,
  sessionLabelOptions,
  stripMenuColumnsForSave,
} from '../../utils/orderMenuGrid';

function splitCategories(categories: string[]): [string[], string[]] {
  const mid = Math.ceil(categories.length / 2);
  return [categories.slice(0, mid), categories.slice(mid)];
}

function buildScheduleDraft(extras: OrderExtras, defaultEventDate: string) {
  return {
    dateFrom: extras.scheduleDateFrom ?? defaultEventDate,
    dateTo: extras.scheduleDateTo ?? defaultEventDate,
    sessions: Object.fromEntries(
      MEAL_SESSIONS.map((s) => [
        s.id,
        {
          timeFrom: extras.mealSchedules?.[s.id]?.timeFrom ?? '',
          timeTo: extras.mealSchedules?.[s.id]?.timeTo ?? '',
        },
      ]),
    ) as Record<string, { timeFrom: string; timeTo: string }>,
  };
}

function sessionTimesFromExtras(extras: OrderExtras, session: string) {
  return {
    timeFrom: extras.mealSchedules?.[session]?.timeFrom ?? '',
    timeTo: extras.mealSchedules?.[session]?.timeTo ?? '',
  };
}

export function OrderDetailView({
  order,
  dishes,
  workers,
  onRefresh,
}: {
  order: Enquiry;
  dishes: Dish[];
  workers: Worker[];
  onRefresh: () => void;
}) {
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingExtras, setEditingExtras] = useState(false);
  const [dishId, setDishId] = useState('');
  const [mealSession, setMealSession] = useState('Breakfast');
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState('');
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [scheduleSaving, setScheduleSaving] = useState(false);

  const extras = useMemo(() => parseOrderNotes(order.notes), [order.notes]);
  const [draftExtras, setDraftExtras] = useState<OrderExtras>(extras);
  const defaultEventDate = toDateInputValue(order.eventDate);
  const [draftSchedule, setDraftSchedule] = useState(() => buildScheduleDraft(extras, defaultEventDate));
  const [sessionTimeFrom, setSessionTimeFrom] = useState(() => sessionTimesFromExtras(extras, 'Breakfast').timeFrom);
  const [sessionTimeTo, setSessionTimeTo] = useState(() => sessionTimesFromExtras(extras, 'Breakfast').timeTo);
  const [columnDate, setColumnDate] = useState(() => extras.scheduleDateFrom ?? defaultEventDate);
  const [columnPax, setColumnPax] = useState('');
  const [sessionLabel, setSessionLabel] = useState('');

  const menuItems = useMemo(
    () => (order.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category)),
    [order.dishes],
  );
  const mealPrefs = useMemo(
    () => (order.dishes ?? []).filter((d) => PREFERENCE_CATEGORIES.has(d.category)),
    [order.dishes],
  );

  const byCategory = useMemo(() => {
    const map: Record<string, EnquiryDish[]> = {};
    for (const d of menuItems) {
      (map[d.category] ||= []).push(d);
    }
    return map;
  }, [menuItems]);

  const orderedSessions = useMemo(() => groupMenuItems(menuItems), [menuItems]);
  const [colLeft, colRight] = splitCategories(orderedSessions);

  const displayDietary = extras.dietary;

  const scheduleSummary = useMemo(() => {
    const from = extras.scheduleDateFrom;
    const to = extras.scheduleDateTo ?? from;
    const datePart =
      from && to
        ? from === to
          ? formatDate(from)
          : `${formatDate(from)} – ${formatDate(to)}`
        : '';
    const sessionLines = orderedSessions
      .map((session) => {
        const range = formatMealTimeRange(extras.mealSchedules?.[session]);
        return range ? `${session}: ${range}` : null;
      })
      .filter(Boolean) as string[];
    return { datePart, sessionLines };
  }, [extras, orderedSessions]);

  const sessionPaxSummary = useMemo(() => {
    const cols = resolveMenuColumns(extras, order, menuItems);
    const withPax = cols.filter((c) => c.pax != null && c.pax > 0);
    if (withPax.length === 0) return 'Set per session when adding menu';
    return withPax.map((c) => `${c.sessionLabel} ${c.pax}`).join(' · ');
  }, [extras, order, menuItems]);

  function pickMealSession(session: string) {
    setMealSession(session);
    const times = sessionTimesFromExtras(extras, session);
    setSessionTimeFrom(times.timeFrom);
    setSessionTimeTo(times.timeTo);
    setSessionLabel('');
    const cols = resolveMenuColumns(extras, order, menuItems);
    const existing = cols.find((c) => c.date === columnDate && c.baseSession === session);
    setColumnPax(existing?.pax != null ? String(existing.pax) : '');
  }

  async function handleAdd() {
    setAddError('');
    if (!dishId) {
      setAddError('Select a menu item first.');
      return;
    }
    if (!mealSession) {
      setAddError('Choose a meal session (breakfast, lunch, etc.).');
      return;
    }
    if (!columnDate) {
      setAddError('Pick the service date for this column (like Excel row 3).');
      return;
    }
    if (!columnPax.trim()) {
      setAddError('Enter pax for this session (e.g. 60 for breakfast, 100 for lunch).');
      return;
    }
    const paxNum = Number(columnPax);
    if (Number.isNaN(paxNum) || paxNum < 1) {
      setAddError('Enter a valid pax count for this session.');
      return;
    }
    setSaving(true);
    try {
      const currentColumns = resolveMenuColumns(extras, order, menuItems);
      const label = sessionLabel.trim() || sessionLabelOptions(mealSession);
      const { columns, columnId } = findOrCreateColumn(currentColumns, {
        date: columnDate,
        baseSession: mealSession,
        sessionLabel: label,
        pax: paxNum,
        timeFrom: sessionTimeFrom,
        timeTo: sessionTimeTo,
      });

      let merged: OrderExtras = {
        ...extras,
        menuColumns: stripMenuColumnsForSave(columns),
        mealSchedules: {
          ...(extras.mealSchedules ?? {}),
          [mealSession]: {
            timeFrom: sessionTimeFrom || null,
            timeTo: sessionTimeTo || null,
          },
        },
      };
      await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });

      const prevIds = new Set((order.dishes ?? []).map((d) => d.id));
      const updated = await addOrderDish(order.id, {
        dishId,
        category: mealSession,
      });
      const newDish = updated.dishes.find(
        (d) => !prevIds.has(d.id) && (d.dishId === dishId || d.dishName),
      );
      if (newDish) {
        merged = assignDishColumn(merged, newDish.id, columnId);
        await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });
      }

      setDishId('');
      await onRefresh();
    } catch {
      setAddError('Could not add item.');
    } finally {
      setSaving(false);
    }
  }

  async function saveExtras() {
    setSaving(true);
    try {
      await updateEnquiry(order.id, { notes: serializeOrderNotes(draftExtras) });
      setEditingExtras(false);
      await onRefresh();
    } finally {
      setSaving(false);
    }
  }

  function startEditSchedule() {
    setDraftSchedule(buildScheduleDraft(extras, defaultEventDate));
    setEditingSchedule(true);
  }

  async function saveSchedule() {
    setScheduleSaving(true);
    try {
      const merged: OrderExtras = {
        ...extras,
        scheduleDateFrom: draftSchedule.dateFrom || null,
        scheduleDateTo: draftSchedule.dateTo || null,
        scheduleTimeFrom: null,
        scheduleTimeTo: null,
        mealSchedules: mealSchedulesForSave(draftSchedule.sessions),
      };
      await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });
      setEditingSchedule(false);
      await onRefresh();
    } finally {
      setScheduleSaving(false);
    }
  }

  function startEditExtras() {
    setDraftExtras(parseOrderNotes(order.notes));
    setEditingExtras(true);
  }

  const menuColumns = useMemo(
    () => resolveMenuColumns(extras, order, menuItems),
    [extras, order, menuItems],
  );

  return (
    <div className="order-view max-w-5xl mx-auto pb-12">
      <Link
        to="/orders"
        className="inline-flex items-center gap-2 text-sm text-[var(--muted)] hover:text-[var(--primary)] mb-6"
      >
        <ArrowLeft size={18} />
        Back to orders
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="order-view-title text-3xl md:text-4xl text-[var(--foreground)] tracking-tight">
            {order.customerName}
          </h1>
          <p className="text-sm text-[var(--muted)] mt-1 font-mono">{formatOrderId(order.id)}</p>
        </div>
        <span className="px-4 py-1.5 rounded-full text-sm font-medium bg-blue-500/15 text-blue-700 dark:text-blue-300 border border-blue-500/25">
          {statusLabel(order.status)}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[
          { icon: Clock, label: 'Date & time', value: formatDateTime(order.eventDate) },
          { icon: UtensilsCrossed, label: 'Session pax', value: sessionPaxSummary },
          { icon: MapPin, label: 'Venue', value: order.eventLocation },
          { icon: Phone, label: 'Contact', value: order.phoneNumber },
        ].map(({ icon: Icon, label, value }) => (
          <div
            key={label}
            className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 shadow-[var(--shadow-sm)]"
          >
            <Icon size={18} className="text-[var(--order-accent)] mb-2" />
            <p className="text-[10px] uppercase tracking-wider text-[var(--order-accent)] font-medium">{label}</p>
            <p className="text-sm font-semibold text-[var(--foreground)] mt-1 leading-snug">{value}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        <Link
          to={`/orders/${order.id}/kitchen`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-[var(--border)] text-sm hover:bg-[var(--sidebar-hover)]"
        >
          <FileText size={16} /> Kitchen copy
        </Link>
        <Link
          to={`/orders/${order.id}/billing`}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-[var(--border)] text-sm hover:bg-[var(--sidebar-hover)]"
        >
          <FileText size={16} /> Order copy
        </Link>
      </div>

      <OrderRegionalStyleSection orderId={order.id} extras={extras} onRefresh={onRefresh} />

      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mb-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-2">
            <ChefHat size={22} className="text-[var(--order-accent)]" />
            <h2 className="order-view-title text-xl font-semibold text-[var(--foreground)]">Menu breakdown</h2>
          </div>
          <button
            type="button"
            onClick={() => setShowAddForm((v) => !v)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--primary)] text-white text-sm font-medium hover:bg-[var(--primary-hover)]"
          >
            <Plus size={18} />
            Add menu item
          </button>
        </div>

        {showAddForm && (
          <div className="mb-8 p-4 rounded-xl border border-[var(--border)] bg-[var(--background)]">
            <p className="text-sm text-[var(--muted)] mb-4">
              Set pax per session (breakfast, lunch, coffee, etc.) — each can be different. Then add dish names.
            </p>
            <div className="flex flex-wrap gap-2 mb-4">
              {MEAL_SESSIONS.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => pickMealSession(s.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    mealSession === s.id
                      ? 'bg-[var(--primary)] text-white border-[var(--primary)]'
                      : 'bg-[var(--card)] text-[var(--foreground)] border-[var(--border)] hover:border-[var(--primary)]'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
              <div>
                <label className="text-xs text-[var(--muted)]">Service date</label>
                <input
                  type="date"
                  value={columnDate}
                  onChange={(e) => setColumnDate(e.target.value)}
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--muted)]">Session label (Excel row 4)</label>
                <input
                  type="text"
                  value={sessionLabel}
                  onChange={(e) => setSessionLabel(e.target.value)}
                  placeholder={sessionLabelOptions(mealSession)}
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--muted)]">Pax for {mealSession} *</label>
                <input
                  type="number"
                  min={1}
                  required
                  value={columnPax}
                  onChange={(e) => setColumnPax(e.target.value)}
                  placeholder="e.g. 60 or 100"
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--muted)]">Time from ({mealSession})</label>
                <input
                  type="time"
                  value={sessionTimeFrom}
                  onChange={(e) => setSessionTimeFrom(e.target.value)}
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-[var(--muted)]">Time to ({mealSession})</label>
                <input
                  type="time"
                  value={sessionTimeTo}
                  onChange={(e) => setSessionTimeTo(e.target.value)}
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg text-sm"
                />
              </div>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-end">
              <div className="lg:col-span-10">
                <DishSearchSelect
                  dishes={dishes}
                  value={dishId}
                  onChange={setDishId}
                />
              </div>
              <div className="lg:col-span-2">
                <Button type="button" onClick={handleAdd} disabled={saving || !dishId} className="w-full !py-2">
                  Add
                </Button>
              </div>
            </div>
            {addError && <p className="text-sm text-red-600 mt-2">{addError}</p>}
          </div>
        )}

        {menuColumns.length > 0 || menuItems.length > 0 ? (
          <>
            <OrderExcelHeader order={order} />
            <OrderExcelMenuGrid
              order={order}
              extras={extras}
              menuItems={menuItems}
              onRefresh={onRefresh}
            />
          </>
        ) : (
          <p className="text-center text-[var(--muted)] py-10 text-sm">
            No menu items yet. Choose a session, set date, pax, and time, then add dishes — columns appear like the Excel menu sheet.
          </p>
        )}

        {mealPrefs.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[var(--border)]">
            <h4 className="text-sm font-semibold text-[var(--order-accent)] mb-2">Meal services (from enquiry)</h4>
            <ul className="text-sm space-y-1">
              {mealPrefs.map((d) => (
                <li key={d.id} className="flex justify-between gap-4">
                  <span>{d.dishName}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)] mb-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
          <div className="flex items-center gap-2">
            <Calendar size={22} className="text-[var(--order-accent)]" />
            <h2 className="order-view-title text-xl font-semibold text-[var(--foreground)]">Event schedule</h2>
          </div>
          {!editingSchedule ? (
            <button
              type="button"
              onClick={startEditSchedule}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-[var(--border)] hover:bg-[var(--sidebar-hover)] text-[var(--foreground)]"
            >
              <Pencil size={14} /> Edit
            </button>
          ) : (
            <div className="flex gap-2">
              <Button type="button" onClick={saveSchedule} disabled={scheduleSaving} className="!py-1.5 !px-3 text-xs">
                Save
              </Button>
              <button
                type="button"
                onClick={() => setEditingSchedule(false)}
                className="px-3 py-1.5 text-xs border border-[var(--border)] rounded-lg"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {editingSchedule ? (
          <div className="space-y-6 text-sm">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-[var(--order-accent)]">Event date from</label>
                <input
                  type="date"
                  value={draftSchedule.dateFrom}
                  onChange={(e) => setDraftSchedule({ ...draftSchedule, dateFrom: e.target.value })}
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-[var(--order-accent)]">Event date to</label>
                <input
                  type="date"
                  value={draftSchedule.dateTo}
                  min={draftSchedule.dateFrom}
                  onChange={(e) => setDraftSchedule({ ...draftSchedule, dateTo: e.target.value })}
                  className="form-input w-full mt-1 px-3 py-2 rounded-lg"
                />
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-[var(--order-accent)] mb-3">
                Meal times (only sessions on this order)
              </p>
              {orderedSessions.length === 0 ? (
                <p className="text-[var(--muted)] text-sm">Add menu items first, then set times above or here.</p>
              ) : (
                <div className="space-y-3">
                  {orderedSessions.map((session) => (
                    <div key={session} className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
                      <span className="font-medium text-[var(--foreground)]">{session}</span>
                      <input
                        type="time"
                        value={draftSchedule.sessions[session]?.timeFrom ?? ''}
                        onChange={(e) =>
                          setDraftSchedule({
                            ...draftSchedule,
                            sessions: {
                              ...draftSchedule.sessions,
                              [session]: { ...draftSchedule.sessions[session], timeFrom: e.target.value },
                            },
                          })
                        }
                        className="form-input px-3 py-2 rounded-lg"
                      />
                      <input
                        type="time"
                        value={draftSchedule.sessions[session]?.timeTo ?? ''}
                        onChange={(e) =>
                          setDraftSchedule({
                            ...draftSchedule,
                            sessions: {
                              ...draftSchedule.sessions,
                              [session]: { ...draftSchedule.sessions[session], timeTo: e.target.value },
                            },
                          })
                        }
                        className="form-input px-3 py-2 rounded-lg"
                      />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="space-y-4 text-sm">
            <div>
              <p className="text-xs font-semibold text-[var(--order-accent)] mb-1">Event dates</p>
              <p className="text-[var(--foreground)]">
                {scheduleSummary.datePart || 'Not set — click Edit for multi-day booking'}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold text-[var(--order-accent)] mb-2">Meal times</p>
              {scheduleSummary.sessionLines.length === 0 ? (
                <p className="text-[var(--muted)]">Set times when adding each meal session</p>
              ) : (
                <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-[var(--foreground)]">
                  {scheduleSummary.sessionLines.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
        <p className="text-xs text-[var(--muted)] mt-4">
          Only meal sessions with dishes are shown. Set date range for multi-day events; enter times manually per session.
        </p>
      </div>

      <OrderDispatchSection
        orderId={order.id}
        menuItems={menuItems}
        byCategory={byCategory}
        colLeft={colLeft}
        colRight={colRight}
        workers={workers}
        extras={extras}
        onRefresh={onRefresh}
      />

      <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-6 md:p-8 shadow-[var(--shadow-sm)]">
        <div className="flex items-center justify-between gap-3 mb-5">
          <h2 className="order-view-title text-xl font-semibold text-[var(--foreground)]">Customizations</h2>
          {!editingExtras ? (
            <button
              type="button"
              onClick={startEditExtras}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-[var(--border)] hover:bg-[var(--sidebar-hover)] text-[var(--foreground)]"
            >
              <Pencil size={14} /> Edit
            </button>
          ) : (
            <div className="flex gap-2">
              <Button type="button" onClick={saveExtras} disabled={saving} className="!py-1.5 !px-3 text-xs">
                Save
              </Button>
              <button
                type="button"
                onClick={() => setEditingExtras(false)}
                className="px-3 py-1.5 text-xs border border-[var(--border)] rounded-lg"
              >
                Cancel
              </button>
            </div>
          )}
        </div>

        {editingExtras ? (
          <div className="space-y-4 text-sm">
            <div>
              <label className="text-xs font-medium text-[var(--order-accent)]">Dietary requests (one per line)</label>
              <textarea
                rows={3}
                value={draftExtras.dietary.join('\n')}
                onChange={(e) =>
                  setDraftExtras({
                    ...draftExtras,
                    dietary: e.target.value.split('\n').map((l) => l.trim()).filter(Boolean),
                  })
                }
                className="form-input w-full mt-1 px-3 py-2 rounded-lg"
                placeholder="Jain option for 50 guests"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--order-accent)]">Live counters (comma separated)</label>
              <input
                value={draftExtras.liveCounters.join(', ')}
                onChange={(e) =>
                  setDraftExtras({
                    ...draftExtras,
                    liveCounters: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
                className="form-input w-full mt-1 px-3 py-2 rounded-lg"
                placeholder="Dosa Counter, Chaat Counter"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-[var(--order-accent)]">Add-ons (comma separated)</label>
              <input
                value={draftExtras.addOns.join(', ')}
                onChange={(e) =>
                  setDraftExtras({
                    ...draftExtras,
                    addOns: e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
                  })
                }
                className="form-input w-full mt-1 px-3 py-2 rounded-lg"
                placeholder="Ice Cream Stall, Paan Counter"
              />
            </div>
          </div>
        ) : (
          <div className="space-y-5">
            <div>
              <p className="text-xs font-semibold text-[var(--order-accent)] mb-2">Dietary requests</p>
              {displayDietary.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">None — click Edit to add.</p>
              ) : (
                <ul className="list-disc list-inside text-sm space-y-1 text-[var(--foreground)]">
                  {displayDietary.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-[var(--order-accent)] mb-2">Live counters</p>
              {extras.liveCounters.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">None</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {extras.liveCounters.map((t) => (
                    <span key={t} className="px-3 py-1 rounded-full text-sm bg-[var(--background)] border border-[var(--border)]">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-[var(--order-accent)] mb-2">Add-ons</p>
              {extras.addOns.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">None</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {extras.addOns.map((t) => (
                    <span key={t} className="px-3 py-1 rounded-full text-sm bg-[var(--background)] border border-[var(--border)]">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <OrderExtrasSection orderId={order.id} extras={extras} onRefresh={onRefresh} />
    </div>
  );
}
