import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, ChefHat, Clock, MapPin, Phone, Pencil, FileText, UtensilsCrossed, Calendar,
  FileSpreadsheet, Printer,
} from 'lucide-react';
import type { Dish, Enquiry, Worker } from '../../api/client';
import {
  formatDate,
  formatDateTime,
  markEnquiryDelivered,
  updateEnquiry,
} from '../../api/client';
import { AmPmTimeInput } from '../AmPmTimeInput';
import { Button } from '../Layout';
import { PaymentReceivedModal } from '../PaymentReceivedModal';
import { OrderCopyView } from '../OrderCopyView';
import { OrderDispatchSection } from './OrderDispatchSection';
import { OrderExtrasSection } from './OrderExtrasSection';
import { OrderRegionalStyleSection } from './OrderRegionalStyleSection';
import { OrderVenueMapSection } from './OrderVenueMapSection';
import { OrderExcelHeader, OrderExcelMenuGrid } from './OrderExcelMenuGrid';
import { useAppData } from '../../context/AppDataContext';
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
import { MEAL_SESSIONS, PREFERENCE_CATEGORIES, resolveSessionTabs } from '../../utils/mealSessions';
import { resolveMenuColumns } from '../../utils/orderMenuGrid';
import { downloadOrderCopyExcel } from '../../utils/orderCopies';

export type OrderPageView = 'details' | 'kitchen' | 'billing';

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

