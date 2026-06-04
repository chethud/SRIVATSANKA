import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { PageHeader, EmptyState, Card } from '../components/Layout';
import { useAppData } from '../context/AppDataContext';
import { formatDate, formatCurrency } from '../api/client';

export default function OrdersPage() {
  const { enquiries } = useAppData();

  const orders = useMemo(
    () => enquiries.filter((e) => e.status === 'CONVERTED'),
    [enquiries],
  );

  return (
    <>
      <PageHeader
        title="Orders"
        description="Converted clients — open an order to manage dishes, copies, and bills"
      />
      {orders.length === 0 ? (
        <EmptyState message="No converted orders yet. Mark an enquiry as CONVERTED on the Enquiries page after the client confirms." />
      ) : (
        <div className="space-y-3">
          {orders.map((e) => {
            const lineTotal = (e.dishes ?? []).reduce(
              (s, d) => s + (d.unitPrice ?? 0) * (d.quantity || 1),
              0,
            );
            const orderTotal = lineTotal * e.guestCount;

            return (
              <Link key={e.id} to={`/orders/${e.id}`}>
                <Card className="p-5 hover:border-[var(--primary)] transition-colors flex items-center justify-between gap-4">
                  <div>
                    <h3 className="font-semibold">{e.customerName}</h3>
                    <p className="text-sm text-[var(--muted)]">
                      {e.eventType} · {e.guestCount} guests · {formatDate(e.eventDate)}
                    </p>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      {(e.dishes?.length ?? 0)} dishes · {formatCurrency(orderTotal)} est.
                    </p>
                  </div>
                  <ChevronRight className="text-[var(--muted)] shrink-0" size={20} />
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </>
  );
}
