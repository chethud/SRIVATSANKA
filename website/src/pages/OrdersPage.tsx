import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { PageHeader, EmptyState, Card } from '../components/Layout';
import { AttentionBadge } from '../components/AttentionBadge';
import { useAppData } from '../context/AppDataContext';
import { formatDate } from '../api/client';
import { isUnviewedOrder, sortOrdersForAttention } from '../utils/attention';

export default function OrdersPage() {
  const { enquiries } = useAppData();
  const [searchParams] = useSearchParams();
  const attentionOnly = searchParams.get('attention') === '1';

  const allOrders = useMemo(
    () => enquiries.filter((e) => e.status === 'CONVERTED'),
    [enquiries],
  );

  const unviewedOrders = useMemo(
    () => sortOrdersForAttention(allOrders.filter(isUnviewedOrder)),
    [allOrders],
  );

  const orders = useMemo(() => {
    const list = attentionOnly ? unviewedOrders : allOrders;
    return sortOrdersForAttention(list);
  }, [allOrders, attentionOnly, unviewedOrders]);

  return (
    <>
      <PageHeader
        title="Orders"
        description={
          attentionOnly
            ? `${orders.length} new ${orders.length === 1 ? 'order needs' : 'orders need'} your attention`
            : 'Converted clients — open an order to manage dishes, copies, and bills'
        }
      />
      {orders.length === 0 ? (
        <EmptyState
          message={
            attentionOnly
              ? 'No new orders waiting — all caught up.'
              : 'No converted orders yet. Mark an enquiry as CONVERTED on the Enquiries page after the client confirms.'
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          {orders.map((e) => {
            const unread = isUnviewedOrder(e);
            return (
              <Link key={e.id} to={`/orders/${e.id}`} className="block">
                <Card
                  className={`p-5 hover:border-[var(--primary)] transition-colors flex items-center justify-between gap-4 ${
                    unread ? 'attention-unread' : ''
                  }`}
                >
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold">{e.customerName}</h3>
                      {unread && <AttentionBadge label="New order" />}
                    </div>
                    <p className="text-sm text-[var(--muted)]">
                      {e.eventType} · {formatDate(e.eventDate)}
                    </p>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      {(e.dishes?.length ?? 0)} menu items
                      {unread ? ' · Not opened yet' : ''}
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
