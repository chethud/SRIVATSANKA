import { formatCurrency, formatDate, type Enquiry } from '../api/client';
import { BrandLogo } from './BrandLogo';
import { formatQuantityDisplay } from '../utils/quantityUnits';

export function OrderCopyView({ enquiry, copyType }: { enquiry: Enquiry; copyType: 'kitchen' | 'billing' }) {
  const lines = (enquiry.dishes ?? []).map((d) => ({
    ...d,
    lineTotal: (d.unitPrice ?? 0) * (d.quantity || 1),
  }));
  const subtotal = lines.reduce((s, l) => s + l.lineTotal, 0);
  const total = subtotal * enquiry.guestCount;
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Billing Copy';

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
              {copyType === 'billing' && <th className="text-right py-2">Amount</th>}
            </tr>
          </thead>
          <tbody>
            {lines.map((l) => (
              <tr key={l.id} className="border-b border-[var(--border)]">
                <td className="py-3">
                  {l.dishName} — {formatQuantityDisplay(l.quantity, l.quantityUnit)}
                  {l.served && <span className="text-[var(--logo-forest)] text-xs ml-1">✓ served</span>}
                  {l.customizations && <span className="block text-xs text-[var(--muted)] mt-0.5">{l.customizations}</span>}
                </td>
                {copyType === 'billing' && <td className="text-right py-3">{formatCurrency(l.lineTotal)}</td>}
              </tr>
            ))}
          </tbody>
          {copyType === 'billing' && (
            <tfoot>
              <tr>
                <td className="pt-3 text-[var(--muted)]">Per guest subtotal</td>
                <td className="pt-3 text-right">{formatCurrency(subtotal)}</td>
              </tr>
              <tr>
                <td className="pt-4 font-bold">Total ({enquiry.guestCount} guests)</td>
                <td className="pt-4 text-right font-bold text-lg">{formatCurrency(total)}</td>
              </tr>
            </tfoot>
          )}
        </table>
      )}
      {copyType === 'kitchen' && (
        <p className="text-xs text-[var(--muted)] mt-8">Kitchen copy — no pricing shown.</p>
      )}
    </div>
  );
}
