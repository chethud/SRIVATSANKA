import { getOrderScheduleInfo, type OrderScheduleKind } from '../utils/orderSchedule';

const BADGE_STYLES: Record<OrderScheduleKind, string> = {
  completed: 'bg-[var(--background)] text-[var(--muted)] border-[var(--border)]',
  today: 'bg-amber-500 text-white border-amber-600 shadow-sm',
  urgent: 'bg-orange-500 text-white border-orange-600 shadow-sm',
  upcoming: 'bg-[var(--primary-light)] text-[var(--primary)] border-[var(--primary)]/30',
  none: '',
};

export function OrderScheduleBadge({
  eventDate,
  className = '',
}: {
  eventDate: string;
  className?: string;
}) {
  const info = getOrderScheduleInfo(eventDate);
  if (info.kind === 'none') return null;

  return (
    <span
      className={`inline-flex items-center px-2.5 py-1 rounded-lg text-[11px] font-semibold leading-tight border whitespace-nowrap ${BADGE_STYLES[info.kind]} ${className}`}
    >
      {info.label}
    </span>
  );
}
