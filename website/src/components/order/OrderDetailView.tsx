import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft, ChefHat, Clock, MapPin, Phone, Plus, Pencil, FileText, User,
} from 'lucide-react';
import type { Dish, Enquiry, EnquiryDish, Worker } from '../../api/client';
import {
  addOrderDish,
  formatDateTime,
  updateEnquiry,
} from '../../api/client';
import { DishSearchSelect } from '../DishSearchSelect';
import { Button } from '../Layout';
import { OrderDispatchSection } from './OrderDispatchSection';
import { OrderMenuItem } from './OrderMenuItem';
import { CustomizationInput } from './CustomizationInput';
import {
  formatOrderId,
  groupMenuItems,
  parseOrderNotes,
  serializeOrderNotes,
  statusLabel,
  type OrderExtras,
} from '../../utils/orderNotes';
import { QuantityUnitFields } from './QuantityUnitFields';

function splitCategories(categories: string[]): [string[], string[]] {
  const mid = Math.ceil(categories.length / 2);
  return [categories.slice(0, mid), categories.slice(mid)];
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
  const [quantity, setQuantity] = useState(1);
  const [quantityUnit, setQuantityUnit] = useState('pcs');
  const [customization, setCustomization] = useState('');
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState('');

  const extras = useMemo(() => parseOrderNotes(order.notes), [order.notes]);
  const [draftExtras, setDraftExtras] = useState<OrderExtras>(extras);

  const menuItems = useMemo(
    () => (order.dishes ?? []).filter((d) => d.category !== 'Cuisine Preference'),
    [order.dishes],
  );
  const cuisinePrefs = useMemo(
    () => (order.dishes ?? []).filter((d) => d.category === 'Cuisine Preference'),
    [order.dishes],
  );

  const byCategory = useMemo(() => {
    const map: Record<string, EnquiryDish[]> = {};
    for (const d of menuItems) {
      (map[d.category] ||= []).push(d);
    }
    return map;
  }, [menuItems]);

  const categories = groupMenuItems(menuItems);
  const [colLeft, colRight] = splitCategories(categories);

  const dietaryFromDishes = useMemo(() => {
    const set = new Set<string>();
    for (const d of order.dishes ?? []) {
      if (d.customizations?.trim()) set.add(d.customizations.trim());
    }
    return [...set];
  }, [order.dishes]);

  const displayDietary = [...new Set([...extras.dietary, ...dietaryFromDishes])];

  async function handleAdd() {
    setAddError('');
    if (!dishId) {
      setAddError('Select a menu item first.');
      return;
    }
    setSaving(true);
    try {
      await addOrderDish(order.id, {
        dishId,
        quantity,
        quantityUnit,
        customizations: customization || undefined,
      });
      setDishId('');
      setQuantity(1);
      setQuantityUnit('pcs');
      setCustomization('');
      setShowAddForm(false);
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

  function startEditExtras() {
    setDraftExtras(parseOrderNotes(order.notes));
    setEditingExtras(true);
  }

  function renderCategoryColumn(cats: string[]) {
    return (
      <div className="space-y-6">
        {cats.map((cat) => (
          <div key={cat}>
            <h4 className="text-sm font-semibold text-[var(--order-accent)] mb-2 tracking-wide">
              {cat}
            </h4>
            <ul>
              {(byCategory[cat] ?? []).map((d) => (
                <OrderMenuItem key={d.id} orderId={order.id} dish={d} onUpdated={onRefresh} />
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }

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
          { icon: User, label: 'PAX', value: `${order.guestCount} guests` },
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
            <p className="text-sm text-[var(--muted)] mb-4">Search the menu, set quantity and unit (pieces, kg, liters, etc.).</p>
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-end">
              <div className="lg:col-span-3">
                <DishSearchSelect
                  dishes={dishes}
                  value={dishId}
                  onChange={setDishId}
                />
              </div>
              <div className="lg:col-span-4 grid grid-cols-2 gap-2">
                <QuantityUnitFields
                  idPrefix={`add-${order.id}`}
                  quantity={quantity}
                  unit={quantityUnit}
                  onQuantityChange={setQuantity}
                  onUnitChange={setQuantityUnit}
                />
              </div>
              <div className="lg:col-span-3">
                <label className="text-xs text-[var(--muted)]">Customization</label>
                <CustomizationInput
                  id={`add-custom-${order.id}`}
                  value={customization}
                  onChange={setCustomization}
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

        {menuItems.length === 0 ? (
          <p className="text-center text-[var(--muted)] py-10 text-sm">
            No menu items yet. Click <strong>Add menu item</strong> to build the order in category format.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
            {renderCategoryColumn(colLeft)}
            {renderCategoryColumn(colRight)}
          </div>
        )}

        {cuisinePrefs.length > 0 && (
          <div className="mt-8 pt-6 border-t border-[var(--border)]">
            <h4 className="text-sm font-semibold text-[var(--order-accent)] mb-2">Cuisine style (from enquiry)</h4>
            <ul className="text-sm space-y-1">
              {cuisinePrefs.map((d) => (
                <li key={d.id} className="flex justify-between gap-4">
                  <span>{d.dishName}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
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
    </div>
  );
}
