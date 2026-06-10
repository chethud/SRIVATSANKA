import { formatDate, type Enquiry } from '../api/client';
import { BrandLogo } from './BrandLogo';
import { formatQuantityDisplay } from '../utils/quantityUnits';

export function OrderCopyView({ enquiry, copyType }: { enquiry: Enquiry; copyType: 'kitchen' | 'billing' }) {
  const lines = enquiry.dishes ?? [];
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';

  return (
    <div className="max-w-2xl mx-auto bg-white print:shadow-none" id="order-copy-print">
      <div className="-mx-8 -mt-8 mb-8 px-6 pt-6 pb-4 border-b-4 border-[var(--accent)]">
        <BrandLogo variant="card" className="mx-auto max-w-[220px]" />
        <p className="text-center text-sm font-semibold text-[var(--primary)] mt-4">{title}</p>
      </div>
      <dl className="grid grid-cols-2 gap-3 text-sm mb-8">
        <div><dt className="text-[var(--muted)]">Customer</dt><dd className="font-medium">{enquiry.customerName}</dd></div>
        <div><dt className="text-[var(--muted)]">Event</dt><dd>{enquiry.eventType}</dd></div>
        <div><dt className="text-[var(--muted)]">Date</dt><dd>{formatDate(enquiry.eventDate)}</dd></div>
        <div><dt className="text-[var(--muted)]">Guests</dt><dd>{enquiry.guestCount}</dd></div>
        <div className="col-span-2"><dt className="text-[var(--muted)]">Location</dt><dd>{enquiry.eventLocation}</dd></div>
      </dl>
      {lines.length === 0 ? (
        <p className="text-[var(--muted)] text-sm">No dishes on this order yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-[var(--primary-dark)]">
              <th className="text-left py-2">Dish</th>
              <th className="text-left py-2">Quantity</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => (
              <tr key={l.id} className="border-b border-[var(--border)]">
                <td className="py-3">
                  {l.dishName}
                  {l.served && <span className="text-[var(--logo-forest)] text-xs ml-1">✓ served</span>}
                  {l.customizations && <span className="block text-xs text-[var(--muted)] mt-0.5">{l.customizations}</span>}
                </td>
                <td className="py-3 text-[var(--muted)]">{formatQuantityDisplay(l.quantity, l.quantityUnit)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="text-xs text-[var(--muted)] mt-8">Menu quantities only — no pricing on this copy.</p>
    </div>
  );
}