export function OrderDetailView({
  order,
  dishes,
  workers,
  onOrderUpdated,
  onDishesCatalogUpdated,
  initialView = 'details',
}: {
  order: Enquiry;
  dishes: Dish[];
  workers: Worker[];
  onOrderUpdated: (order: Enquiry) => void;
  onDishesCatalogUpdated?: () => Promise<void>;
  initialView?: OrderPageView;
}) {
  const [pageView, setPageView] = useState<OrderPageView>(initialView);
  const [excelBusy, setExcelBusy] = useState(false);
  const [editingExtras, setEditingExtras] = useState(false);
  const [addingSession, setAddingSession] = useState(false);
  const [newSessionName, setNewSessionName] = useState('');
  const [sessionSaving, setSessionSaving] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState(false);
  const [scheduleSaving, setScheduleSaving] = useState(false);
  const [deliveryBusy, setDeliveryBusy] = useState(false);
  const [showPaymentPopup, setShowPaymentPopup] = useState(false);
  const { refresh } = useAppData();

  async function handleDownloadExcel(copyType: 'kitchen' | 'billing') {
    setExcelBusy(true);
    try {
      await downloadOrderCopyExcel(order, copyType);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not download Excel. Please try again.');
    } finally {
      setExcelBusy(false);
    }
  }

  async function handleAddCustomSession() {
    const name = newSessionName.trim();
    if (!name) return;
    const exists = sessionTabs.some((s) => s.id.toLowerCase() === name.toLowerCase());
    if (exists) {
      setAddingSession(false);
      setNewSessionName('');
      return;
    }
    setSessionSaving(true);
    try {
      const customSessions = [...(extras.customSessions ?? []), name];
      const updated = await updateEnquiry(order.id, {
        notes: serializeOrderNotes({ ...extras, customSessions }),
      });
      onOrderUpdated(updated);
      setAddingSession(false);
      setNewSessionName('');
    } catch {
      alert('Could not add session. Please try again.');
    } finally {
      setSessionSaving(false);
    }
  }

  const extras = useMemo(() => parseOrderNotes(order.notes), [order.notes]);
  const [draftExtras, setDraftExtras] = useState<OrderExtras>(extras);
  const defaultEventDate = toDateInputValue(order.eventDate);
  const [draftSchedule, setDraftSchedule] = useState(() => buildScheduleDraft(extras, defaultEventDate));

  const menuItems = useMemo(
    () => (order.dishes ?? []).filter((d) => !PREFERENCE_CATEGORIES.has(d.category)),
    [order.dishes],
  );

  const sessionTabs = useMemo(
    () =>
      resolveSessionTabs(
        extras.customSessions,
        [
          ...menuItems.map((d) => d.category),
          ...(extras.menuColumns ?? []).map((c) => c.baseSession),
          ...dishes.map((d) => d.category),
        ],
      ),
    [extras.customSessions, extras.menuColumns, menuItems, dishes],
  );
  const mealPrefs = useMemo(
    () => (order.dishes ?? []).filter((d) => PREFERENCE_CATEGORIES.has(d.category)),
    [order.dishes],
  );

  const orderedSessions = useMemo(() => groupMenuItems(menuItems), [menuItems]);

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
    return withPax.map((c) => `${c.sessionLabel} · ${c.pax}`).join('\n');
  }, [extras, order, menuItems]);

  const dateTimeSummary = useMemo(() => {
    if (scheduleSummary.datePart) return scheduleSummary.datePart;
    return formatDateTime(order.eventDate);
  }, [scheduleSummary.datePart, order.eventDate]);

  async function saveExtras() {
    setSaving(true);
    try {
      const updated = await updateEnquiry(order.id, { notes: serializeOrderNotes(draftExtras) });
      setEditingExtras(false);
      onOrderUpdated(updated);
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
      const updated = await updateEnquiry(order.id, { notes: serializeOrderNotes(merged) });
      setEditingSchedule(false);
      onOrderUpdated(updated);
    } finally {
      setScheduleSaving(false);
    }
  }

  function startEditExtras() {
    setDraftExtras(parseOrderNotes(order.notes));
    setEditingExtras(true);
  }

  async function handleMarkDelivered() {
    setDeliveryBusy(true);
    try {
      const updated = await markEnquiryDelivered(order.id);
      onOrderUpdated(updated);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Could not mark delivered');
    } finally {
      setDeliveryBusy(false);
    }
  }

  return (
    <div className="order-view max-w-5xl mx-auto pb-12">
      {showPaymentPopup && (
        <PaymentReceivedModal
          orders={[order]}
          forceOrderId={order.id}
          onCloseForce={() => setShowPaymentPopup(false)}
          onResolved={async (updated) => {
            onOrderUpdated(updated);
            setShowPaymentPopup(false);
            await refresh();
          }}
        />
      )}

      <Link to="/orders" className="order-view-back">
        <ArrowLeft size={18} />
        Back to orders
      </Link>

      <div className="order-hero">
        <div>
          <h1 className="order-view-title text-3xl md:text-4xl text-[var(--foreground)] tracking-tight">
            {order.customerName}
          </h1>
          <p className="order-hero-meta">{formatOrderId(order.id)}</p>
          {order.eventType && <p className="order-hero-event">{order.eventType}</p>}
        </div>
        <div className="flex flex-col items-end gap-2">
          <span className="order-status-badge">{statusLabel(order.status)}</span>
          {order.paymentReceived ? (
            <span className="text-xs font-medium text-[var(--success-text)]">Payment received</span>
          ) : order.deliveredAt ? (
            <div className="flex flex-col items-end gap-1.5">
              <span className="text-xs font-medium text-amber-800">Delivered · awaiting payment</span>
              <button
                type="button"
                onClick={() => setShowPaymentPopup(true)}
                className="px-3 py-2.5 text-xs font-semibold rounded-lg bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] min-h-[2.5rem]"
              >
                Record payment
              </button>
            </div>
          ) : (
            <button
              type="button"
              disabled={deliveryBusy}
              onClick={() => void handleMarkDelivered()}
              className="px-3 py-2.5 text-xs font-semibold rounded-lg bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] disabled:opacity-60 min-h-[2.5rem]"
            >
              {deliveryBusy ? 'Saving…' : 'Mark as delivered'}
            </button>
          )}
        </div>
      </div>

      <div className="order-stat-grid">
        {[
          { icon: Clock, label: 'Date & time', value: dateTimeSummary },
          { icon: UtensilsCrossed, label: 'Session pax', value: sessionPaxSummary },
          { icon: MapPin, label: 'Venue', value: order.eventLocation },
          { icon: Phone, label: 'Contact', value: order.phoneNumber },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="order-stat-card">
            <div className="order-stat-icon">
              <Icon size={18} />
            </div>
            <div className="min-w-0">
              <p className="order-stat-label">{label}</p>
              <p
                className={`order-stat-value${label === 'Session pax' ? ' order-stat-value--sessions' : ''}`}
              >
                {value}
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="order-copy-bar">
        <button
          type="button"
          className={`order-copy-btn ${pageView === 'details' ? 'order-copy-btn--active' : ''}`}
          onClick={() => setPageView('details')}
        >
          <Pencil size={18} /> Order details
        </button>
        <button
          type="button"
          className={`order-copy-btn ${pageView === 'kitchen' ? 'order-copy-btn--active' : ''}`}
          onClick={() => setPageView('kitchen')}
        >
          <FileText size={18} /> Kitchen copy
        </button>
        <button
          type="button"
          className={`order-copy-btn ${pageView === 'billing' ? 'order-copy-btn--active' : ''}`}
          onClick={() => setPageView('billing')}
        >
          <FileText size={18} /> Order copy
        </button>
      </div>

      {pageView !== 'details' ? (
        <div className="order-inline-copy">
          <div className="order-inline-copy-actions print:hidden">
            <Button type="button" onClick={() => window.print()} className="flex items-center gap-2">
              <Printer size={16} />
              Print
            </Button>
            <Button
              type="button"
              onClick={() => void handleDownloadExcel(pageView)}
              disabled={excelBusy}
              className="flex items-center gap-2"
            >
              <FileSpreadsheet size={16} />
              {excelBusy ? 'Preparing Excel…' : 'Download Excel'}
            </Button>
          </div>
          <div className="order-copy-surface print:border-0 print:shadow-none print:p-0">
            <OrderCopyView enquiry={order} copyType={pageView} />
          </div>
        </div>
      ) : (
      <>
      <div className="order-section">
        <div className="order-section-head">
          <div className="order-section-title">
            <span className="order-section-icon order-section-icon--gold">
              <Calendar size={18} />
            </span>
            Event schedule
          </div>
          {!editingSchedule ? (
            <button type="button" onClick={startEditSchedule} className="order-btn-ghost">
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
                className="order-btn-ghost"
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
                      <AmPmTimeInput
                        value={draftSchedule.sessions[session]?.timeFrom ?? ''}
                        onChange={(hhmm) =>
                          setDraftSchedule({
                            ...draftSchedule,
                            sessions: {
                              ...draftSchedule.sessions,
                              [session]: { ...draftSchedule.sessions[session], timeFrom: hhmm },
                            },
                          })
                        }
                        aria-label={`${session} from`}
                      />
                      <AmPmTimeInput
                        value={draftSchedule.sessions[session]?.timeTo ?? ''}
                        onChange={(hhmm) =>
                          setDraftSchedule({
                            ...draftSchedule,
                            sessions: {
                              ...draftSchedule.sessions,
                              [session]: { ...draftSchedule.sessions[session], timeTo: hhmm },
                            },
                          })
                        }
                        aria-label={`${session} to`}
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
                <div className="flex flex-wrap gap-2">
                  {scheduleSummary.sessionLines.map((line) => (
                    <span key={line} className="order-schedule-pill">{line}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
        <p className="text-xs text-[var(--muted)] mt-4 pt-4 border-t border-[var(--border)]">
          Only meal sessions with dishes are shown. Set date range for multi-day events; enter times manually per session.
        </p>
      </div>

      <OrderRegionalStyleSection
        orderId={order.id}
        order={order}
        extras={extras}
        onOrderUpdated={onOrderUpdated}
      />

      <OrderVenueMapSection orderId={order.id} extras={extras} onOrderUpdated={onOrderUpdated} />

      <div className="order-section">
        <div className="order-section-head">
          <div className="order-section-title">
            <span className="order-section-icon">
              <ChefHat size={18} />
            </span>
            Menu breakdown
          </div>
        </div>

        <p className="order-section-sub">
          Pick a day, create Lunch / Dinner / other sessions together, then add dishes and times in each block.
        </p>

        <OrderExcelHeader order={order} />
        <OrderExcelMenuGrid
          order={order}
          extras={extras}
          menuItems={menuItems}
          sessionTabs={sessionTabs}
          dishes={dishes}
          onOrderUpdated={onOrderUpdated}
          onDishesCatalogUpdated={onDishesCatalogUpdated}
          onAddCustomSession={handleAddCustomSession}
          customSessionName={newSessionName}
          onCustomSessionNameChange={setNewSessionName}
          addingCustomSession={addingSession}
          onAddingCustomSessionChange={setAddingSession}
          customSessionSaving={sessionSaving}
        />

        {mealPrefs.length > 0 && (
          <div className="order-meal-prefs">
            <h4 className="order-meal-prefs-title">Meal services (from enquiry)</h4>
            <ul className="order-meal-prefs-list">
              {mealPrefs.map((d) => (
                <li key={d.id} className="order-meal-prefs-item">
                  <span>{d.dishName}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <OrderExtrasSection orderId={order.id} extras={extras} onOrderUpdated={onOrderUpdated} />

      <OrderDispatchSection
        orderId={order.id}
        workers={workers}
        extras={extras}
        onOrderUpdated={onOrderUpdated}
      />

      <div className="order-section">
        <div className="order-section-head">
          <div className="order-section-title">
            <span className="order-section-icon order-section-icon--gold">
              <Pencil size={16} />
            </span>
            Customizations
          </div>
          {!editingExtras ? (
            <button type="button" onClick={startEditExtras} className="order-btn-ghost">
              <Pencil size={14} /> Edit
            </button>
          ) : (
            <div className="flex gap-2">
              <Button type="button" onClick={saveExtras} disabled={saving} className="!py-1.5 !px-3 text-xs">
                Save
              </Button>
              <button type="button" onClick={() => setEditingExtras(false)} className="order-btn-ghost">
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
      </>
      )}
    </div>
  );
}
