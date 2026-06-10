import { formatDate, type Enquiry } from '../api/client';

function buildHtml(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const lines = enquiry.dishes ?? [];
  const title = copyType === 'kitchen' ? 'Kitchen Copy' : 'Order Copy';

  const rows = lines
    .map(
      (l) => `
      <li style="padding:8px 0;border-bottom:1px solid #e5e7eb;">
        ${l.dishName}
        ${l.served ? '<span style="color:#15803d;font-size:12px;"> ✓ served</span>' : ''}
        ${l.customizations ? `<br><span style="color:#6b7280;font-size:12px;">${l.customizations}</span>` : ''}
      </li>`,
    )
    .join('');

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>${title}</title></head><body style="font-family:system-ui,sans-serif;padding:24px;max-width:640px;margin:0 auto;">
    <h1 style="color:#0b6b3a;">SRIVATSANKA</h1>
    <h2 style="font-size:14px;color:#64748b;">${title}</h2>
    <p><strong>${enquiry.customerName}</strong> · ${enquiry.eventType}<br>
    ${formatDate(enquiry.eventDate)} · ${enquiry.guestCount} guests · ${enquiry.eventLocation}</p>
    <ul style="list-style:none;padding:0;margin-top:16px;">
      ${rows || '<li style="padding:12px 0;color:#6b7280;">No dishes</li>'}
    </ul>
  </body></html>`;
}

export function downloadOrderCopy(enquiry: Enquiry, copyType: 'kitchen' | 'billing') {
  const html = buildHtml(enquiry, copyType);
  const blob = new Blob([html], { type: 'text/html' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${enquiry.customerName.replace(/\s+/g, '-')}-${copyType}-copy.html`;
  a.click();
  URL.revokeObjectURL(url);
}

export function printOrderCopy() {
  window.print();
}
