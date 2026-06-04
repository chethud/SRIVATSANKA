import { useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, FileText, Plus } from 'lucide-react';
import { PageHeader, Card, Button, EmptyState } from '../components/Layout';
import { DishSearchSelect } from '../components/DishSearchSelect';
import { OrderDishRow } from '../components/OrderDishRow';
import { useAppData } from '../context/AppDataContext';
import { addOrderDish, formatDate, formatCurrency } from '../api/client';

const CUSTOMIZATION_OPTIONS = [
  '', 'No Milk', 'No Onion', 'No Garlic', 'Less Spice', 'Less Sweet', 'Extra Vegetables',
];

export default function OrderDetailPage() {
  const { orderId } = useParams<{ orderId: string }>();
  const { enquiries, dishes, refresh } = useAppData();
  const order = enquiries.find((e) => e.id === orderId && e.status === 'CONVERTED');

  const [dishId, setDishId] = useState('');
  const [quantity, setQuantity] = useState(1);
  const [unitPrice, setUnitPrice] = useState<number | ''>('');
  const [customization, setCustomization] = useState('');
  const [saving, setSaving] = useState(false);
  const [addError, setAddError] = useState('');

  const lineTotal = useMemo(() => {
    if (!order) return 0;
    return (order.dishes ?? []).reduce((s, d) => s + (d.unitPrice ?? 0) * (d.quantity || 1), 0);
  }, [order]);
  const orderTotal = lineTotal * (order?.guestCount ?? 1);

  if (!order) {
    return (
      <>
        <Link to="/orders" className="text-sm text-[var(--primary)] hover:underline inline-flex items-center gap-1 mb-4">
          <ArrowLeft size={16} /> Back to orders
        </Link>
        <EmptyState message="Order not found or not converted yet." />
      </>
    );
  }

  function onDishPick(d: { id: string; price: number } | null) {
    if (d) setUnitPrice(d.price);
    else setUnitPrice('');
  }

  async function handleAdd() {
    setAddError('');
    if (!dishId || !orderId) {
      setAddError('Search and select a dish first.');
      return;
    }
    setSaving(true);
    try {
      await addOrderDish(orderId, {
        dishId,
        quantity: Math.max(1, quantity),
        customizations: customization || undefined,
        unitPrice: unitPrice === '' ? undefined : Number(unitPrice),
      });
      setDishId('');
      setQuantity(1);
      setUnitPrice('');
      setCustomization('');
      await refresh();
    } catch {
      setAddError('Could not add dish. Try again.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <Link to="/orders" className="text-sm text-[var(--primary)] hover:underline inline-flex items-center gap-1 mb-4">
        <ArrowLeft size={16} /> Back to orders
      </Link>
      <PageHeader
        title={order.customerName}
        description={`${order.eventType} · ${order.guestCount} guests · ${formatDate(order.eventDate)} · ${formatCurrency(orderTotal)} est.`}
      />

      <div className="flex flex-wrap gap-3 mb-8">
        <Link to={`/orders/${order.id}/kitchen`}>
          <Button type="button" className="flex items-center gap-2">
            <FileText size={16} /> Kitchen copy
          </Button>
        </Link>
        <Link to={`/orders/${order.id}/billing`}>
          <Button type="button" className="flex items-center gap-2">
            <FileText size={16} /> Billing copy
          </Button>
        </Link>
      </div>

      <Card className="p-6 mb-6">
        <h3 className="font-semibold text-lg mb-1">Add dish to order</h3>
        <p className="text-sm text-[var(--muted)] mb-5">Search menu, set quantity & customization, then click Add.</p>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-end">
          <div className="lg:col-span-4">
            <DishSearchSelect
              dishes={dishes}
              value={dishId}
              onChange={setDishId}
              onSelectDish={(d) => onDishPick(d)}
            />
          </div>
          <div className="lg:col-span-2">
            <label className="text-xs text-[var(--muted)] font-medium mb-1 block">Quantity</label>
            <input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, Number(e.target.value)))}
              className="w-full px-3 py-2.5 border border-[var(--border)] rounded-lg text-sm"
            />
          </div>
          <div className="lg:col-span-3">
            <label className="text-xs text-[var(--muted)] font-medium mb-1 block">Customization</label>
            <select
              value={customization}
              onChange={(e) => setCustomization(e.target.value)}
              className="w-full px-3 py-2.5 border border-[var(--border)] rounded-lg text-sm"
            >
              {CUSTOMIZATION_OPTIONS.map((c) => (
                <option key={c || 'none'} value={c}>{c || 'None'}</option>
              ))}
            </select>
          </div>
          <div className="lg:col-span-2">
            <label className="text-xs text-[var(--muted)] font-medium mb-1 block">Unit price (₹)</label>
            <input
              type="number"
              min={0}
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value === '' ? '' : Number(e.target.value))}
              placeholder="Auto"
              className="w-full px-3 py-2.5 border border-[var(--border)] rounded-lg text-sm"
            />
          </div>
          <div className="lg:col-span-1">
            <Button
              type="button"
              onClick={handleAdd}
              disabled={saving || !dishId}
              className="w-full flex items-center justify-center gap-1 !py-2.5"
            >
              <Plus size={18} />
              Add
            </Button>
          </div>
        </div>
        {addError && <p className="text-sm text-red-600 mt-3">{addError}</p>}
      </Card>

      <Card className="p-6">
        <h3 className="font-semibold mb-4">Order menu ({order.dishes?.length ?? 0})</h3>
        {(order.dishes ?? []).length === 0 ? (
          <p className="text-sm text-[var(--muted)] py-6 text-center">No dishes yet. Use the form above to add items.</p>
        ) : (
          <ul className="space-y-2">
            {order.dishes.map((d) => (
              <OrderDishRow key={d.id} orderId={order.id} dish={d} onUpdated={refresh} />
            ))}
          </ul>
        )}
      </Card>
    </>
  );
}
