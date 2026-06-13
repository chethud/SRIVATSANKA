import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { PageHeader, EmptyState, Card } from '../components/Layout';
import { AttentionBadge } from '../components/AttentionBadge';
import { OrderScheduleBadge } from '../components/OrderScheduleBadge';
import { FilterChips } from '../components/ui';
import { useAppData } from '../context/AppDataContext';
import { formatDate } from '../api/client';
import { isUnviewedOrder, sortOrdersForAttention } from '../utils/attention';
import { MONTH_FILTERS, matchesMonthFilter } from '../utils/monthFilter';
import { isOrderCompleted, sortOrdersBySchedule } from '../utils/orderSchedule';
import { buildSerialNumberMap } from '../utils/serialNumbers';

const SCHEDULE_FILTERS = [
  { id: 'ALL', label: 'All orders' },
  { id: 'UPCOMING', label: 'Upcoming' },
  { id: 'COMPLETED', label: 'Completed' },
];

export default function OrdersPage() {
  const { enquiries } = useAppData();
  const [searchParams] = useSearchParams();
  const attentionOnly = searchParams.get('attention') === '1';
  const [monthFilter, setMonthFilter] = useState('ALL');
  const [scheduleFilter, setScheduleFilter] = useState('ALL');

  const allOrders = useMemo(
    () => enquiries.filter((e) => e.status === 'CONVERTED'),
    [enquiries],
  );

  const serialNumbers = useMemo(() => buildSerialNumberMap(allOrders), [allOrders]);

  const unviewedOrders = useMemo(
    () => sortOrdersForAttention(allOrders.filter(isUnviewedOrder)),
    [allOrders],
  );

  const orders = useMemo(() => {
    let list = attentionOnly ? unviewedOrders : allOrders;
    list = list.filter((e) => matchesMonthFilter(e.createdAt, monthFilter));
    if (scheduleFilter === 'UPCOMING') {
      list = list.filter((e) => !isOrderCompleted(e.eventDate));
    } else if (scheduleFilter === 'COMPLETED') {
      list = list.filter((e) => isOrderCompleted(e.eventDate));
    }
    list = attentionOnly ? sortOrdersForAttention(list) : sortOrdersBySchedule(list);
    return list;
  }, [allOrders, attentionOnly, unviewedOrders, monthFilter, scheduleFilter]);

  return (
    <>
      <PageHeader
        title="Orders"
        description={
          attentionOnly
            ? `${orders.length} new ${orders.length === 1 ? 'order needs' : 'orders need'} your attention`
            : 'Converted clients — upcoming orders show a countdown; past event dates are marked completed'
        }
      />
      <div className="flex flex-col gap-3 mb-6">
        <FilterChips options={SCHEDULE_FILTERS} selected={scheduleFilter} onSelect={setScheduleFilter} />
        <FilterChips options={MONTH_FILTERS} selected={monthFilter} onSelect={setMonthFilter} />
      </div>
      {orders.length === 0 ? (
        <EmptyState
          message={
            attentionOnly
              ? 'No new orders waiting — all caught up.'
              : 'No orders match your filters.'
          }
        />
      ) : (
        <div className="flex flex-col gap-4">
          {orders.map((e) => {
            const unread = isUnviewedOrder(e);
            const serial = serialNumbers.get(e.id);
            const completed = isOrderCompleted(e.eventDate);
            return (
              <Link key={e.id} to={`/orders/${e.id}`} className="block">
                <Card
                  className={`relative p-5 hover:border-[var(--primary)] transition-colors flex items-center justify-between gap-4 ${
                    unread ? 'attention-unread' : completed ? 'opacity-90' : ''
                  }`}
                >
                  <OrderScheduleBadge
                    eventDate={e.eventDate}
                    className="absolute top-3 right-12 sm:right-14"
                  />
                  <div className="min-w-0 pr-24 sm:pr-28">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-[var(--muted)] tabular-nums">#{serial}</span>
                      <h3 className="font-semibold">{e.customerName}</h3>
                      {unread && <AttentionBadge label="New order" />}
                    </div>
                    <p className="text-sm text-[var(--muted)]">
                      {e.eventType} · {formatDate(e.eventDate)}
                    </p>
                    <p className="text-xs text-[var(--muted)] mt-1">
                      {(e.dishes?.length ?? 0)} menu items
                      {unread ? ' · Not opened yet' : completed ? ' · Event finished' : ''}
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
